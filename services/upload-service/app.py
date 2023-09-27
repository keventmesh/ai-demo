import base64
import io
import os
import signal
import sys
import uuid

import boto3
import botocore
from PIL import Image
from flask import Flask, request
from flask_cors import CORS, cross_origin

MAX_IMG_SIZE_IN_BYTES = int(os.environ.get("MAX_IMG_SIZE_IN_BYTES", 1000 * 1000))
MAX_IMG_WIDTH = int(os.environ.get("MAX_IMG_WIDTH", 640))
MAX_IMG_HEIGHT = int(os.environ.get("MAX_IMG_HEIGHT", 640))

S3_ENDPOINT_URL = os.environ.get("S3_ENDPOINT_URL")
S3_ACCESS_KEY_ID = os.environ.get("S3_ACCESS_KEY_ID")
S3_ACCESS_KEY_SECRET = os.environ.get("S3_ACCESS_KEY_SECRET")
S3_ACCESS_SSL_VERIFY = os.environ.get("S3_ACCESS_SSL_VERIFY", "true").lower() == "true"
S3_BUCKET_NAME = os.environ.get("S3_BUCKET_NAME")

if not S3_ENDPOINT_URL:
    raise Exception("Missing S3_ENDPOINT_URL")
if not S3_ACCESS_KEY_ID:
    raise Exception("Missing S3_ACCESS_KEY_ID")
if not S3_ACCESS_KEY_SECRET:
    raise Exception("Missing S3_ACCESS_KEY_SECRET")
if not S3_BUCKET_NAME:
    raise Exception("Missing S3_BUCKET_NAME")

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
def upload_request():
    print("Received request")

    # set req size limit in Flask
    # https://stackoverflow.com/questions/25036498/is-it-possible-to-limit-flask-post-data-size-on-a-per-route-basis
    content_length = request.content_length
    if content_length is None:
        return "Missing content-length", 400

    if content_length > MAX_IMG_SIZE_IN_BYTES:
        return f"Request length too large {content_length / 1024:.2f} KB", 400

    if "image_b64" not in request.json:
        return "Missing image_b64", 400

    image_base64 = request.json["image_b64"]

    if len(image_base64) > MAX_IMG_SIZE_IN_BYTES:
        return f"Image too large {len(image_base64) / 1024:.2f} KB", 400

    try:
        base64_decoded = base64.b64decode(image_base64)
    except Exception as e:
        print(e)
        return f"Failed to decode image", 400

    try:
        image = Image.open(io.BytesIO(base64_decoded))
    except Exception as e:
        print(e)
        return f"Failed to load the image", 400

    width, height = image.size
    if width > MAX_IMG_WIDTH or height > MAX_IMG_HEIGHT:
        return f"Image too wide or tall {width}x{height}", 400

    upload_id = uuid.uuid4().hex

    try:
        s3.put_object(Bucket=S3_BUCKET_NAME, Key=upload_id, Body=base64_decoded)
    except Exception as e:
        print(e)
        return f"Failed to upload", 500

    return {
        "uploadId": upload_id
    }, 200


if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
