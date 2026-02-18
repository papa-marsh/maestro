import asyncio
import threading
from datetime import timedelta
from typing import Any

from maestro.handlers.types import EventTypeName, get_event_type
from maestro.integrations.home_assistant.types import EventContext, WebSocketEvent
from maestro.integrations.home_assistant.websocket_client import WebSocketClient
from maestro.integrations.redis import RedisClient
from maestro.integrations.state_manager import StateManager
from maestro.utils.dates import IntervalSeconds, local_now, resolve_timestamp
from maestro.utils.exceptions import WebSocketConnectionError
from maestro.utils.logging import build_process_id, log, set_process_id

LAST_CONNECTED_KEY = "websocket_last_connected"
SYNC_THRESHOLD = timedelta(minutes=30)


class WebSocketManager:
    """
    Manages WebSocket connection lifecycle and routes events to handlers.
    Runs in a background thread with automatic reconnection.
    """

    def __init__(self) -> None:
        self.client = WebSocketClient()
        self.redis = RedisClient()
        self.min_reconnect_delay = 2
        self.max_reconnect_delay = 30
        self.reconnect_delay = self.min_reconnect_delay
        self.running = True
        self.process_id = build_process_id("websocket")

    def start(self) -> None:
        thread = threading.Thread(
            target=self._run_event_loop,
            daemon=True,
            name="WebSocketManager",
        )
        thread.start()
        log.info("WebSocket manager started", thread_name=thread.name)

    def stop(self) -> None:
        log.info("WebSocket manager stopping")
        self.running = False

    def _run_event_loop(self) -> None:
        """Run asyncio event loop in dedicated thread"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            loop.run_until_complete(self._maintain_connection())
        except Exception:
            log.exception("WebSocket event loop crashed")
        finally:
            loop.close()

    async def _maintain_connection(self) -> None:
        """Maintain WebSocket connection with exponential backoff reconnection"""
        set_process_id(self.process_id)

        while self.running:
            try:
                log.info("Attempting WebSocket connection")
                await self.client.connect()
                self.reconnect_delay = self.min_reconnect_delay

                if self._sync_states_needed():
                    self._sync_all_states()

                await self.client.subscribe_to_events(self._handle_event)

                self.set_last_connected()

            except WebSocketConnectionError as e:
                log.error("WebSocket connection error", error=str(e))
                self.set_last_connected()
            except Exception:
                log.exception("Unexpected WebSocket error")
                self.set_last_connected()

            try:
                await self.client.close()
            except Exception:
                log.exception("Error closing WebSocket")

            if not self.running:
                break  # type:ignore[unreachable]

            log.warning("Attempting WebSocket reconnection", delay_seconds=self.reconnect_delay)
            await asyncio.sleep(self.reconnect_delay)
            self.reconnect_delay = min(self.reconnect_delay + 2, self.max_reconnect_delay)

    def set_last_connected(self) -> None:
        """Persist the current time as the last WebSocket connection time"""
        try:
            log.info("Setting WebSocket connection time to now")
            self.redis.set(
                key=LAST_CONNECTED_KEY,
                value=local_now().isoformat(),
                ttl_seconds=IntervalSeconds.THIRTY_DAYS,
            )
        except Exception:
            log.exception("Failed to set last connected time")

    def _sync_states_needed(self) -> bool:
        """Sync all states only if disconnected longer than threshold"""
        last_connected = self.redis.get(LAST_CONNECTED_KEY)
        if last_connected is None:
            log.info("Last WebSocket connection time unknown - syncing entity states")
            return True

        last_connected = resolve_timestamp(last_connected)

        disconnect_duration = local_now() - last_connected
        if disconnect_duration >= SYNC_THRESHOLD:
            log.info(
                "WebSocket disconnected for extended period - syncing entity states",
                disconnect_duration=str(disconnect_duration),
            )
            return True
        else:
            log.info(
                "WebSocket reconnected quickly - skipping entity state sync",
                disconnect_duration=str(disconnect_duration),
            )
            return False

    def _sync_all_states(self) -> None:
        """Fetch all entity states from Home Assistant"""
        try:
            state_manager = StateManager()
            count = state_manager.fetch_all_hass_entities()
            log.info("State sync completed", entity_count=count)
        except Exception:
            log.exception("Failed to sync states")

    def _handle_event(self, raw_event: dict[str, Any]) -> None:
        """Route incoming WebSocket events to appropriate handlers"""
        from maestro.app import app

        event_type_name = (
            EventTypeName.HASS_STARTUP
            if self.is_hass_startup_event(raw_event)  # TODO: This is a hack
            else raw_event.get("event_type")
        )

        if not event_type_name or not isinstance(event_type_name, str):
            raise WebSocketConnectionError("Malformed websocket event payload")

        event_type = get_event_type(event_type_name)

        process_id = build_process_id(event_type.process_id_prefix)
        set_process_id(process_id)

        log.debug("WebSocket event received", event_type=event_type_name)

        context_data = raw_event.get("context", {})
        event = WebSocketEvent(
            event_type=event_type_name,
            data=raw_event.get("data", {}),
            time_fired=resolve_timestamp(str(raw_event.get("time_fired"))),
            origin=raw_event.get("origin", ""),
            context=EventContext(
                id=context_data.get("id", ""),
                parent_id=context_data.get("parent_id"),
                user_id=context_data.get("user_id"),
            ),
        )
        try:
            with app.app_context():
                event_type.handler_func(event)
        except Exception:
            log.exception(
                "Uncaught exception raised during WebSocket event",
                event_type=event_type_name,
            )

    @classmethod
    def is_hass_startup_event(cls, raw_event: dict[str, Any]) -> bool:
        if raw_event.get("event_type") != EventTypeName.STATE_CHANGED:
            return False

        entity_id: str = raw_event.get("data", {}).get("entity_id")

        return entity_id == "sensor.home_assistant_uptime"
