import os
import signal
import sys
from threading import Lock

from cloudevents.http import from_http
from flask import Flask, render_template, request
from flask_cors import CORS, cross_origin
from flask_socketio import SocketIO


def handler(signal, frame):
    print('Gracefully shutting down')
    sys.exit(0)


signal.signal(signal.SIGINT, handler)
signal.signal(signal.SIGTERM, handler)

# Set this variable to "threading", "eventlet" or "gevent" to test the
# different async modes, or leave it set to None for the application to choose
# the best option based on installed packages.
async_mode = None

app = Flask(__name__)
socketio = SocketIO(app, async_mode=async_mode)
cors = CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'

mutex = Lock()
# TODO: entries here actually need a TTL to prevent leaks
prediction_reply_requests = {}  # upload_id -> request sid (client connection id)


@app.route('/test')
@cross_origin()
def test_ui():
    return render_template('index.html', async_mode=socketio.async_mode)


@app.route("/", methods=["POST"])
@cross_origin()
def receive_cloud_event():
    event = from_http(request.headers, request.get_data())

    print(
        f"Found {event['id']} from {event['source']} with type "
        f"{event['type']} and specversion {event['specversion']}"
    )

    data = event.data
    if 'uploadId' not in data:
        print("No upload ID in event data")
        return "No upload ID in event data", 500

    upload_id = data['uploadId']
    with mutex:
        if upload_id in prediction_reply_requests:
            if upload_id not in prediction_reply_requests:
                print("Upload ID not found in prediction reply requests")
                return "Upload ID not found in prediction reply requests", 500

            # this is the websocket sid of the client waiting for the reply
            sid = prediction_reply_requests[upload_id]
            print("Found client waiting for reply", sid)

            # send the reply to the client, with whatever we received as the data
            socketio.emit('reply', data, room=sid)

            # remove the client from the list of clients waiting for a reply
            del prediction_reply_requests[upload_id]

            return "", 204
        else:
            print("No client waiting for reply")

    return "", 204


@socketio.event
@cross_origin()
def request_prediction_reply(message):
    print("Received prediction reply request", message)
    if 'uploadId' not in message:
        # TODO: return error message to client over WS
        print("No upload ID in request")
        return

    upload_id = message['uploadId']
    print("Requested reply for Upload ID", upload_id)
    with mutex:
        prediction_reply_requests[upload_id] = request.sid
    return "ok"


if __name__ == '__main__':
    socketio.run(app, allow_unsafe_werkzeug=True, debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
