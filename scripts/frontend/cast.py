import threading
from time import sleep
from typing import override

import pychromecast
from maestro.domains import MediaPlayer
from maestro.integrations import RedisClient
from maestro.triggers import cron_trigger
from maestro.utils import log
from pychromecast.config import APP_DASHCAST
from pychromecast.controllers.dashcast import DashCastController
from pychromecast.controllers.receiver import CastStatus, CastStatusListener
from pychromecast.dial import get_device_info

from registry import media_player

NEST_DISPLAYS: list[tuple[MediaPlayer, str]] = [
    (media_player.office_display, "192.168.0.125"),
    (media_player.living_room_display, "192.168.0.143"),
    (media_player.kitchen_display, "192.168.0.127"),
]

CAST_URL = "http://192.168.0.107:8123/lovelace-cast/overview"
CAST_LOCK_KEY_PREFIX = "cast_lock_"
CHROMECAST_PORT = 8009
DEVICE_INFO_TIMEOUT_SECONDS = 10
CONNECT_TIMEOUT_SECONDS = 15
APP_READY_TIMEOUT_SECONDS = 15
DISCONNECT_TIMEOUT_SECONDS = 10


class DashCastReadyListener(CastStatusListener):
    """Waits for DashCast to accept URLs: on launch it reports "Application is
    starting" and only becomes responsive once its status is "Application ready"."""

    def __init__(self) -> None:
        self.app_ready = threading.Event()

    @override
    def new_cast_status(self, status: CastStatus) -> None:
        if status.app_id == APP_DASHCAST and status.status_text == "Application ready":
            self.app_ready.set()
        else:
            self.app_ready.clear()


def execute_cast(ip_address: str) -> None:
    device_info = get_device_info(ip_address, timeout=DEVICE_INFO_TIMEOUT_SECONDS)
    if device_info is None or device_info.uuid is None:
        raise ConnectionError(f"No device info returned from {ip_address}")

    host = (
        ip_address,
        CHROMECAST_PORT,
        device_info.uuid,
        device_info.model_name,
        device_info.friendly_name,
    )
    # tries=1 bounds the socket client's connection attempts; on failure its worker
    # thread exits instead of retrying forever, and wait() raises RequestTimeout.
    cast = pychromecast.get_chromecast_from_host(
        host,
        tries=1,
        timeout=CONNECT_TIMEOUT_SECONDS,
    )
    try:
        cast.wait(timeout=CONNECT_TIMEOUT_SECONDS)

        # A running DashCast session means the dashboard is already up. It can't be
        # relaunched or messaged anyway: the device ignores LAUNCH for an app that is
        # already running, and DashCast stops listening once it has navigated to a page.
        # If the session ever dies, the display falls back to idle and the next run
        # re-casts.
        if cast.app_id == APP_DASHCAST:
            log.debug("Display is already casting", ip_address=ip_address)
            return

        dashcast = DashCastController()
        cast.register_handler(dashcast)
        ready_listener = DashCastReadyListener()
        cast.register_status_listener(ready_listener)

        cast.start_app(APP_DASHCAST, force_launch=True)
        if not ready_listener.app_ready.wait(timeout=APP_READY_TIMEOUT_SECONDS):
            raise TimeoutError("DashCast app never reported ready")

        # With the app already running, the URL message sends synchronously.
        # The DashCast receiver never acknowledges it, so there is nothing to wait on.
        dashcast.load_url(CAST_URL, force=True)
    finally:
        # Disconnect stops the socket client thread; skipping it leaks a held
        # connection that counts against the display's per-client connection cap.
        cast.disconnect(timeout=DISCONNECT_TIMEOUT_SECONDS)


def call_cast_command(display: MediaPlayer, ip_address: str) -> None:
    lock_key = CAST_LOCK_KEY_PREFIX + display.id.entity
    with RedisClient().lock(lock_key, timeout_seconds=100, exit_if_owned=True):
        try:
            execute_cast(ip_address)
        except Exception:
            log.exception("Exception raised while attempting to cast", target=display.id)


@cron_trigger("*/10 * * * *")
def cast_to_displays() -> None:
    for display, ip_address in NEST_DISPLAYS:
        call_cast_command(display, ip_address)
        sleep(90)
