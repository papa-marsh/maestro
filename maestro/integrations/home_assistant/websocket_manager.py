import asyncio
import threading
from collections.abc import Callable
from typing import Any

from maestro.integrations.home_assistant.websocket_client import WebSocketClient
from maestro.integrations.state_manager import StateManager
from maestro.utils.exceptions import WebSocketConnectionError
from maestro.utils.logging import build_process_id, log, set_process_id
from maestro.webhooks.event_fired import handle_event_fired
from maestro.webhooks.hass_shutdown import handle_hass_shutdown
from maestro.webhooks.hass_startup import handle_hass_startup
from maestro.webhooks.notif_action import handle_notif_action
from maestro.webhooks.state_changed import handle_state_changed


class WebSocketManager:
    """
    Manages WebSocket connection lifecycle and routes events to handlers.
    Runs in a background thread with automatic reconnection.
    """

    def __init__(self) -> None:
        self.client = WebSocketClient()
        self.min_reconnect_delay = 1
        self.reconnect_delay = self.min_reconnect_delay
        self.max_reconnect_delay = 60
        self.running = True

    def start(self) -> None:
        """Start WebSocket manager in background thread"""
        thread = threading.Thread(
            target=self._run_event_loop,
            daemon=True,
            name="WebSocketManager",
        )
        thread.start()
        log.info("WebSocket manager started", thread_name=thread.name)

    def stop(self) -> None:
        """Stop WebSocket manager gracefully"""
        self.running = False
        log.info("WebSocket manager stopping")

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
        while self.running:
            try:
                process_id = build_process_id("websocket")
                set_process_id(process_id)

                log.info("Attempting WebSocket connection")
                await self.client.connect()
                self.reconnect_delay = self.min_reconnect_delay

                log.info("Syncing all entity states after WebSocket connection")
                self._sync_all_states()

                await self.client.subscribe_to_events(self._handle_event)

            except WebSocketConnectionError as e:
                log.error("WebSocket connection error", error=str(e))
            except Exception:
                log.exception("Unexpected WebSocket error")

            try:
                await self.client.close()
            except Exception:
                log.exception("Error closing WebSocket")

            if not self.running:
                break  # type:ignore[unreachable]

            log.warning("Attempting WebSocket reconnection", delay_seconds=self.reconnect_delay)
            await asyncio.sleep(self.reconnect_delay)
            self.reconnect_delay = min(self.reconnect_delay * 2, self.max_reconnect_delay)

    def _sync_all_states(self) -> None:
        """Fetch all entity states from Home Assistant to catch up after reconnection"""
        try:
            state_manager = StateManager()
            count = state_manager.fetch_all_hass_entities()
            log.info("State sync completed", entity_count=count)
        except Exception:
            log.exception("Failed to sync states after reconnection")

    def _handle_event(self, event: dict[str, Any]) -> None:
        """
        Route incoming WebSocket events to appropriate handlers.
        Reuses existing webhook handler functions.
        """
        from maestro.app import EventType, app

        event_type = event.get("event_type")
        if not event_type or not isinstance(event_type, str):
            raise WebSocketConnectionError("Malformed ")

        log.debug("WebSocket event received", event_type=event_type)

        request_body = self._build_request_body(event_type, event)

        # Route to appropriate handler (same handlers used by webhooks)
        handler_map: dict[EventType, Callable] = {
            EventType.STATE_CHANGED: handle_state_changed,
            EventType.IOS_NOTIF_ACTION: handle_notif_action,
            EventType.HASS_STARTED: handle_hass_startup,
            EventType.HASS_STOPPED: handle_hass_shutdown,
        }

        handler = handler_map.get(event_type, handle_event_fired)

        try:
            with app.app_context():
                handler(request_body)
        except Exception:
            log.exception("Error handling WebSocket event", event_type=event_type)

    def _build_request_body(self, event_type: str, event: dict[str, Any]) -> dict[str, Any]:
        """
        Convert WebSocket event format to webhook request_body format.
        This allows reuse of all existing webhook handler code.
        """
        from maestro.app import EventType

        # Extract common fields
        time_fired = event.get("time_fired")
        data = event.get("data", {})
        context = event.get("context", {})

        # Build base structure
        request_body = {
            "timestamp": time_fired,  # WebSocket uses time_fired for both
            "time_fired": time_fired,
            "event_type": event_type,
        }

        # Event-specific field mapping
        if event_type == EventType.STATE_CHANGED:
            # state_changed events have old_state and new_state in data
            old_state = data.get("old_state")
            new_state = data.get("new_state")

            request_body.update(
                {
                    "entity_id": data.get("entity_id"),
                    "old_state": old_state.get("state") if old_state else None,
                    "new_state": new_state.get("state") if new_state else None,
                    "old_attributes": old_state.get("attributes") if old_state else None,
                    "new_attributes": new_state.get("attributes") if new_state else None,
                }
            )

        elif event_type == EventType.IOS_NOTIF_ACTION:
            # iOS notification actions
            request_body.update(
                {
                    "user_id": context.get("user_id"),
                    "data": data,
                }
            )

        else:
            # Generic events
            request_body.update(
                {
                    "user_id": context.get("user_id"),
                    "data": data,
                }
            )

        return request_body
