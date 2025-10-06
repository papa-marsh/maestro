import contextlib
from http import HTTPMethod, HTTPStatus
from typing import Any

import requests
from structlog.stdlib import get_logger

from maestro.config import DOMAIN_IGNORE_LIST, HOME_ASSISTANT_TOKEN, HOME_ASSISTANT_URL
from maestro.integrations.home_assistant.types import Domain, EntityData, EntityId
from maestro.utils.dates import resolve_timestamp

log = get_logger()


class HomeAssistantClient:
    """Client for interacting with Home Assistant REST API"""

    def check_health(self) -> bool:
        """Check if Home Assistant API is accessible and healthy"""
        path = "/api/"
        response_data, status = self.execute_request(method=HTTPMethod.GET, path=path)

        return (
            status == HTTPStatus.OK
            and isinstance(response_data, dict)
            and response_data.get("message") == "API running."
        )

    def get_entity(self, entity_id: str) -> EntityData:
        """Get the current state of a specific entity"""
        path = f"/api/states/{entity_id}"

        response_data, status = self.execute_request(method=HTTPMethod.GET, path=path)

        if status == HTTPStatus.NOT_FOUND:
            raise ValueError(f"Entity {entity_id} doesn't exist")
        if status != HTTPStatus.OK or not response_data or not isinstance(response_data, dict):
            raise ConnectionError(f"Failed to retrieve valid state for `{entity_id}`")

        return self.resolve_entity_response(response_data)

    def get_all_entities(self) -> list[EntityData]:
        """Get the current state of all entities"""
        path = "/api/states"
        response_data, status = self.execute_request(
            method=HTTPMethod.GET,
            path=path,
        )

        if status != HTTPStatus.OK or not response_data or not isinstance(response_data, list):
            raise ConnectionError("Failed to retrieve states")

        entities = []
        for state_data in response_data:
            if not isinstance(state_data, dict):
                raise TypeError("Unexpected non-dict in state response")
            if "entity_id" not in state_data or not isinstance(state_data["entity_id"], str):
                raise KeyError("Entity dictionary is missing entity_id")

            domain = state_data["entity_id"].split(".")[0]
            if domain in DOMAIN_IGNORE_LIST:
                continue

            entity = self.resolve_entity_response(state_data)
            entities.append(entity)

        return entities

    def set_entity(
        self,
        entity_id: str,
        state: str,
        attributes: dict[str, Any],
    ) -> tuple[EntityData, bool]:
        """Set the state and attributes of an entity. Returns (EntityData, created)"""
        path = f"/api/states/{entity_id}"
        body = {
            "state": state,
            "attributes": attributes,
        }

        response_data, status = self.execute_request(
            method=HTTPMethod.POST,
            path=path,
            body=body,
        )

        if status not in (HTTPStatus.OK, HTTPStatus.CREATED):
            raise ConnectionError(f"Failed to set state for entity {entity_id}")

        if not isinstance(response_data, dict):
            raise ConnectionError(f"Expected dict response for entity {entity_id}")

        entity = self.resolve_entity_response(response_data)
        created = status == HTTPStatus.CREATED

        return entity, created

    def delete_entity(self, entity_id: str) -> None:
        """Delete an entity from Home Assistant"""
        path = f"/api/states/{entity_id}"

        _, status = self.execute_request(method=HTTPMethod.DELETE, path=path)

        if status == HTTPStatus.NOT_FOUND:
            raise ValueError(f"Entity {entity_id} doesn't exist")
        if status != HTTPStatus.OK:
            raise ConnectionError(f"Failed to delete entity {entity_id}")

    def delete_entity_if_exists(self, entity_id: str) -> None:
        """Delete an entity if it exists, ignoring errors if it doesn't exist"""
        with contextlib.suppress(ValueError):
            self.delete_entity(entity_id)

    def perform_action(
        self,
        domain: Domain,
        action: str,
        entity_id: str | list[str] | None = None,
        **body_params: Any,
    ) -> list[EntityData]:
        """Perform an action on one or more entities"""
        path = f"/api/services/{domain}/{action}"
        if entity_id is not None:
            body_params["entity_id"] = entity_id

        response_data, status = self.execute_request(
            method=HTTPMethod.POST,
            path=path,
            body=body_params,
        )

        if status != HTTPStatus.OK:
            raise ConnectionError(f"Failed to perform action {domain}.{action}")

        if not isinstance(response_data, list):
            raise ConnectionError(f"Expected list response for action {domain}.{action}")

        entities = []
        for state_data in response_data:
            if not isinstance(state_data, dict):
                raise TypeError("Unexpected non-dict in state response")

            entity = self.resolve_entity_response(state_data)
            entities.append(entity)

        return entities

    def execute_request(
        self,
        method: HTTPMethod,
        path: str,
        body: dict | None = None,
    ) -> tuple[dict | list, int]:
        """Execute an HTTP request to the Home Assistant API"""
        url = f"{HOME_ASSISTANT_URL}{path}"
        headers = {
            "Authorization": f"Bearer {HOME_ASSISTANT_TOKEN}",
            "Content-Type": "application/json",
        }

        try:
            log.info("Sending request to Home Assistant", method=method, path=path)
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                json=body,
                timeout=5,
            )
            data = response.json() if response.content else {}

        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Network error: {e}") from e
        except requests.exceptions.JSONDecodeError:
            data = {}

        return data, response.status_code

    @staticmethod
    def resolve_entity_response(raw_dict: dict) -> EntityData:
        """Convert raw API response data to EntityData object"""
        keys = {
            "entity_id",
            "state",
            "attributes",
            "last_changed",
            "last_reported",
            "last_updated",
        }
        if not all(key in raw_dict for key in keys):
            raise KeyError("Couldn't resolve EntityData. Missing required keys.")

        entity = EntityData(
            entity_id=EntityId(raw_dict["entity_id"]),
            state=str(raw_dict["state"]),
            attributes=raw_dict["attributes"] or {},
        )
        entity.attributes["last_changed"] = resolve_timestamp(raw_dict["last_changed"])
        entity.attributes["last_reported"] = resolve_timestamp(raw_dict["last_reported"])
        entity.attributes["last_updated"] = resolve_timestamp(raw_dict["last_updated"])

        return entity
