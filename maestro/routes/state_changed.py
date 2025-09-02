import json
import re
from dataclasses import dataclass
from typing import Any

from flask import Response, current_app, jsonify, request


@dataclass
class StateChangeState:
    state: str
    attributes: dict[str, Any]


@dataclass
class StateChange:
    entity_id: str
    new_state: StateChangeState
    old_state: StateChangeState


def handle_state_changed() -> tuple[Response, int] | Response:
    try:
        request_body = request.get_json() or {}
        app.logger.info(f"Request body: {json.dumps(request_body, indent=2)}")

        # Parse event_data if it's a string representation of a dict
        if "event_data" in request_body and isinstance(request_body["event_data"], str):
            event_data_str = request_body["event_data"]
            parsed_data = {}

            # Extract entity_id
            entity_match = re.search(r"'entity_id':\s*'([^']+)'", event_data_str)
            if entity_match:
                parsed_data["entity_id"] = entity_match.group(1)

            # Extract old_state
            old_state_match = re.search(r"'old_state':\s*(<state[^>]+>)", event_data_str)
            if old_state_match:
                parsed_data["old_state"] = parse_state_object(old_state_match.group(1))

            # Extract new_state
            new_state_match = re.search(r"'new_state':\s*(<state[^>]+>)", event_data_str)
            if new_state_match:
                parsed_data["new_state"] = parse_state_object(new_state_match.group(1))

            request_body["event_data"] = parsed_data
            app.logger.info(f"Parsed event_data: {parsed_data}")

        return jsonify({"status": "success", "message": "Event processed"})
    except Exception as e:
        app.logger.error(f"Error processing event: {e}")
        return jsonify({"error": "Internal server error"}), 500


def parse_state_object(state_str: str) -> dict[str, Any] | None:
    """
    Parse a state object string.
    Example: '<state sensor.memory_free=713.3; attr1=val1, attr2=val2 @ timestamp>'
    """
    state_match = re.search(r"<state\s+[^=]+=([^;]+);([^@]+)@", state_str)
    if not state_match:
        return None

    state_value = state_match.group(1).strip()
    attributes_str = state_match.group(2).strip()

    # Parse attributes
    attributes = {}
    if attributes_str:
        attr_pairs = re.findall(r"(\w+)=([^,]+)", attributes_str)
        for key, value in attr_pairs:
            # Clean up the value and try to convert to appropriate type
            value = value.strip()
            # Try to convert to number if possible
            try:
                if "." in value:
                    attributes[key] = float(value)
                else:
                    attributes[key] = int(value)
            except ValueError:
                # Keep as string, but remove any quotes
                attributes[key] = value.strip("'\"")

    return {
        "state": state_value,
        "attributes": attributes,
    }
