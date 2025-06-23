import os
from dotenv import load_dotenv


load_dotenv()


def env_get(env_var: str) -> str:
    val = os.environ.get(env_var)
    if not val:
        raise KeyError(f"Env variable '{env_var}' is not set!")
    return val


ORIGIN = env_get("ORIGIN")
REFERER = env_get("REFERER")
GRAPHQL_URL = env_get("GRAPHQL_URL")
COOKIE = env_get("COOKIE")
X_REQ_ID = env_get("X_REQ_ID")
X_CSRF_TOKEN = env_get("X_CSRF_TOKEN")
REDIS_URL = env_get("REDIS_URL")
RESEND_APIKEY = env_get("RESEND_APIKEY")
EMAILS_TO_NOTIFY = env_get("EMAILS_TO_NOTIFY")
JOB_LINK = env_get("JOB_LINK")
