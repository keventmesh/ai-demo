import os
import signal
import sys

import requests
from cloudevents.conversion import to_binary
from cloudevents.http import CloudEvent
from flask import Flask, request

K_SINK = os.environ.get("K_SINK")
SOURCE_DECLARATION = os.environ.get("SOURCE_DECLARATION")

if not K_SINK:
    raise Exception("Missing K_SINK")
if not SOURCE_DECLARATION:
    raise Exception("Missing SOURCE_DECLARATION")

print(f"Going to send events to K_SINK: {K_SINK}")
print(f"Going to use CloudEvent source value as '{SOURCE_DECLARATION}'")


def handler(signal, frame):
    print('Gracefully shutting down')
    sys.exit(0)


signal.signal(signal.SIGINT, handler)
signal.signal(signal.SIGTERM, handler)

app = Flask(__name__)


@app.route("/", methods=["POST"])
def receive_feedback():
    # request body looks like this:
    # {
    #  "uploadId": "123",
    #  "feedback": 5
    # }

    print(f"Received request")

    body = request.json

    if 'uploadId' not in body:
        msg = f"'uploadId' not in request"
        print(msg)
        return msg, 400

    if 'feedback' not in body:
        msg = f"'feedback' not in request"
        print(msg)
        return msg, 400

    ce_data = {
        "uploadId": body['uploadId'],
        "feedback": int(body['feedback']),
    }

    ce_attributes = {
        "type": "com.knative.dev.feedback.event",
        "source": SOURCE_DECLARATION,
    }
    event = CloudEvent(ce_attributes, ce_data)

    # Creates the HTTP request representation of the CloudEvent in binary content mode
    headers, body = to_binary(event)

    try:
        print(f"Sending event with payload {str(ce_data)} to {K_SINK}")
        requests.post(K_SINK, data=body, headers=headers)
    except Exception as e:
        print(f"Failed to send event to {K_SINK} with error: {e}")
        return f"Failed to send event to {K_SINK}", 500

    return "", 204


if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
