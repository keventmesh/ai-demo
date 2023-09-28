import os
import random
import signal
import sys

import boto3
import botocore
from cloudevents.conversion import to_binary
from cloudevents.http import CloudEvent
from cloudevents.http import from_http
from flask import Flask, request, make_response
from flask_cors import CORS, cross_origin

S3_ENDPOINT_URL = os.environ.get("S3_ENDPOINT_URL")
S3_ACCESS_KEY_ID = os.environ.get("S3_ACCESS_KEY_ID")
S3_ACCESS_KEY_SECRET = os.environ.get("S3_ACCESS_KEY_SECRET")
S3_ACCESS_SSL_VERIFY = os.environ.get("S3_ACCESS_SSL_VERIFY", "true").lower() == "true"
S3_BUCKET_NAME = os.environ.get("S3_BUCKET_NAME")
SOURCE_DECLARATION = os.environ.get("SOURCE_DECLARATION")

if not S3_ENDPOINT_URL:
    raise Exception("Missing S3_ENDPOINT_URL")
if not S3_ACCESS_KEY_ID:
    raise Exception("Missing S3_ACCESS_KEY_ID")
if not S3_ACCESS_KEY_SECRET:
    raise Exception("Missing S3_ACCESS_KEY_SECRET")
if not S3_BUCKET_NAME:
    raise Exception("Missing S3_BUCKET_NAME")
if not SOURCE_DECLARATION:
    raise Exception("Missing SOURCE_DECLARATION")

print(f"Going to use CloudEvent source value as '{SOURCE_DECLARATION}'")

app = Flask(__name__)
cors = CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'

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


def handler(signal, frame):
    print('Gracefully shutting down')
    sys.exit(0)


signal.signal(signal.SIGINT, handler)
signal.signal(signal.SIGTERM, handler)


@app.post("/")
@cross_origin()
def prediction_request():
    print("Received request")

    event = from_http(request.headers, request.get_data())

    print(
        f"Found {event['id']} from {event['source']} with type "
        f"{event['type']} and specversion {event['specversion']}"
    )

    data = event.data

    if "event" not in data:
        return "Missing event", 400

    if data["event"] != "s3:ObjectCreated:Put":
        print(f'Ignoring unhandled event type f{data["event"]}')
        return f'Ignoring unhandled event type f{data["event"]}', 200

    if "records" not in data:
        return "Missing records", 400

    records = data["records"]
    if len(records) == 0:
        return "No records", 400

    # TODO: only use the first record for now

    record = records[0]
    if "bucket" not in record:
        return "Missing bucket", 400

    if "object" not in record:
        return "Missing object", 400

    # TODO: error handling
    object = s3.get_object(Bucket=record["bucket"], Key=record["object"])

    # TODO: pass this to inference service
    content = object["Body"].read()

    print("Received content of length", len(content))

    ce_data = {
        "uploadId": "deadbeef",
        "probability": random.random() + 0.2,  # 70 chance of being positive
        "x0": "0.24543",
        "x1": "0.556647",
        "y0": "0.34543",
        "y1": "0.656647"
    }

    ce_attributes = {
        "type": "com.knative.dev.prediction.event",
        "source": SOURCE_DECLARATION,
    }
    event = CloudEvent(ce_attributes, ce_data)

    # Creates the HTTP request representation of the CloudEvent in binary content mode
    headers, body = to_binary(event)

    resp = make_response(body, 200)
    for header, value in headers.items():
        resp.headers[header] = value

    return resp


if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
