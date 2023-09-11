from threading import Lock
from flask import Flask, render_template, session, request
from flask_socketio import SocketIO, emit
from threading import Lock
from cloudevents.http import from_http

# Set this variable to "threading", "eventlet" or "gevent" to test the
# different async modes, or leave it set to None for the application to choose
# the best option based on installed packages.
async_mode = None

app = Flask(__name__)
socketio = SocketIO(app, async_mode=async_mode)

mutex = Lock()
# TODO: entries here actually need a TTL to prevent leaks
connections = {}  # sid -> request
prediction_reply_requests = {}  # upload_id -> sid


@app.route('/test')
def test_ui():
    return render_template('index.html', async_mode=socketio.async_mode)


@app.route("/", methods=["POST"])
def receive_cloud_event():
    event = from_http(request.headers, request.get_data())

    print(
        f"Found {event['id']} from {event['source']} with type "
        f"{event['type']} and specversion {event['specversion']}"
    )

    data = event.data
    upload_id = data['uploadId']
    with mutex:
        if upload_id in prediction_reply_requests:
            sid = prediction_reply_requests[upload_id]
            print("Found client waiting for reply", sid)
            socketio.emit('reply', data, room=sid)
            del prediction_reply_requests[upload_id]
            return "", 204
        else:
            print("No client waiting for reply")

    return "", 204


def register_client(request):
    with mutex:
        connections[request.sid] = request


def deregister_client(request):
    with mutex:
        del connections[request.sid]


@socketio.event
def connect():
    print("Client connected", request.sid)
    register_client(request)


@socketio.on('disconnect')
def disconnect():
    print('Client disconnected', request.sid)
    deregister_client(request)


@socketio.event
def request_prediction_reply(message):
    print("Received prediction reply request", message)
    upload_id = message['uploadId']
    print("Requested reply for Upload ID", upload_id)
    with mutex:
        prediction_reply_requests[upload_id] = request.sid


if __name__ == '__main__':
    socketio.run(app)
