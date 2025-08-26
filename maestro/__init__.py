import json
import logging
import re

from flask import Flask, Response, jsonify, request

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)


@app.route("/")
def hello_world() -> str:
    app.logger.info("Hello World")
    return "<p>Hello, World!</p>"


@app.route("/events/state_changed", methods=["POST"])
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

            # Extract states (simplified - just get the state value)
            old_state_match = re.search(r"'old_state':\s*<state\s+[^=]+=([^;]+);", event_data_str)
            if old_state_match:
                parsed_data["old_state"] = old_state_match.group(1)

            new_state_match = re.search(r"'new_state':\s*<state\s+[^=]+=([^;]+);", event_data_str)
            if new_state_match:
                parsed_data["new_state"] = new_state_match.group(1)

            request_body["event_data"] = parsed_data
            app.logger.info(f"Parsed event_data: {parsed_data}")

        return jsonify({"status": "success", "message": "Event processed"})
    except Exception as e:
        app.logger.error(f"Error processing event: {e}")
        return jsonify({"error": "Internal server error"}), 500
