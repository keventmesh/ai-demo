## Test run v1

```shell
cd v1

mkdir model

# download model 
gsutil cp -r gs://knative-ai-demo/kserve-models/knative_01/0001 ./model

tree

.
├── Dockerfile
└── model
    └── 0001
        ├── fingerprint.pb
        ├── saved_model.pb
        └── variables
            ├── variables.data-00000-of-00001
            └── variables.index

4 directories, 5 files

# make a test run, before building the image
docker run --rm -p 8500:8500 -p 8501:8501 \
--mount type=bind,source=./model,target=/models/demo \
-e MODEL_NAME=demo -t tensorflow/serving

# manually call with an invalid 3 pixel image
curl -d '{"instances": [[[ [82,83,65],[83,86,69],[92,99,83] ]]]}' -X POST http://localhost:8501/v1/models/demo:predict | jq | more

{
  "predictions": [
    {
      "detection_multiclass_scores": [
        [
          0.00440392504,
          0.0125000263
        ],
        [
          0.00591045246,
          0.0114316624
        ],
        [
          0.00671821414,
          0.0111456951
        ],
```


## Build the image - v1

This image is published at `quay.io/kevent-mesh/ai-demo-inference-service-v1`.

Set your Docker repo override:
```shell
export DOCKER_REPO_OVERRIDE=docker.io/aliok
```

Build it:
```shell
cd v1

mkdir model

# download model 
gsutil cp -r gs://knative-ai-demo/kserve-models/knative_01/0001 ./model

docker build . -t ${DOCKER_REPO_OVERRIDE}/inference-service-v1
```

Test it:
```shell
docker run --rm -p 8500:8500 -p 8501:8501 -t ${DOCKER_REPO_OVERRIDE}/inference-service-v1
```
