# Admin service

This service renders a view for a given upload with:

- image itself
- its prediction results
- received feedback

This image is published at `quay.io/kevent-mesh/ai-demo-admin-service`.

# Pre-requisites

- Have Minio working, with an upload in it
- Have the Postgres working, with the prediction and feedbacks in it

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
PORT=8087 \
S3_ENDPOINT_URL="https://localhost:9445" \
S3_ACCESS_KEY_ID="minio" \
S3_ACCESS_KEY_SECRET="minio1234" \
S3_ACCESS_SSL_VERIFY="false" \
S3_BUCKET_NAME="ai-demo" \
DB_HOST="localhost" \
DB_PORT="5432" \
DB_DATABASE="ai-demo" \
DB_USERNAME="postgres" \
DB_PASSWORD="postgres" \
python app.py
```

Test:

- Open http://localhost:8087/?case={uploadId} in your browser. You should see the image, its prediction and feedbacks.
