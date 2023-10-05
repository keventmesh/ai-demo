import base64
import io
import os
import signal
import sys
import uuid

import boto3
import botocore
from flask import Flask, request, render_template
import psycopg2

S3_ENDPOINT_URL = os.environ.get("S3_ENDPOINT_URL")
S3_ACCESS_KEY_ID = os.environ.get("S3_ACCESS_KEY_ID")
S3_ACCESS_KEY_SECRET = os.environ.get("S3_ACCESS_KEY_SECRET")
S3_ACCESS_SSL_VERIFY = os.environ.get("S3_ACCESS_SSL_VERIFY", "true").lower() == "true"
S3_BUCKET_NAME = os.environ.get("S3_BUCKET_NAME")
DB_HOST = os.environ.get("DB_HOST")
DB_PORT = os.environ.get("DB_PORT")
DB_DATABASE = os.environ.get("DB_DATABASE")
DB_USERNAME = os.environ.get("DB_USERNAME")
DB_PASSWORD = os.environ.get("DB_PASSWORD")

if not S3_ENDPOINT_URL:
    raise Exception("Missing S3_ENDPOINT_URL")
if not S3_ACCESS_KEY_ID:
    raise Exception("Missing S3_ACCESS_KEY_ID")
if not S3_ACCESS_KEY_SECRET:
    raise Exception("Missing S3_ACCESS_KEY_SECRET")
if not S3_BUCKET_NAME:
    raise Exception("Missing S3_BUCKET_NAME")
if not DB_HOST:
    raise Exception("Missing DB_HOST")
if not DB_PORT:
    raise Exception("Missing DB_PORT")
if not DB_DATABASE:
    raise Exception("Missing DB_DATABASE")
if not DB_USERNAME:
    raise Exception("Missing DB_USERNAME")
if not DB_PASSWORD:
    raise Exception("Missing DB_PASSWORD")

app = Flask(__name__)

boto_config = botocore.client.Config(connect_timeout=5, retries={'max_attempts': 1})

# https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3.html
s3 = boto3.client(
    's3',
    config=boto_config,
    endpoint_url=S3_ENDPOINT_URL,
    aws_access_key_id=S3_ACCESS_KEY_ID,
    aws_secret_access_key=S3_ACCESS_KEY_SECRET,
    verify=S3_ACCESS_SSL_VERIFY,
)

# check if the bucket exists
try:
    # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3/client/head_bucket.html
    s3.head_bucket(Bucket=S3_BUCKET_NAME)
except Exception as e:
    print(e)
    raise Exception(f"Bucket {S3_BUCKET_NAME} does not exist")

conn = psycopg2.connect(
    host=os.environ['DB_HOST'],
    port=os.environ['DB_PORT'],
    database=os.environ['DB_DATABASE'],
    user=os.environ['DB_USERNAME'],
    password=os.environ['DB_PASSWORD']
)


def handler(signal, frame):
    print('Gracefully shutting down')
    sys.exit(0)


signal.signal(signal.SIGINT, handler)
signal.signal(signal.SIGTERM, handler)


@app.get("/case")
def renderCase():
    upload_id = request.args.get('uploadId')
    if not upload_id:
        return "Missing uploadId", 400

    print(f"Received request for upload id: {upload_id}")

    try:
        obj = s3.get_object(Bucket=S3_BUCKET_NAME, Key=upload_id)
    except Exception as e:
        print(f"Failed to get object {upload_id} from bucket {S3_BUCKET_NAME}: {e}")
        return "Failed to get object", 500

    try:
        image_base64 = base64.b64encode(obj["Body"].read())
        image_base64 = image_base64.decode("utf-8")
        # image_base64 is like this: "/9j/4A............................f/Z"
    except Exception as e:
        print(f"Failed to read object body {upload_id} from bucket {S3_BUCKET_NAME}: {e}")
        return "Failed to read object body", 500

    print(f"Fetched image content of bas64 decoded length {len(image_base64)} for upload ID {upload_id}")

    cur = conn.cursor()
    print(f"Fetching feedback for upload {upload_id}")
    cur.execute('SELECT feedback, created_on from feedbacks where upload_id = %s', (upload_id,))
    feedback = cur.fetchone()
    cur.close()
    print(f"Feedback for upload {upload_id} is {feedback}")

    cur = conn.cursor()
    print(f"Fetching prediction for upload {upload_id}")
    cur.execute('SELECT probability, x0, x1, y0, y1, created_on from predictions where upload_id = %s', (upload_id,))
    prediction = cur.fetchone()
    cur.close()
    print(f"Predictions for upload {upload_id} is {prediction}")

    if feedback is not None:
        feedback = {
            "feedback": feedback[0],
            "feedbackDate": int(feedback[1].timestamp() * 1000),
        }

    if prediction is not None:
        prediction = {
            "probability": prediction[0],
            "x0": prediction[1],
            "x1": prediction[2],
            "y0": prediction[3],
            "y1": prediction[4],
            "predictionDate": int(prediction[5].timestamp() * 1000),
        }

    data = {
        "uploadId": upload_id,
        "image": image_base64,
        "prediction": prediction,
        "feedback": feedback,
    }

    print(data["prediction"])
    print(data["feedback"])

    return render_template('index.html', data=data)


if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
