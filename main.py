import resend
from slowapi import Limiter
from datetime import datetime
from configs import GRAPHQL_URL, REDIS_URL, RESEND_APIKEY, EMAILS_TO_NOTIFY
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import requests, logging, aioredis, json, pytz
from fastapi import FastAPI, HTTPException, Request
from utils import rate_limit_exceeded_handler, QUERY, HEADERS




# SETUP LOGGER
logger = logging.getLogger(__file__)




# DNA
app = FastAPI(
    title='NYU Handshake Notifier v1',
    description='NYU Handshake Notifier v1',
    version='0.0.1',
)




# INIT
ist = pytz.timezone("Asia/Kolkata")
resend.api_key = RESEND_APIKEY
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)




# On-Start
@app.on_event("startup")
async def startup_event():
    # connect to Redis on startup
    app.state.redis = await aioredis.create_redis_pool(f"{REDIS_URL}")
    logger.info("Connected to Redis")




# On-Destroy
@app.on_event("shutdown")
async def shutdown_event():
    # disconnect from Redis on shutdown
    app.state.redis.close()
    await app.state.redis.wait_closed()
    logger.info("Disconnected from Redis")




# health
@app.get('/health')
@limiter.limit("2/minute")
async def check_alive(request: Request):
    return {'message': 'alive'}




def notify_via_email(new_jobs):
    if new_jobs:
        job_html_parts = []
        for idx, job in enumerate(new_jobs, start=1):
            job_data = job.get("node", {}).get("job", {})

            title = job_data.get("title", "N/A")
            job_html_parts.append(
                f"<p><strong>{idx}. {title}</strong><br>"
            )

        job_html_content = "<h3>NYU New OnCampus Job(s) on Handshake:</h3>" + "".join(job_html_parts)

        params: resend.Emails.SendParams = {
            "from": "alerts@resend.dev",
            "to": EMAILS_TO_NOTIFY.split(';'),
            "subject": "NYU Handshake New OnCampus Job(s) Alert!",
            "html": job_html_content,
        }
        return params


@app.post("/search-jobs")
async def search_jobs():
    new_jobs = []
    payload = {
        "operationName": "JobSearchQuery",
        "variables": {
            "first": 50,
            "after": "MA==",
            "input": {
                "filter": {"query": "nyu"},
                "sort": {"direction": "DESC", "field": "POST_DATE"}
            }
        },
        "query": QUERY
    }


    # check last job search timing in redis-cache
    last_check_timing = ""
    if await app.state.redis.exists("LAST_JOB_POSTING_CHECK"):
        cached_data = await app.state.redis.get("LAST_JOB_POSTING_CHECK")
        if cached_data is not None:
            last_check_timing = json.loads(cached_data).get("last_check")
        else:
            logger.warning("no-last-check-timing")

    try:
        res = requests.post(GRAPHQL_URL, json=payload, headers=HEADERS)
        jobs = res.json().get("data").get("jobSearch").get("edges")
        await app.state.redis.set("LAST_JOB_POSTING_CHECK", json.dumps({'last_check': datetime.now(ist).replace(microsecond=0).isoformat()}))
        await app.state.redis.expire("LAST_JOB_POSTING_CHECK", 24 * 60 * 60 * 50)
        if last_check_timing:
            for job in jobs:
                if datetime.fromisoformat(job.get("node").get("job").get("createdAt")) > datetime.fromisoformat(last_check_timing):
                    new_jobs.append(job)
        if new_jobs:
            params = notify_via_email(new_jobs)
            resend.Emails.send(params)
            logger.info("Alert Send")
            return {'message': 'emails notified for new jobs'}
        else:
            return {'message': 'no new jobs'}
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Request failed: {str(e)}")