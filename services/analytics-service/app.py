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
                   'upload_id VARCHAR(200) NOT NULL,'
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

signal.signal(signal.SIGINT, handler)
signal.signal(signal.SIGTERM, handler)

app = Flask(__name__)


@app.route("/feedbacks", methods=["POST"])
def receive_event():
    # request body looks like this:
    # {
    #   "feedback": <int>
    #   "upload_id": <string>
    # }

    print(f"Received request: {request.json}")

    body = request.json

    if 'feedback' not in body:
        return f"'feedback' not in request", 400

    if 'upload_id' not in body:
        return f"'upload_id' not in request", 400

    cur = conn.cursor()

    cur.execute('INSERT INTO feedbacks (feedback, upload_id) VALUES (%s, %s)',
                (body['feedback'], body['upload_id']))

    conn.commit()
    cur.close()

    return "", 204


if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
