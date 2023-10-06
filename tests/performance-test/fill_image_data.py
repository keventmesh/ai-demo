import json
import os
import random

IMAGES_DIR = "images/scaled"
DATA_FILE = "data.json"


def main():
    output = {}

    with open(DATA_FILE) as f:
        existing_arr = json.load(f)
        existing = {}
        for item in existing_arr:
            existing[item["image"]] = item

    for file in os.listdir(IMAGES_DIR):
        if file.endswith(".jpg") or file.endswith(".png") or file.endswith(".jpeg"):
            file = os.path.join(IMAGES_DIR, file)
            if file in existing:
                image_item = existing[file]
                output[file] = image_item
            else:
                output[file] = {
                    "image": file,
                    "feedback": 5 if random.random() > 0.5 else 1  # 50% of the time, the feedback is 5
                }

    with open(DATA_FILE, "w") as f:
        json.dump(list(output.values()), f, indent=4)


if __name__ == '__main__':
    main()
