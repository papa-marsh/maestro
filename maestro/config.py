import os

HOME_ASSISTANT_URL = os.environ["HOME_ASSISTANT_URL"].rstrip("/")
HOME_ASSISTANT_TOKEN = os.environ["HOME_ASSISTANT_TOKEN"]

REDIS_HOST = os.environ["REDIS_HOST"]
REDIS_PORT = int(os.environ["REDIS_PORT"])
