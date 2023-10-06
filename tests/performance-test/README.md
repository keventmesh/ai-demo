## Development environment setup
Setup virtual environment:
```shell
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:
```shell
pip install -r requirements.txt
```

## Scale down images
```shell
python scale.py
```

This will take images from `images/source` folder and scale them down to 640x640 and save them to `images/scaled` folder.

## Filling the image data file
```shell
python fill_image_data.py
```
