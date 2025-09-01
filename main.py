import resend
from slowapi import Limiter
from datetime import datetime, timedelta
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import requests, logging, aioredis, json, pytz
from fastapi import FastAPI, HTTPException, Request
from utils import rate_limit_exceeded_handler, QUERY, HEADERS
from configs import GRAPHQL_URL, REDIS_URL, RESEND_APIKEY, EMAILS_TO_NOTIFY, JOB_LINK
from fastapi.middleware.cors import CORSMiddleware


# SETUP LOGGER
logger = logging.getLogger(__file__)




# DNA
app = FastAPI(
    title='NYU Handshake Notifier v1',
    description='NYU Handshake Notifier v1',
    version='0.0.1',
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # or restrict to your frontend domain(s)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)




# INIT
ist = pytz.timezone("Asia/Kolkata")
resend.api_key = RESEND_APIKEY
limiter = Limiter(key_func=get_remote_address)
#app.state.limiter = limiter
#app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)




# On-Start
# @app.on_event("startup")
# async def startup_event():
#     connect to Redis on startup
#     app.state.redis = await aioredis.create_redis_pool(f"{REDIS_URL}")
#     logger.info("Connected to Redis")




# On-Destroy
# @app.on_event("shutdown")
# async def shutdown_event():
#     # disconnect from Redis on shutdown
#     app.state.redis.close()
#     await app.state.redis.wait_closed()
#     logger.info("Disconnected from Redis")




# health
@app.get('/health')
#@limiter.limit("2/minute")
async def check_alive(request: Request):
    return {'message': 'alive'}




def notify_via_email(new_jobs):
    if new_jobs:
        job_html_parts = []
        for idx, job in enumerate(new_jobs, start=1):
            job_data = job.get("node", {}).get("job", {})

            title = job_data.get("title", "N/A")
            start_date = job_data.get("startDate")[:10] if job_data.get("startDate") else "N/A"
            end_date = job_data.get("endDate")[:10] if job_data.get("endDate") else "N/A"
            work_hours = job_data.get("workSchedule").get("hours", "N/A") if job_data.get("workSchedule") else "N/A"
            work_interval = job_data.get("workSchedule").get("interval", "N/A").capitalize() if job_data.get("workSchedule") else "N/A"
            job_id = job_data.get("id", "")
            job_link = f"{JOB_LINK}/{job_id}"

            salary_min = job_data.get("salaryRange", {}).get("min", "N/A")
            salary_max = job_data.get("salaryRange", {}).get("max", "N/A")

            salary_info = (
                f"${int(salary_min/100)} - ${int(salary_max/100)}/hr"
                if salary_min != "N/A" and salary_max != "N/A"
                else "N/A"
            )

            job_html_parts.append(
                f"<p><strong>{idx}. <a href='{job_link}' target='_blank'>{title}</a></strong><br>"
                f"Start Date: {start_date}<br>"
                f"End Date: {end_date}<br>"
                f"Duration: {work_hours} hrs/{work_interval}<br>"
                f"Salary: {salary_info}</p>"
            )

        job_html_content = "<h3>NYU on-campus job posting(s) in the past 6hours on Handshake:</h3>" + "".join(job_html_parts)

        params: resend.Emails.SendParams = {
            "from": "alerts@resend.dev",
            "to": EMAILS_TO_NOTIFY.split(';'),
            "subject": "NYU Handshake OnCampus Job Alerts!",
            "html": job_html_content,
        }
        return params




@app.post("/search-jobs")
async def search_jobs():
    payload = {
        "operationName": "JobSearchQuery",
        "variables": {
            "first": 50,
            "after": "MA==",
            "input": {
                "filter": {
                    "locationRequirements": [
                        {"point": "40.785306,-73.979956", "label": "New York, NY, New York 10024, United States", "type": "place", "distance": "50mi"},
                        {"point": "42.751211,-75.465247", "label": "New York, United States", "type": "region", "distance": "50mi", "text": "New York"},
                        {"point": "40.712749,-74.005994", "label": "New York City, New York, United States", "type": "place", "distance": "50mi", "text": "New York City"}
                    ],
                    "query": "nyu"
                },
                "sort": {"direction": "DESC", "field": "POST_DATE"}
            }
        },
        "query": QUERY
    }

    try:
        logger.info(f"Making outbound request to {GRAPHQL_URL}")
        res = requests.post(GRAPHQL_URL, json=payload, headers=HEADERS, timeout=10)

        logger.info(f"Outbound status code: {res.status_code}")
        logger.info(f"Outbound headers: {res.headers}")
        logger.info(f"Outbound text (first 500 chars): {res.text[:500]}")

        return {
            "outbound_status": res.status_code,
            "outbound_headers": dict(res.headers),
            "outbound_body_snippet": res.text[:500]
        }

    except requests.RequestException as e:
        logger.error(f"Outbound request failed: {e}")
        raise HTTPException(status_code=500, detail=f"Outbound request failed: {str(e)}")
