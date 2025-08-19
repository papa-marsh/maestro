import json
import logging

from flask import Flask, jsonify, request

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)


@app.route("/")
def hello_world():
    app.logger.info("Hello World")
    return "<p>Hello, World!</p>"


@app.route("/events", methods=["POST"])
def handle_event():
    try:
        app.logger.info("Event received and processing")
        request_body = request.get_json() or {}
        app.logger.info(f"Request body: {json.dumps(request_body, indent=2)}")
        return jsonify({'status': 'success', 'message': 'Event processed'})
    except Exception as e:
        app.logger.error(f"Error processing event: {e}")
        return jsonify({'error': 'Internal server error'}), 500
