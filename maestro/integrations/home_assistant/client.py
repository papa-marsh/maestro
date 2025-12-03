from contextlib import suppress
from http import HTTPMethod, HTTPStatus
from typing import Any

import requests
from requests.exceptions import JSONDecodeError, RequestException

from maestro.config import DOMAIN_IGNORE_LIST, HOME_ASSISTANT_TOKEN, HOME_ASSISTANT_URL
from maestro.integrations.home_assistant.domain import Domain
from maestro.integrations.home_assistant.types import EntityData, EntityId
from maestro.utils.dates import resolve_timestamp, serialize_datetimes
from maestro.utils.exceptions import (
    EntityDoesNotExistError,
    EntityOperationError,
    HomeAssistantClientError,
    MalformedResponseError,
)
from maestro.utils.logging import log


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
            raise EntityDoesNotExistError(f"Entity `{entity_id}` doesn't exist")
        if status != HTTPStatus.OK:
            raise HomeAssistantClientError(f"Request failed fetching entity `{entity_id}`")
        if not response_data or not isinstance(response_data, dict):
            raise MalformedResponseError(f"Invalid response shape fetching entity `{entity_id}`")

        return self.resolve_entity_response(response_data)

    def get_all_entities(self) -> list[EntityData]:
        """Get the current state of all entities"""
        path = "/api/states"
        response_data, status = self.execute_request(
            method=HTTPMethod.GET,
            path=path,
        )

        if status != HTTPStatus.OK:
            raise HomeAssistantClientError("Request failed fetching all entities")
        if not response_data or not isinstance(response_data, list):
            raise MalformedResponseError("Invalid response shape fetching all entities")

        entities = []
        for state_data in response_data:
            if not isinstance(state_data, dict):
                raise MalformedResponseError("Unexpected non-dict in state response")
            if "entity_id" not in state_data or not isinstance(state_data["entity_id"], str):
                raise MalformedResponseError("Entity dictionary is missing entity_id string")

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
            "attributes": serialize_datetimes(attributes),
        }

        response_data, status = self.execute_request(
            method=HTTPMethod.POST,
            path=path,
            body=body,
        )

        if status not in (HTTPStatus.OK, HTTPStatus.CREATED):
            raise EntityOperationError(f"Failed to set state for entity {entity_id}")

        if not isinstance(response_data, dict):
            raise MalformedResponseError(f"Expected dict response for entity {entity_id}")

        entity = self.resolve_entity_response(response_data)
        created = status == HTTPStatus.CREATED

        return entity, created

    def delete_entity(self, entity_id: str) -> None:
        """Delete an entity from Home Assistant"""
        path = f"/api/states/{entity_id}"

        _, status = self.execute_request(method=HTTPMethod.DELETE, path=path)

        if status == HTTPStatus.NOT_FOUND:
            raise EntityDoesNotExistError(f"Entity {entity_id} doesn't exist")
        if status != HTTPStatus.OK:
            raise EntityOperationError(f"Failed to delete entity {entity_id}")

    def delete_entity_if_exists(self, entity_id: str) -> None:
        """Delete an entity if it exists, ignoring errors if it doesn't exist"""
        with suppress(EntityDoesNotExistError):
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
            raise EntityOperationError(
                f"Failed to perform action {domain}.{action}: "
                f"status={status}, response={response_data}"
            )

        if not isinstance(response_data, list):
            raise MalformedResponseError(f"Expected list response for action {domain}.{action}")

        entities = []
        for state_data in response_data:
            if not isinstance(state_data, dict):
                raise MalformedResponseError("Unexpected non-dict in state response")

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
            log.info("Sending request to Home Assistant", method=method, path=path, body=body)
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                json=body,
                timeout=5,
            )
            data = response.json() if response.content else {}

        except (JSONDecodeError, RequestException) as e:
            raise HomeAssistantClientError(f"Network error: {e}") from e
        if response.status_code >= 500:
            raise HomeAssistantClientError("Home Assistant server error")

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
            raise MalformedResponseError("Couldn't resolve EntityData. Missing required keys.")

        state = raw_dict["state"]
        entity_id = EntityId(raw_dict["entity_id"])

        if not isinstance(state, str):
            log.info(
                "Casting fetched entity state to string",
                entity_id=entity_id,
                state=state,
                type=type(state),
            )
            state = str(state)

        entity = EntityData(
            entity_id=entity_id,
            state=state,
            attributes=raw_dict["attributes"] or {},
        )
        entity.attributes["last_changed"] = resolve_timestamp(raw_dict["last_changed"])
        entity.attributes["last_reported"] = resolve_timestamp(raw_dict["last_reported"])
        entity.attributes["last_updated"] = resolve_timestamp(raw_dict["last_updated"])

        return entity
