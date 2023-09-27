# Upload service

This service uploads files to a storage over S3 protocol.

This image is published at `quay.io/kevent-mesh/ai-demo-upload-service`.

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
PORT=8081 \
S3_ENDPOINT_URL="https://localhost:9445" \
S3_ACCESS_KEY_ID="minio" \
S3_ACCESS_KEY_SECRET="minio1234" \
S3_ACCESS_SSL_VERIFY="false" \
S3_BUCKET_NAME="ai-demo" \
python app.py
```

Test:
```shell
curl 'http://localhost:8081/' \
  -H 'Accept: application/json, text/javascript, */*; q=0.01' \
  -H 'Content-Type: application/json; charset=UTF-8' \
  --data-raw '{"image_b64":"iVBORw0KGgoAAAANSUhEUgAAAAoAAAAOCAYAAAAWo42rAAAAAXNSR0IArs4c6QAAAfxJREFUKFMty8FLU3EAwPHv7/d7czmF2JxhguGhP6BjdCgRKsJiFA6pLBN3CKIMk/RQqKiHVRgYGQgRER46BBURJSYFGYIUWo6VOhDKydya5qbrvbe3X6DdPx/R2lyvTzWF2F1ZhTIMlJIoKdnIbRKdmCD28hWv42lEW0vDFtxVUfkfqi2Yyazz9d0Y8fH32/Ba6Iyubw7hL69Aqm1kGIrVdIrI21ESU58Zmf6G6LjYpOsvtOD1+ZFK4i4y0FqQTCzz480o8dkIfeMTiBuXQ/rkuWZ8Ph+2lqxkHarL3CSXl5h+9pzFSISeT9OI7vZLOnC6Ea/Xy9RClqfRv/QcLiO/nuBh+D6/PkZ44SQRvZ1XdbCxkVRW8uTDb3Z6ithbLtm/x6K39Q6J2UUmi1cQ4a5OHQgGWTcVw2NJXIZBYJ+HMrnKg9Z7fPk+w0xJDjHQf1MfOR6gpLSE1JqNnddU+V3MR+cZaR/ip7PGaDqGGB68pQ/U1LKjuBSPx40UsJHNsRCd43Ggn0liJKvLEUN3w/pgzSGUoRBCIaVA2ybZ1TTJeIKZuRgd3Y8QJ+rqdF9XB0pqLNNEODYeo0Ahb4ME27JYiicQ19uu6PNnGzDNHLpQQDoWRcImb1lYZg60g8ulEIMDt/Wxo7VkM39w8g4qv4nSFrZlYpmbaMfZCv8A05jsaQzcdV8AAAAASUVORK5CYII="}'
```


# Running with Docker

Set your Docker repo override:
```shell
export DOCKER_REPO_OVERRIDE=docker.io/aliok
```


Build the image:
```shell
docker build . -t ${DOCKER_REPO_OVERRIDE}/upload-service
```

Run the image:
```shell
docker run --rm \
-p 8081:8081 \
-e PORT="8081" \
-e S3_ENDPOINT_URL="https://192.168.2.160:9445" \
-e S3_ACCESS_KEY_ID="minio" \
-e S3_ACCESS_KEY_SECRET="minio1234" \
-e S3_ACCESS_SSL_VERIFY="false" \
-e S3_BUCKET_NAME="ai-demo" \
${DOCKER_REPO_OVERRIDE}/upload-service
```

Test the image:
```shell
curl 'http://localhost:8081/' \
  -H 'Accept: application/json, text/javascript, */*; q=0.01' \
  -H 'Content-Type: application/json; charset=UTF-8' \
  --data-raw '{"image_b64":"iVBORw0KGgoAAAANSUhEUgAAAAoAAAAOCAYAAAAWo42rAAAAAXNSR0IArs4c6QAAAfxJREFUKFMty8FLU3EAwPHv7/d7czmF2JxhguGhP6BjdCgRKsJiFA6pLBN3CKIMk/RQqKiHVRgYGQgRER46BBURJSYFGYIUWo6VOhDKydya5qbrvbe3X6DdPx/R2lyvTzWF2F1ZhTIMlJIoKdnIbRKdmCD28hWv42lEW0vDFtxVUfkfqi2Yyazz9d0Y8fH32/Ba6Iyubw7hL69Aqm1kGIrVdIrI21ESU58Zmf6G6LjYpOsvtOD1+ZFK4i4y0FqQTCzz480o8dkIfeMTiBuXQ/rkuWZ8Ph+2lqxkHarL3CSXl5h+9pzFSISeT9OI7vZLOnC6Ea/Xy9RClqfRv/QcLiO/nuBh+D6/PkZ44SQRvZ1XdbCxkVRW8uTDb3Z6ithbLtm/x6K39Q6J2UUmi1cQ4a5OHQgGWTcVw2NJXIZBYJ+HMrnKg9Z7fPk+w0xJDjHQf1MfOR6gpLSE1JqNnddU+V3MR+cZaR/ip7PGaDqGGB68pQ/U1LKjuBSPx40UsJHNsRCd43Ggn0liJKvLEUN3w/pgzSGUoRBCIaVA2ybZ1TTJeIKZuRgd3Y8QJ+rqdF9XB0pqLNNEODYeo0Ahb4ME27JYiicQ19uu6PNnGzDNHLpQQDoWRcImb1lYZg60g8ulEIMDt/Wxo7VkM39w8g4qv4nSFrZlYpmbaMfZCv8A05jsaQzcdV8AAAAASUVORK5CYII="}'
```
