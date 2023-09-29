## Simple example of using TensorFlow Serving

https://www.tensorflow.org/tfx/serving/docker

```shell
mkdir /tmp/tensorflow_serving
cd /tmp/tensorflow_serving

git clone https://github.com/tensorflow/serving
# Location of demo models
TESTDATA="$(pwd)/serving/tensorflow_serving/servables/tensorflow/testdata"

# Start TensorFlow Serving container and open the REST API port
docker run -t --rm -p 8501:8501 \
    -v "$TESTDATA/saved_model_half_plus_two_cpu:/models/half_plus_two" \
    -e MODEL_NAME=half_plus_two \
    tensorflow/serving

# Query the model using the predict API
curl -d '{"instances": [1.0, 2.0, 5.0]}' -X POST http://localhost:8501/v1/models/half_plus_two:predict

# Returns => { "predictions": [2.5, 3.0, 4.5] }
```


## Use the previously trained model with TensorFlow Serving

https://www.tensorflow.org/tfx/serving/serving_basic

```shell
# create a copy of the model in /tmp
mkdir -p /tmp/knative01/0001
cp -R /Users/aliok/go/src/github.com/aliok/knative-eventing-ai-demo/training/TensorFlow/workspace/training_01/exported-models/my_model/saved_model/* /tmp/knative01/0001/
tree /tmp/knative01/
# /tmp/knative01/
# └── 0001
#     └── saved_model
#         ├── assets
#         ├── fingerprint.pb
#         ├── saved_model.pb
#         └── variables
#             ├── variables.data-00000-of-00001
#             └── variables.index
# 5 directories, 4 files


docker run --rm -p 8500:8500 -p 8501:8501 \
--mount type=bind,source=/tmp/knative01,target=/models/knative01 \
-e MODEL_NAME=knative01 -t tensorflow/serving

# manually call with an invalid 3 pixel image
curl -d '{"instances": [[[ [82,83,65],[83,86,69],[92,99,83] ]]]}' -X POST http://localhost:8501/v1/models/knative01:predict | jq

# call with a proper but small image
# image path relative to repo root
IMAGE_PATH="./tensorflow_serving_test/test_smaller.jpeg"
# IMAGE_DATA will hold the image data as a list of lists of lists
IMAGE_DATA=$(python -c "from PIL import Image;import os;import numpy as np;print(np.array(Image.open(os.path.join(os.getcwd(), '${IMAGE_PATH}'))).tolist())")

INFERENCE_START=$(date +%s.%N)

# call the inference, which will return a JSON with the predictions
# there can be too many results, so, let's not print them right now
INFERENCE_RESULT=$(curl -d "{\"instances\": [ ${IMAGE_DATA} ]}" -X POST http://localhost:8501/v1/models/knative01:predict)

INFERENCE_END=$(date +%s.%N)
DIFF=$(echo "$INFERENCE_END - $INFERENCE_START" | bc)
echo "Inference took ${DIFF} seconds."

# INFERENCE_RESULT looks like this
# ❯ echo ${INFERENCE_RESULT} | jq
# {
#   "predictions": [
#     {
#       "num_detections": 100,
#       "detection_anchor_indices": [
#         50731,
#         49765,
#         ...
#       ],
#       "detection_classes": [
#         1,
#         1,
#         ...
#       ],
#       "detection_scores": [
#         0.9999997615814209,
#         0.9999997615814209,
#          ...
#       ],
#       ...
#     }
#   ]
# }

# we only requested inference for a single image, so, get it
PREDICTIONS=$(echo ${INFERENCE_RESULT} | jq '.predictions[0]')

echo "Made $(echo ${PREDICTIONS} | jq '.num_detections') detections in the image."
# print the information about the first detection
echo "First detection box: "
echo ${PREDICTIONS} | jq '.detection_boxes[0]'

echo "First detection score: "
echo ${PREDICTIONS} | jq '.detection_scores[0]'

```
