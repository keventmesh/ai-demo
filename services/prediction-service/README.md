# Prediction service

This service:
- Receives a `com.knative.dev.minio.event` event
- Downloads the image from Minio
- Sends the image to the KServe inference service
- Replies with the prediction result as a `com.knative.dev.prediction.event` event

This image is published at `quay.io/kevent-mesh/ai-demo-prediction-service`.

# Pre-requisites

Setup Minio:
```shell
# create namespace
kubectl create namespace minio-dev

# create instance
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  labels:
    app: minio
  name: minio
  namespace: minio-dev
spec:
  containers:
  - name: minio
    image: quay.io/minio/minio:latest
    command:
    - /bin/bash
    - -c
    args: 
    - minio server /data --console-address :9090
    env:
    - name: MINIO_ROOT_USER
      value: minio
    - name: MINIO_ROOT_PASSWORD
      value: minio1234
EOF

# allow network access
kubectl port-forward pod/minio --address 0.0.0.0 9445 9090 -n minio-dev --address=0.0.0.0
```

Or, if you already have a Minio instance running on Kubernetes, you can use that.

```shell
kubectl port-forward -n minio-operator svc/minio 9445:443 --address=0.0.0.0
```

## Create a bucket
```shell
# Create a bucket named "ai-demo"
python - <<EOF
import boto3
s3 = boto3.resource('s3', endpoint_url='http://localhost:9445', aws_access_key_id='minio', aws_secret_access_key='minio1234', verify=False)

# OR 
# s3 = boto3.resource('s3', endpoint_url='https://localhost:9445', aws_access_key_id='minio', aws_secret_access_key='minio1234', verify=False)

s3.create_bucket(Bucket="ai-demo")
EOF
```

## Create an image on Minio:
```shell
python - <<EOF
import boto3
import base64
# s3 = boto3.client( 's3', endpoint_url='http://localhost:9445', aws_access_key_id='minio', aws_secret_access_key='minio1234', verify=False)

# OR 
s3 = boto3.client( 's3', endpoint_url='https://localhost:9445', aws_access_key_id='minio', aws_secret_access_key='minio1234', verify=False)

img = 'iVBORw0KGgoAAAANSUhEUgAAAAoAAAAOCAYAAAAWo42rAAAAAXNSR0IArs4c6QAAAfxJREFUKFMty8FLU3EAwPHv7/d7czmF2JxhguGhP6BjdCgRKsJiFA6pLBN3CKIMk/RQqKiHVRgYGQgRER46BBURJSYFGYIUWo6VOhDKydya5qbrvbe3X6DdPx/R2lyvTzWF2F1ZhTIMlJIoKdnIbRKdmCD28hWv42lEW0vDFtxVUfkfqi2Yyazz9d0Y8fH32/Ba6Iyubw7hL69Aqm1kGIrVdIrI21ESU58Zmf6G6LjYpOsvtOD1+ZFK4i4y0FqQTCzz480o8dkIfeMTiBuXQ/rkuWZ8Ph+2lqxkHarL3CSXl5h+9pzFSISeT9OI7vZLOnC6Ea/Xy9RClqfRv/QcLiO/nuBh+D6/PkZ44SQRvZ1XdbCxkVRW8uTDb3Z6ithbLtm/x6K39Q6J2UUmi1cQ4a5OHQgGWTcVw2NJXIZBYJ+HMrnKg9Z7fPk+w0xJDjHQf1MfOR6gpLSE1JqNnddU+V3MR+cZaR/ip7PGaDqGGB68pQ/U1LKjuBSPx40UsJHNsRCd43Ggn0liJKvLEUN3w/pgzSGUoRBCIaVA2ybZ1TTJeIKZuRgd3Y8QJ+rqdF9XB0pqLNNEODYeo0Ahb4ME27JYiicQ19uu6PNnGzDNHLpQQDoWRcImb1lYZg60g8ulEIMDt/Wxo7VkM39w8g4qv4nSFrZlYpmbaMfZCv8A05jsaQzcdV8AAAAASUVORK5CYII='
base64_decoded = base64.b64decode(img)
s3.put_object(Bucket='ai-demo', Key='my-image', Body=base64_decoded)
EOF
```

# Running locally

