import json
from collections.abc import Callable
from typing import Any

from aiohttp import ClientSession, ClientWebSocketResponse, ClientWSTimeout, WSMsgType

from maestro.config import HOME_ASSISTANT_TOKEN, HOME_ASSISTANT_URL
from maestro.utils.exceptions import WebSocketConnectionError
from maestro.utils.logging import log


class WebSocketClient:
    """
    Async WebSocket client for Home Assistant API.
    Handles authentication and event subscription.
    """

    def __init__(self) -> None:
        self.ws_url = (
            HOME_ASSISTANT_URL.replace("http://", "ws://").replace("https://", "wss://")
            + "/api/websocket"
        )
        self.session: ClientSession | None = None
        self.websocket: ClientWebSocketResponse | None = None
        self.message_id = 0
        self.authenticated = False

    async def connect(self) -> None:
        """Establish WebSocket connection to Home Assistant"""
        self.session = self.session or ClientSession()

        log.info("Connecting to Home Assistant WebSocket", url=self.ws_url)

        try:
            self.websocket = await self.session.ws_connect(
                url=self.ws_url,
                timeout=ClientWSTimeout(ws_close=10),
                heartbeat=10,
            )
        except Exception as e:
            raise WebSocketConnectionError(f"WebSocket connection failed: {e}") from e

        msg = await self._receive_message()
        if msg.get("type") != "auth_required":
            raise WebSocketConnectionError(f"Expected auth_required, got {msg.get('type')}")
        log.debug("Received auth_required message")

        await self._send_message({"type": "auth", "access_token": HOME_ASSISTANT_TOKEN})

        auth_response = await self._receive_message()
        if auth_response.get("type") == "auth_ok":
            self.authenticated = True
            log.info("WebSocket authenticated successfully")
        elif auth_response.get("type") == "auth_invalid":
            raise WebSocketConnectionError(f"Authentication failed: {auth_response.get('message')}")
        else:
            raise WebSocketConnectionError(f"Unexpected auth response: {auth_response.get('type')}")

    async def subscribe_to_events(self, callback: Callable[[dict[str, Any]], None]) -> None:
        """
        Subscribe to all Home Assistant events.
        Calls the callback function for each event received.
        """
        if not self.authenticated:
            raise WebSocketConnectionError("Must authenticate before subscribing")

        subscription_id = self._next_id()
        await self._send_message({"id": subscription_id, "type": "subscribe_events"})

        result = await self._receive_message()
        if result.get("id") != subscription_id or not result.get("success"):
            raise WebSocketConnectionError(f"Subscription failed: {result}")

        log.info("Subscribed to all Home Assistant events", subscription_id=subscription_id)

        await self._listen_for_events(subscription_id, callback)

    async def _listen_for_events(
        self,
        subscription_id: int,
        callback: Callable[[dict[str, Any]], None],
    ) -> None:
        """Process incoming event messages"""
        if self.websocket is None:
            raise WebSocketConnectionError("WebSocket not connected")

        async for msg in self.websocket:
            if msg.type == WSMsgType.TEXT:
                data = json.loads(msg.data)

                if data.get("id") == subscription_id and data.get("type") == "event":
                    event = data.get("event", {})
                    callback(event)

            elif msg.type == WSMsgType.CLOSED:
                log.warning("WebSocket connection closed by server")
                break
            elif msg.type == WSMsgType.ERROR:
                log.error("WebSocket error", error=self.websocket.exception())
                break

    async def close(self) -> None:
        """Close WebSocket connection"""
        if self.websocket:
            await self.websocket.close()
            self.websocket = None

        if self.session:
            await self.session.close()
            self.session = None

        self.authenticated = False
        log.info("WebSocket connection closed")

    async def _send_message(self, message: dict[str, Any]) -> None:
        """Send a message to Home Assistant"""
        if self.websocket is None:
            raise WebSocketConnectionError("WebSocket not connected")

        await self.websocket.send_json(message)
        log.debug("Sent WebSocket message", message_type=message.get("type"))

    async def _receive_message(self) -> dict[str, Any]:
        """Receive a message from Home Assistant"""
        if self.websocket is None:
            raise WebSocketConnectionError("WebSocket not connected")

        msg = await self.websocket.receive()

        if msg.type == WSMsgType.TEXT:
            if not isinstance(msg.data, str):
                raise TypeError
            data = json.loads(msg.data)
            if not isinstance(data, dict):
                raise TypeError
            return data
        elif msg.type == WSMsgType.CLOSED:
            raise WebSocketConnectionError("WebSocket closed during receive")
        elif msg.type == WSMsgType.ERROR:
            raise WebSocketConnectionError(f"WebSocket error: {self.websocket.exception()}")
        else:
            raise WebSocketConnectionError(f"Unexpected message type: {msg.type}")

    def _next_id(self) -> int:
        """Generate next message ID"""
        self.message_id += 1
        return self.message_id
