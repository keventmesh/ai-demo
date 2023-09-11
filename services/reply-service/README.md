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
docker run --rm -p 5000:5000 ${DOCKER_REPO_OVERRIDE}/upload-service
```

Test the image:
```shell
curl localhost:5000
```
