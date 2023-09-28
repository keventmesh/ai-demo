import os
import signal
import sys
from threading import Lock

from cachetools import TTLCache
from cloudevents.http import from_http
from flask import Flask, render_template, request
from flask_cors import CORS, cross_origin
from flask_socketio import SocketIO

MAX_ITEMS_IN_CACHES = int(os.environ.get("MAX_ITEMS_IN_CACHES", 1000 * 1000))  # 1M client erquests, 1M predictions
CACHE_ITEM_TTL_IN_SECONDS = int(os.environ.get("CACHE_ITEM_TTL_IN_SECONDS", 5 * 60))  # 5 minutes


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

# upload_id -> data
replies = TTLCache(
    maxsize=MAX_ITEMS_IN_CACHES,
    ttl=CACHE_ITEM_TTL_IN_SECONDS
)

# upload_id -> client id (called sid in socketio)
client_prediction_reply_requests = TTLCache(
    maxsize=MAX_ITEMS_IN_CACHES,
    ttl=CACHE_ITEM_TTL_IN_SECONDS
)


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
        replies[upload_id] = data

        # cases:
        # 1. we just received a prediction for uploadId, and there is a client waiting for the reply
        #   - send the reply to the client
        #   - remove the client from the list of clients waiting for a reply
        #   - remove the reply from replies list
        # 2. we just received a prediction for uploadId, but there is no client waiting for the reply
        #   - store the reply in replies list
        #   - (in the websocket handler) when a client requests the reply, send it to the client immediately

        if upload_id not in client_prediction_reply_requests:
            print("No client waiting for reply, storing the data for future client requests")
        else:
            # this is the websocket sid of the client waiting for the reply
            sid = client_prediction_reply_requests[upload_id]
            print(f"Found client {sid} waiting for reply for the upload, sending the reply")

            # send the reply to the client, with whatever we received as the data
            socketio.emit('reply', data, room=sid)

            # remove the client from the list of clients waiting for a reply
            del client_prediction_reply_requests[upload_id]
            del replies[upload_id]

    return "", 204


@socketio.event
@cross_origin()
def request_prediction_reply(message):
    print("Received prediction reply request", message)
    if 'uploadId' not in message:
        # TODO: return error message to client over WS
        print("No upload ID in request")
        return

    # cases:
    # 1. we already have a reply for the given uploadId:
    #   - send the reply to the client
    #   - remove the reply from replies list
    #   - remove the client from the list of clients waiting for a reply (shouldn't be there, but just in case)
    # 2. we don't have a reply for the given uploadId yet:
    #   - store the client in the list of clients waiting for a reply
    #   - (in the HTTP handler) when a reply is received, send it to the client immediately

    upload_id = message['uploadId']
    print("Requested reply for Upload ID", upload_id)

    with mutex:
        if upload_id in replies:
            print(f"Found reply for upload ID {upload_id}, sending it to the client")
            socketio.emit('reply', replies[upload_id], room=request.sid)
            del replies[upload_id]
            client_prediction_reply_requests.pop(upload_id, None)  # remove if exists
        else:
            print(f"No reply for upload ID {upload_id} yet, storing the client for future replies")
            client_prediction_reply_requests[upload_id] = request.sid

    return "ok"


if __name__ == '__main__':
    socketio.run(app, allow_unsafe_werkzeug=True, debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