Setup virtual environment:
```shell
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:    
```shell
pip install -r requirements.txt
```

Run:
```shell
PORT=8083 \
SOURCE_DECLARATION="prediction-service" \
S3_ENDPOINT_URL="https://localhost:9445" \
S3_ACCESS_KEY_ID="minio" \
S3_ACCESS_KEY_SECRET="minio1234" \
S3_ACCESS_SSL_VERIFY="false" \
S3_BUCKET_NAME="ai-demo" \
python app.py
```

Test:
```shell
# Send a sample event
curl -i 'http://localhost:8083/'                      \
  -H 'ce-time: 2023-09-26T12:35:14.372688+00:00'      \
  -H 'ce-type: com.knative.dev.minio.event'           \
  -H 'ce-source: pod.ai-demo.minio-webhook-service'   \
  -H 'ce-id: a9254f41-4d32-45d2-8293-e90d96876de1'    \
  -H 'ce-specversion: 1.0'                            \
  -H 'accept: */*'                                    \
  -H 'accept-encoding: gzip, deflate'                 \
  -H 'content-type: '                                 \
  -d $'{"event": "s3:ObjectCreated:Put", "records": [{"eventTime": "2023-09-26T09:38:47.702Z", "bucket": "ai-demo", "object": "my-image", "etag": "702314f405adeaa9aa042985692cd49e"}]}'
```

You should see this reply:
```json
{
  "uploadId": "deadbeef",
  "probability": "0.9012353451",
  "x0": "0.24543",
  "x1": "0.356647",
  "y0": "0.34543",
  "y1": "0.556647"
}
```

with these headers:
```
Server: Werkzeug/2.3.7 Python/3.9.6
Date: Wed, 27 Sep 2023 12:11:02 GMT
Content-Type: text/html; charset=utf-8
Content-Length: 125
ce-specversion: 1.0
ce-id: df0340be-6e7e-4136-8445-895b8de32a0b
ce-source: prediction-service
ce-type: com.knative.dev.prediction.event
ce-time: 2023-09-27T12:11:02.451656+00:00
Access-Control-Allow-Origin: *
Connection: close
```


# Running with Docker

Set your Docker repo override:
```shell
export DOCKER_REPO_OVERRIDE=docker.io/aliok
```


Build the image:
```shell
docker build . -t ${DOCKER_REPO_OVERRIDE}/prediction-service
```

Run the image:
```shell
docker run --rm \
-p 8083:8083 \
-e SOURCE_DECLARATION="prediction-service" \
-e PORT="8083" \
-e S3_ENDPOINT_URL="https://192.168.2.160:9445" \
-e S3_ACCESS_KEY_ID="minio" \
-e S3_ACCESS_KEY_SECRET="minio1234" \
-e S3_ACCESS_SSL_VERIFY="false" \
-e S3_BUCKET_NAME="ai-demo" \
${DOCKER_REPO_OVERRIDE}/prediction-service
```

Test the image:
```shell
curl 'http://localhost:8081/' \
  -H 'Accept: application/json, text/javascript, */*; q=0.01' \
  -H 'Content-Type: application/json; charset=UTF-8' \
  --data-raw '{"image_b64":"iVBORw0KGgoAAAANSUhEUgAAAAoAAAAOCAYAAAAWo42rAAAAAXNSR0IArs4c6QAAAfxJREFUKFMty8FLU3EAwPHv7/d7czmF2JxhguGhP6BjdCgRKsJiFA6pLBN3CKIMk/RQqKiHVRgYGQgRER46BBURJSYFGYIUWo6VOhDKydya5qbrvbe3X6DdPx/R2lyvTzWF2F1ZhTIMlJIoKdnIbRKdmCD28hWv42lEW0vDFtxVUfkfqi2Yyazz9d0Y8fH32/Ba6Iyubw7hL69Aqm1kGIrVdIrI21ESU58Zmf6G6LjYpOsvtOD1+ZFK4i4y0FqQTCzz480o8dkIfeMTiBuXQ/rkuWZ8Ph+2lqxkHarL3CSXl5h+9pzFSISeT9OI7vZLOnC6Ea/Xy9RClqfRv/QcLiO/nuBh+D6/PkZ44SQRvZ1XdbCxkVRW8uTDb3Z6ithbLtm/x6K39Q6J2UUmi1cQ4a5OHQgGWTcVw2NJXIZBYJ+HMrnKg9Z7fPk+w0xJDjHQf1MfOR6gpLSE1JqNnddU+V3MR+cZaR/ip7PGaDqGGB68pQ/U1LKjuBSPx40UsJHNsRCd43Ggn0liJKvLEUN3w/pgzSGUoRBCIaVA2ybZ1TTJeIKZuRgd3Y8QJ+rqdF9XB0pqLNNEODYeo0Ahb4ME27JYiicQ19uu6PNnGzDNHLpQQDoWRcImb1lYZg60g8ulEIMDt/Wxo7VkM39w8g4qv4nSFrZlYpmbaMfZCv8A05jsaQzcdV8AAAAASUVORK5CYII="}'
```
 
You should see the same output as earlier.
