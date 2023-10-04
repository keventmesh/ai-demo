# Analytics service

This service:
 - gets feedbacks at `/feedbacks` and persist them to Postgresql for analytics

This image is published at `quay.io/kevent-mesh/ai-demo-analytics-service:main`.

# Pre-requisites

Start a Postgres container:
```shell
docker run --rm --name postgres \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=ai-demo \
  -p 5432:5432 \
  postgres
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
PORT=8086 \
DB_HOST="localhost" \
DB_PORT="5432" \
DB_DATABASE="ai-demo" \
DB_USERNAME="postgres" \
DB_PASSWORD="postgres" \
python app.py
```

Test sending feedbacks:
```shell
curl -v "localhost:8086/feedbacks" \
  -X POST \
  -H "Ce-Specversion: 1.0" \
  -H "Ce-Type: does.not.matter" \
  -H "Content-Type: application/json" \
  -H "Ce-Source: knative://foo.bar" \
  -H "Ce-time: 2020-12-02T13:49:13.77Z" \
  -H "Ce-Id: 536808d3-88be-4077-9d7a-a3f162705f79" \
  -d '{"uploadId": "xyz", "feedback": 1}'
```

Check the DB:
```shell
docker exec -ti postgres psql postgresql://postgres:postgres@localhost:5432/ai-demo -c "select * from feedbacks;"

 id | feedback | upload_id |         created_on         
----+----------+-----------+----------------------------
  1 |        1 | xyz       | 2023-10-03 15:42:19.941195
(1 row)
```

Test sending predictions:
```shell
curl -v "localhost:8086/predictions" \
  -X POST \
  -H "Ce-Specversion: 1.0" \
  -H "Ce-Type: does.not.matter" \
  -H "Content-Type: application/json" \
  -H "Ce-Source: knative://foo.bar" \
  -H "Ce-time: 2020-12-02T13:49:13.77Z" \
  -H "Ce-Id: 536808d3-88be-4077-9d7a-a3f162705f79" \
  -d '{"uploadId": "xyz", "probability": 0.999, "x0": 0.24543, "x1": 0.24543, "y0": 0.24543, "y1": 0.24543}'
```

Check the DB:
```shell
docker exec -ti postgres psql postgresql://postgres:postgres@localhost:5432/ai-demo -c "select * from predictions;"

 id |  probability   | upload_id |       x0       |       x1       |       y0       |       y1       |         created_on         
----+----------------+-----------+----------------+----------------+----------------+----------------+----------------------------
  1 | 0.999000000000 | xyz       | 0.245430000000 | 0.245430000000 | 0.245430000000 | 0.245430000000 | 2023-10-03 15:50:11.873927
(1 row)
```

# Running with Docker

Set your Docker repo override:
```shell
export DOCKER_REPO_OVERRIDE=docker.io/aliok
```


Build the image:
```shell
docker build . -t ${DOCKER_REPO_OVERRIDE}/analytics-service
```

Run the image:
```shell
docker run --rm \
-p 8086:8086 \
-e DB_HOST="192.168.2.160" \
-e DB_PORT="5432" \
-e DB_DATABASE="ai-demo" \
-e DB_USERNAME="postgres" \
-e DB_PASSWORD="postgres" \
-e MAX_ITEMS_IN_CACHES="1000000" \
-e CACHE_ITEM_TTL_IN_SECONDS="300" \
${DOCKER_REPO_OVERRIDE}/analytics-service
```

