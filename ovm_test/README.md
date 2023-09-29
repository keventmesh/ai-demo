# Using OVMS

### Setup Python environment

```shell
python3 -m venv .venv
source .venv/bin/activate
```

### Running quick start of OVMS

https://docs.openvino.ai/2023.1/ovms_docs_quick_start_guide.html

Download stuff:
```shell
docker pull openvino/model_server:latest

curl --create-dirs \
 https://storage.openvinotoolkit.org/repositories/open_model_zoo/2022.1/models_bin/2/face-detection-retail-0004/FP32/face-detection-retail-0004.xml\
 https://storage.openvinotoolkit.org/repositories/open_model_zoo/2022.1/models_bin/2/face-detection-retail-0004/FP32/face-detection-retail-0004.bin\
 -o model/1/face-detection-retail-0004.xml \
 -o model/1/face-detection-retail-0004.bin
 
curl --fail \
 https://raw.githubusercontent.com/openvinotoolkit/model_server/releases/2023/1/demos/common/python/client_utils.py \
 -o client_utils.py \
 https://raw.githubusercontent.com/openvinotoolkit/model_server/releases/2023/1/demos/face_detection/python/face_detection.py \
 -o face_detection.py \
 https://raw.githubusercontent.com/openvinotoolkit/model_server/releases/2023/1/demos/common/python/requirements.txt \
 -o client_requirements.txt
 
curl --fail --create-dirs https://raw.githubusercontent.com/openvinotoolkit/model_server/releases/2023/1/demos/common/static/images/people/people1.jpeg -o images/people1.jpeg

❯ tree
.
├── README.md
├── client_requirements.txt
├── client_utils.py
├── face_detection.py
├── images
│   └── people1.jpeg
└── model
    └── 1
        ├── face-detection-retail-0004.bin
        └── face-detection-retail-0004.xml
4 directories, 7 files
```

Start the container:
```shell
docker run --name=ovm --rm -u $(id -u):$(id -g) -v $(pwd)/model:/models/face-detection -p 9000:9000 openvino/model_server:latest \
--model_path /models/face-detection --model_name face-detection --port 9000 --shape auto

# print directory structure of the container
docker exec -it ovm ls -aLR /models

/models:
.  ..  face-detection

/models/face-detection:
.  ..  1

/models/face-detection/1:
.  ..  face-detection-retail-0004.bin  face-detection-retail-0004.xml
```

Run the inference:
```shell
pip install -r client_requirements.txt

mkdir results

python face_detection.py --batch_size 1 --width 600 --height 400 --input_images_dir images --output_dir results --grpc_port 9000
```

### Run TensorFlow Serving with OVM server - NOT WORKING

```shell
ls $(pwd)/../kserve_test/models/knative_01/0001
> fingerprint.pb  saved_model.pb  variables

docker run --name=ovm \--rm -u $(id -u):$(id -g) \
 -v $(pwd)/../kserve_test/models/knative_01/0001:/models/knative_01/1 \
 -p 9000:9000 openvino/model_server:latest \
 --model_path /models/knative_01 \
 --model_name knative_01 \
 --port 9000 \
 --shape auto
 
 docker run --name=ovm \--rm -u $(id -u):$(id -g) \
 -v /tmp/knative01/0001:/models/knative_01/1 \
 -p 9000:9000 openvino/model_server:latest \
 --model_path /models/knative_01 \
 --model_name knative_01 \
 --port 9000 \
 --shape auto
```


### Convert TensorFlow model to IR model (using opset11)

https://docs.openvino.ai/2023.1/notebooks/101-tensorflow-classification-to-openvino-with-output.html
https://docs.openvino.ai/2023.1/openvino_docs_MO_DG_prepare_model_convert_model_Convert_Model_From_TensorFlow.html
https://docs.openvino.ai/2023.1/openvino_docs_ops_opset11.html

