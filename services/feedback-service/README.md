# Feedback service

This service gets feedback from the client, converts them to CloudEvents and pushes them to the given sink.

This image is published at `quay.io/kevent-mesh/ai-demo-feedback-service`.


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
PORT=8085 \
K_SINK="https://webhook.site/48cdb072-bcf8-470e-8746-90ac76415316" \
SOURCE_DECLARATION="feedback-service" \
python app.py
```

Test:
```shell
curl localhost:8085 -i -X POST -H "Content-Type: application/json" -d '{"uploadId": "deadbeef", "feedback": "5"}'
```

See the outcome at https://webhook.site/#!/48cdb072-bcf8-470e-8746-90ac76415316/9f30a497-8b43-49a9-8f4b-25f1a2366bfe/1

You should see this body:
```json
{
  "uploadId": "deadbeef",
  "feedback": "5"
}
```
and these headers:
```
connection: close
content-length: 180
ce-time: 2023-09-26T11:29:10.252868+00:00
ce-type: com.knative.dev.feedback.event
ce-source: feedback-service
ce-id: 2ea7f9e1-2ca7-4984-bfb5-d4c1064d12da
ce-specversion: 1.0
accept: */*
accept-encoding: gzip, deflate
user-agent: python-requests/2.31.0
host: webhook.site
content-type: 	
```

# Running with Docker

Set your Docker repo override:
```shell
export DOCKER_REPO_OVERRIDE=docker.io/aliok
```


Build the image:
```shell
docker build . -t ${DOCKER_REPO_OVERRIDE}/feedback-service
```

Run the image:
```shell
docker run --rm \
-p 8085:8085 \
-e PORT="8085" \
-e K_SINK="https://webhook.site/48cdb072-bcf8-470e-8746-90ac76415316" \
-e SOURCE_DECLARATION="feedback-service" \
${DOCKER_REPO_OVERRIDE}/feedback-service
```

Test:
```shell
curl localhost:8085 -i -X POST -H "Content-Type: application/json" -d '{"uploadId": "deadbeef", "feedback": "5"}'
```

See the outcome at https://webhook.site/#!/48cdb072-bcf8-470e-8746-90ac76415316/9f30a497-8b43-49a9-8f4b-25f1a2366bfe/1
