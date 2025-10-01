import os
from zoneinfo import ZoneInfo

HOME_ASSISTANT_URL = os.environ["HOME_ASSISTANT_URL"].rstrip("/")
HOME_ASSISTANT_TOKEN = os.environ["HOME_ASSISTANT_TOKEN"]

REDIS_HOST = os.environ["REDIS_HOST"]
REDIS_PORT = int(os.environ["REDIS_PORT"])

DATABASE_URL = os.environ["DATABASE_URL"]
SQLALCHEMY_TRACK_MODIFICATIONS = False

TIMEZONE = ZoneInfo(os.environ.get("TIMEZONE", "America/New_York"))
AUTOPOPULATE_REGISTRY = os.environ.get("AUTOPOPULATE_REGISTRY") in [True, "True", "true", 1, "1"]
DOMAIN_IGNORE_LIST = os.environ.get("DOMAIN_IGNORE_LIST", "").split(",")
NOTIFY_ACTION_LIST = {
    notify_mapping.split(":")[1]: notify_mapping.split(":")[0]
    for notify_mapping in os.environ.get("NOTIFY_ACTION_LIST", "").split(",")
}