```shell
# clean up virtual environment
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate

pip install "openvino==2023.1.0"
pip install "opencv-python=4.8.1.78"
pip install "matplotlib==3.8.0"
pip install "tensorflow-serving-api==2.13.0"

# pip install openvino-dev==2023.1.0
# pip install "openvino-dev[tensorflow2]==2023.1.0"

python - <<EOF
import time
from pathlib import Path

import openvino as ov
import cv2
import matplotlib.pyplot as plt
import numpy as np
import tensorflow as tf

model_path = Path("/Users/aliok/go/src/github.com/aliok/knative-eventing-ai-demo/kserve_test/models/knative_01/0001")

ir_dir = Path("/tmp/foo")
ir_dir.mkdir(exist_ok=True)
ir_path = Path("/tmp/foo/ir_model.xml")

print("Exporting TensorFlow model to IR... This may take a few minutes.")
ov_model = ov.convert_model(model_path)
# ov_model = ov.convert_model(model_path, input=[[1, 224, 224, 3]])
ov.save_model(ov_model, ir_path)
EOF
````

### Convert TensorFlow model to IR model (using opset10) - doesn't work

https://docs.openvino.ai/2023.1/notebooks/101-tensorflow-classification-to-openvino-with-output.html
https://docs.openvino.ai/2023.1/openvino_docs_MO_DG_prepare_model_convert_model_Convert_Model_From_TensorFlow.html
https://docs.openvino.ai/2023.0/openvino_docs_ops_opset11.html

Using version 2023.1.0 and doing the conversion resulted in this error in OVM server on RHODS:
```
Converting input model. Cannot create Interpolate layer map/while/Preprocessor/ResizeImage/resize/ResizeBilinear id:56 from unsupported opset: opset11
```

The OVM version on RHODS is `OpenVINO Model Server 2022.3.27eb5939`. So, I tried to use that version of OpenVino and do the conversion again.
However, the conversion functionality is implemented in `openvino-dev` package after version 2022.3.0.
And, I couldn't find a way to make 2023.1.0 to convert to a model that's before opset11.


### Running the newly converted IR model with OVM

https://docs.openvino.ai/2023.1/ovms_docs_models_repository.html
https://docs.openvino.ai/2023.1/ovms_docs_rest_api_tfs.html#doxid-ovms-docs-rest-api-tfs

Start the container, with rest enabled:
```shell
docker run --name=ovm --rm -u $(id -u):$(id -g) \
 -v /tmp/foo:/models/foo/1 \
 -p 9000:9000 -p 9191:9191 \
 openvino/model_server:latest \
 --model_path /models/foo --model_name foo \
 --port 9000 --rest_port=9191 \
 --shape auto

# print directory structure of the container
docker exec -it ovm ls -aLR /models

/models:
.  ..  foo

/models/foo:
.  ..  1

/models/foo/1:
.  ..  ir_model.bin  ir_model.xml
```


Examine shit:
```shell
curl http://localhost:9191/v1/models/foo

{
 "model_version_status": [
  {
   "version": "1",
   "state": "AVAILABLE",
   "status": {
    "error_code": "OK",
    "error_message": "OK"
   }
  }
 ]
}

curl http://localhost:9191/v1/models/foo/versions/1
{
 "model_version_status": [
  {
   "version": "1",
   "state": "AVAILABLE",
   "status": {
    "error_code": "OK",
    "error_message": "OK"
   }
  }
 ]
}
```

Run inference:
```shell
curl -d '{"instances": [[[ [82,83,65],[83,86,69],[92,99,83] ]]]}' -X POST http://localhost:9191/v1/models/foo/versions/1:predict | jq | more

{
  "predictions": [
    {
      "detection_boxes": [
        [
          0.895665109,
          0,
          0.977747619,
          0.0993095264
        ],
        [
          0.794969738,
          0.841132522,
          1,
          1
        ],
```

### Use OVMS Adapter

https://docs.openvino.ai/2023.1/omz_model_api_ovms_adapter.html

```shell
docker run -d --rm -v \
 /home/user/models:/models \
 -p 9000:9000 \
 openvino/model_server:latest \
 --model_path /models/model1 --model_name model1 \
 --port 9000 --shape auto \
 --nireq 32 --target_device CPU \--plugin_config "{\"CPU_THROUGHPUT_STREAMS\": \"CPU_THROUGHPUT_AUTO\"}"

```
