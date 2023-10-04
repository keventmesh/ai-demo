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
def receive_event():
    # request body looks like this:
    # {
    #   "EventName": "s3:ObjectCreated:Put",
    #   "Key": "ai-demo/service.yaml",
    #   "Records": [
    #     {
    #       "eventVersion": "2.0",
    #       "eventSource": "minio:s3",
    #       "awsRegion": "",
    #       "eventTime": "2023-09-26T09:38:47.702Z",
    #       "eventName": "s3:ObjectCreated:Put",
    #       "userIdentity": {
    #         "principalId": "minio"
    #       },
    #       "requestParameters": {
    #         "principalId": "minio",
    #         "region": "",
    #         "sourceIPAddress": "[::1]"
    #       },
    #       "responseElements": {
    #         "x-amz-id-2": "dd9025bab4ad464b049177c95eb6ebf374d3b3fd1af9251148b658df7ac2e3e8",
    #         "x-amz-request-id": "178869619B8B3C05",
    #         "x-minio-deployment-id": "639f7c63-1965-4710-b8fe-e6b1b47e2e09",
    #         "x-minio-origin-endpoint": "https://minio.minio-operator.svc.cluster.local"
    #       },
    #       "s3": {
    #         "s3SchemaVersion": "1.0",
    #         "configurationId": "Config",
    #         "bucket": {
    #           "name": "ai-demo",
    #           "ownerIdentity": {
    #             "principalId": "minio"
    #           },
    #           "arn": "arn:aws:s3:::ai-demo"
    #         },
    #         "object": {
    #           "key": "service.yaml",
    #           "size": 576,
    #           "eTag": "702314f405adeaa9aa042985692cd49e",
    #           "contentType": "text/yaml",
    #           "userMetadata": {
    #             "content-type": "text/yaml"
    #           },
    #           "sequencer": "178869619ED32F87"
    #         }
    #       },
    #       "source": {
    #         "host": "[::1]",
    #         "port": "",
    #         "userAgent": "MinIO (linux; amd64) minio-go/v7.0.63 mc/DEVELOPMENT.GOGET"
    #       }
    #     }
    #   ]
    # }

    print(f"Received request")

    body = request.json

    if 'EventName' not in body:
        msg = f"'EventName' not in request"
        print(msg)
        return msg, 400

    if 'Records' not in body:
        msg = f"'Records' not in request"
        print(msg)
        return msg, 400

    if len(body['Records']) == 0:
        msg = f"'Records' is empty"
        print(msg)
        return msg, 400

    ce_data_records = []
    for record in body['Records']:
        ce_data_record = {
            "eventTime": record['eventTime'],
            "bucket": record['s3']['bucket']['name'],
            "object": record['s3']['object']['key'],
            "etag": record['s3']['object']['eTag'],
        }
        ce_data_records.append(ce_data_record)

    ce_data = {
        "event": body['EventName'],
        "records": ce_data_records
    }

    ce_attributes = {
        "type": "com.knative.dev.minio.event",
        "source": SOURCE_DECLARATION,
    }
    event = CloudEvent(ce_attributes, ce_data)

    # Creates the HTTP request representation of the CloudEvent in binary content mode
    headers, body = to_binary(event)

    try:
        print(f"Sending event for object {ce_data_records[0]['bucket']}/{ce_data_records[0]['object']} to {K_SINK}")
        response = requests.post(K_SINK, data=body, headers=headers)
        if response.status_code >= 300:
            print(f"Failed to send event to {K_SINK} with status code: {response.status_code}")
            return f"Failed to send event to {K_SINK}", 500
    except Exception as e:
        print(f"Failed to send event to {K_SINK} with error: {e}")
        return f"Failed to send event to {K_SINK}", 500

    return "", 204


if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
