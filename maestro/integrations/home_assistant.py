from dataclasses import dataclass
from http import HTTPMethod, HTTPStatus
from typing import Any

import requests

from maestro.config import HOME_ASSISTANT_TOKEN, HOME_ASSISTANT_URL
from maestro.domains.entity import Domain


@dataclass
class EntityState:
    entity_id: str
    state: str
    attributes: dict[str, Any]
    last_changed: str
    last_reported: str
    last_updated: str


class HomeAssistantProvider:
    def get_state(self, entity_id: str) -> EntityState | None:
        path = f"/api/states/{entity_id}"

        response_data, status = self.execute_request(method=HTTPMethod.GET, path=path)

        if status == HTTPStatus.NOT_FOUND:
            raise ValueError(f"Entity {entity_id} doesn't exist")
        if status != HTTPStatus.OK or not response_data or not isinstance(response_data, dict):
            raise ConnectionError(f"Failed to retrieve valid state for `{entity_id}`")

        entity_state = EntityState(
            entity_id=response_data.get("entity_id", ""),
            state=response_data.get("state", ""),
            attributes=response_data.get("attributes", {}),
            last_changed=response_data.get("last_changed", ""),
            last_reported=response_data.get("last_reported", ""),
            last_updated=response_data.get("last_updated", ""),
        )

        return entity_state

    def get_all_states(self) -> list[EntityState]:
        path = "/api/states"
        response_data, status = self.execute_request(
            method=HTTPMethod.GET,
            path=path,
        )

        if status != HTTPStatus.OK or not response_data or not isinstance(response_data, list):
            raise ConnectionError("Failed to retrieve states")

        entity_states = []
        for state_data in response_data:
            entity_state = EntityState(
                entity_id=state_data.get("entity_id", ""),
                state=state_data.get("state", ""),
                attributes=state_data.get("attributes", {}),
                last_changed=state_data.get("last_changed", ""),
                last_reported=state_data.get("last_reported", ""),
                last_updated=state_data.get("last_updated", ""),
            )
            entity_states.append(entity_state)

        return entity_states

    def set_state(self, entity_id: str, state: str, attributes: dict[str, Any]) -> EntityState:
        path = f"/api/states/{entity_id}"
        body = {"state": state, "attributes": attributes}

        response_data, status = self.execute_request(method=HTTPMethod.POST, path=path, body=body)

        if status not in (HTTPStatus.OK, HTTPStatus.CREATED):
            raise ConnectionError(f"Failed to set state for entity {entity_id}")

        if not isinstance(response_data, dict):
            raise ConnectionError(f"Expected dict response for entity {entity_id}")

        return EntityState(
            entity_id=response_data.get("entity_id", ""),
            state=response_data.get("state", ""),
            attributes=response_data.get("attributes", {}),
            last_changed=response_data.get("last_changed", ""),
            last_reported=response_data.get("last_reported", ""),
            last_updated=response_data.get("last_updated", ""),
        )

    def perform_action(
        self, domain: Domain, action: str, entity_id: str | list[str], **kwargs: Any
    ) -> list[EntityState]:
        path = f"/api/services/{domain}/{action}"
        body = {"entity_id": entity_id, **kwargs}

        response_data, status = self.execute_request(method=HTTPMethod.POST, path=path, body=body)

        if status != HTTPStatus.OK:
            raise ConnectionError(f"Failed to perform action {domain}.{action}")

        if not isinstance(response_data, list):
            raise ConnectionError(f"Expected list response for action {domain}.{action}")

        if not response_data:
            entity_ids = entity_id if isinstance(entity_id, list) else [entity_id]
            raise ValueError(f"No matching entities found for action {domain}.{action} on {entity_ids}")

        entity_states = []
        for state_data in response_data:
            if isinstance(state_data, dict):
                entity_state = EntityState(
                    entity_id=state_data.get("entity_id", ""),
                    state=state_data.get("state", ""),
                    attributes=state_data.get("attributes", {}),
                    last_changed=state_data.get("last_changed", ""),
                    last_reported=state_data.get("last_reported", ""),
                    last_updated=state_data.get("last_updated", ""),
                )
                entity_states.append(entity_state)

        return entity_states

    def delete_entity(self, entity_id: str) -> None:
        path = f"/api/states/{entity_id}"

        _, status = self.execute_request(method=HTTPMethod.DELETE, path=path)

        if status == HTTPStatus.NOT_FOUND:
            raise ValueError(f"Entity {entity_id} doesn't exist")
        if status != HTTPStatus.OK:
            raise ConnectionError(f"Failed to delete entity {entity_id}")

    def execute_request(self, method: HTTPMethod, path: str, body: dict | None = None) -> tuple[dict | list, int]:
        url = str(HOME_ASSISTANT_URL / path)
        headers = {
            "Authorization": f"Bearer {HOME_ASSISTANT_TOKEN}",
            "Content-Type": "application/json",
        }

        try:
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
