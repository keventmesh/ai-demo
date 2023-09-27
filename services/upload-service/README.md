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
kubectl port-forward pod/minio --address 0.0.0.0 9000 9090 -n minio-dev

# Create a bucket named "ai-demo"
python - <<EOF
import boto3
s3 = boto3.resource('s3', endpoint_url='http://localhost:9000', aws_access_key_id='minio', aws_secret_access_key='minio1234')
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
S3_ENDPOINT_URL="http://localhost:9000" \
S3_ACCESS_KEY_ID="minio" \
S3_ACCESS_KEY_SECRET="minio1234" \
S3_ACCESS_SSL_VERIFY="false" \
S3_BUCKET_NAME="ai-demo" \
flask --app main --debug run
```

Test:
```shell
curl localhost:5000
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
-p 8080:8080 \
-e S3_ENDPOINT_URL="http://192.168.2.160:9000" \
-e S3_ACCESS_KEY_ID="minio" \
-e S3_ACCESS_KEY_SECRET="minio1234" \
-e S3_ACCESS_SSL_VERIFY="false" \
-e S3_BUCKET_NAME="ai-demo" \
${DOCKER_REPO_OVERRIDE}/upload-service
```

Test the image:
```shell
curl localhost:8080
```
