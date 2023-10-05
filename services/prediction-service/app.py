import io
import os
import signal
import sys
import time

import boto3
import botocore
import numpy as np
import requests
from PIL import Image
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
INFERENCE_SERVICE_URL = os.environ.get("INFERENCE_SERVICE_URL")
INFERENCE_SERVICE_MODEL_NAME = os.environ.get("INFERENCE_SERVICE_MODEL_NAME")

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
if not INFERENCE_SERVICE_URL:
    raise Exception("Missing INFERENCE_SERVICE_URL")
if not INFERENCE_SERVICE_MODEL_NAME:
    raise Exception("Missing INFERENCE_SERVICE_MODEL_NAME")

print(f"Going to use CloudEvent source value as '{SOURCE_DECLARATION}'")
print(f"Going to use inference service URL as '{INFERENCE_SERVICE_URL}'")
print(f"Going to use inference service model name as '{INFERENCE_SERVICE_MODEL_NAME}'")
print(f"Going to use S3 endpoint URL as '{S3_ENDPOINT_URL}'")
print(f"Going to use S3 bucket name as '{S3_BUCKET_NAME}'")

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

    bucket = record["bucket"]
    upload_id = record["object"]

    try:
        obj = s3.get_object(Bucket=bucket, Key=upload_id)
    except Exception as e:
        print(f"Failed to get object {upload_id} from bucket {bucket}: {e}")
        return "Failed to get object", 500

    try:
        content = obj["Body"].read()
    except Exception as e:
        print(f"Failed to read object body {upload_id} from bucket {bucket}: {e}")
        return "Failed to read object body", 500

    print(f"Fetched image content of length {len(content)} for upload ID {upload_id}")

    print(f"Calling inference service for upload ID {upload_id}")
    call_start_time = time.time()

    image = Image.open(io.BytesIO(content))
    image_np = np.array(image)
    # drop alpha channel
    image_np = image_np[:, :, :3]

    URL = f'{INFERENCE_SERVICE_URL}/v1/models/{INFERENCE_SERVICE_MODEL_NAME}:predict'
    payload = {'instances': [image_np.tolist()]}

    try:
        response = requests.post(URL, json=payload)
        if response.status_code >= 300:
            print(f"Failed to call inference service for uploadId {upload_id} with status code: {response.status_code}")
            return f"Failed to call inference service", 500
    except Exception as e:
        print(f"Failed to call inference service for uploadId {upload_id}")
        print(e)
        return "Failed to call inference service", 500

    call_end_time = time.time()
    print('Inference call took {} seconds'.format(call_end_time - call_start_time))

    inference = response.json()

    if "predictions" not in inference:
        print(f"Failed to get predictions from inference service for uploadId {upload_id}")
        return "Failed to get predictions from inference service", 500

    # we only call with one image, so we only have one prediction
    predictions = inference['predictions'][0]

    if "num_detections" not in predictions or int(predictions["num_detections"]) == 0:
        ce_data = {
            "uploadId": upload_id,
            "probability": 0,
            "x0": "0",
            "x1": "0",
            "y0": "0",
            "y1": "0"
        }
    else:
        # highest score is the first one
        if "detection_scores" in predictions and len(predictions["detection_scores"]) > 0:
            highest_score = predictions["detection_scores"][0]
        else:
            highest_score = 0

        if "detection_boxes" in predictions and len(predictions["detection_boxes"]) > 0:
            highest_score_box = predictions["detection_boxes"][0]
        else:
            highest_score_box = [0, 0, 0, 0]

        ce_data = {
            "uploadId": upload_id,
            "probability": highest_score,
            # weird that Ys come first
            "y0": highest_score_box[0],
            "x0": highest_score_box[1],
            "y1": highest_score_box[2],
            "x1": highest_score_box[3],
        }

    print(f"Returning prediction result for upload ID {upload_id}: {ce_data}")

    ce_attributes = {
        "type": "eventmesh.ai-demo.prediction",
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
