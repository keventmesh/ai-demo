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
