# UI service

This service simply renders the UI.

This image is published at `quay.io/kevent-mesh/ai-demo-ui-service`.

# Pre-requisites

You need to have upload-service and the reply-service running first. See readme files in those folders.

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
PORT=8080 \
UPLOAD_SERVICE_URL="http://localhost:8081" \
REPLY_SERVICE_URL="http://localhost:8082" \
python app.py
```

Test:
```shell
curl localhost:8080
```


# Running with Docker

Set your Docker repo override:
```shell
export DOCKER_REPO_OVERRIDE=docker.io/aliok
```


Build the image:
```shell
docker build . -t ${DOCKER_REPO_OVERRIDE}/ui-service
```

Run the image:
```shell
docker run --rm \
-p 8080:8080 \
-e PORT="8080" \
-e UPLOAD_SERVICE_URL="http://192.168.2.160:8081" \
-e REPLY_SERVICE_URL="http://192.168.2.160:8082" \
${DOCKER_REPO_OVERRIDE}/ui-service
```

Test the image:
```shell
curl localhost:8080
```
