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
PORT=8082 \
MAX_ITEMS_IN_CACHES=1000000 \
CACHE_ITEM_TTL_IN_SECONDS=300 \
python app.py
```

# Running with Docker

Set your Docker repo override:
```shell
export DOCKER_REPO_OVERRIDE=docker.io/aliok
```


Build the image:
```shell
docker build . -t ${DOCKER_REPO_OVERRIDE}/reply-service
```

Run the image:
```shell
docker run --rm \
-p 8082:8082 \
-e PORT="8082" \
-e MAX_ITEMS_IN_CACHES="1000000" \
-e CACHE_ITEM_TTL_IN_SECONDS="300" \
${DOCKER_REPO_OVERRIDE}/reply-service
```

# Testing - case 1: prediction happens slower than client requesting reply

```shell
# open the test UI
open localhost:8082/test

submit the form, with value deadbeef

# send a CloudEvent
curl -v "http://localhost:8082" \
  -X POST \
  -H "Ce-Specversion: 1.0" \
  -H "Ce-Type: demo.prediction.event" \
  -H "Content-Type: application/json" \
  -H "Ce-Source: knative://foo.bar" \
  -H "Ce-time: 2020-12-02T13:49:13.77Z" \
  -H "Ce-Id: 536808d3-88be-4077-9d7a-a3f162705f79" \
  -d '{"uploadId":"deadbeef", "probability":"0.9012353451", "x0": "0.24543", "x1": "0.356647", "y0": "0.34543", "y1": "0.556647"}'
  
In UI, you will see this:
> Received{"uploadId":"deadbeef","probability":"0.9012353451","x0":"0.24543","x1":"0.356647","y0":"0.34543","y1":"0.556647"}
```

# Testing - case 2: prediction happens faster than client requesting reply

```shell
# open the test UI
open localhost:8082/test

# send a CloudEvent
curl -v "http://localhost:8082" \
  -X POST \
  -H "Ce-Specversion: 1.0" \
  -H "Ce-Type: demo.prediction.event" \
  -H "Content-Type: application/json" \
  -H "Ce-Source: knative://foo.bar" \
  -H "Ce-time: 2020-12-02T13:49:13.77Z" \
  -H "Ce-Id: 536808d3-88be-4077-9d7a-a3f162705f79" \
  -d '{"uploadId":"deadbeef", "probability":"0.9012353451", "x0": "0.24543", "x1": "0.356647", "y0": "0.34543", "y1": "0.556647"}'

submit the form, with value deadbeef
  
In UI, you will see this:
> Received{"uploadId":"deadbeef","probability":"0.9012353451","x0":"0.24543","x1":"0.356647","y0":"0.34543","y1":"0.556647"}
```

# Testing - case 3&4: TTL
Do the same steps as case 1 and case 2, but:
- Start the app by lowering the TTL
- Wait for TTL to expire

