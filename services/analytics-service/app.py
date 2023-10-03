import os
import signal
import sys

import psycopg2
from flask import Flask, request


def init_feedbacks_table():
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS feedbacks ('
                   'id serial PRIMARY KEY,'
                   'feedback INT NOT NULL,'
                   'upload_id VARCHAR(200) UNIQUE NOT NULL,'
                   'created_on TIMESTAMP DEFAULT CURRENT_TIMESTAMP);')
    conn.commit()
    cursor.close()


def init_predictions_table():
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS predictions ('
                   'id serial PRIMARY KEY,'
                   'probability DECIMAL(13, 12) NOT NULL,'
                   'upload_id VARCHAR(200) UNIQUE NOT NULL,'
                   'x0 DECIMAL(13, 12) NOT NULL,'
                   'x1 DECIMAL(13, 12) NOT NULL,'
                   'y0 DECIMAL(13, 12) NOT NULL,'
                   'y1 DECIMAL(13, 12) NOT NULL,'
                   'created_on TIMESTAMP DEFAULT CURRENT_TIMESTAMP);')
    conn.commit()
    cursor.close()


def handler(signal, frame):
    print('Gracefully shutting down')
    sys.exit(0)


conn = psycopg2.connect(
    host=os.environ['DB_HOST'],
    port=os.environ['DB_PORT'],
    database=os.environ['DB_DATABASE'],
    user=os.environ['DB_USERNAME'],
    password=os.environ['DB_PASSWORD']
)

init_feedbacks_table()
init_predictions_table()

signal.signal(signal.SIGINT, handler)
signal.signal(signal.SIGTERM, handler)

app = Flask(__name__)


@app.route("/feedbacks", methods=["POST"])
def receive_feedbacks():
    # request body looks like this:
    # {
    #   "feedback": <int>
    #   "uploadId": <string>
    # }

    print(f"Received request: {request.json}")

    body = request.json

    required_fields = ['feedback', 'uploadId']
    for x in required_fields:
        if x not in body:
            return f"'{x}' not in request", 400

    cur = conn.cursor()

    cur.execute('INSERT INTO feedbacks (feedback, upload_id) '
                'VALUES (%s, %s) '
                'ON CONFLICTS (upload_id) DO NOTHING',
                (body['feedback'], body['uploadId']))

    conn.commit()
    cur.close()

    return "", 204


@app.route("/predictions", methods=["POST"])
def receive_predictions():
    # request body looks like this:
    # {
    #     "uploadId": "deadbeef",
    #     "probability": "0.9012353451",
    #     "x0": "0.24543",
    #     "x1": "0.356647",
    #     "y0": "0.34543",
    #     "y1": "0.556647"
    # }

    print(f"Received request: {request.json}")

    body = request.json

    required_fields = ['probability', 'uploadId', 'x0', 'x1', 'y0', 'y1']
    for x in required_fields:
        if x not in body:
            return f"'{x}' not in request", 400

    cur = conn.cursor()

    cur.execute(
        'INSERT INTO predictions (probability, upload_id, x0, x1, y0, y1) '
        'VALUES (%s, %s, %s, %s, %s, %s) '
        'ON CONFLICTS (upload_id) DO NOTHING',
        (body['probability'], body['uploadId'], body['x0'], body['x1'], body['y0'], body['y1']))

    conn.commit()
    cur.close()

    return "", 204


if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
