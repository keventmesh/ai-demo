import asyncio
import os
from PIL import Image

SRC_DIR = "images/source"
TARGET_DIR = "images/scaled"
MAX_WIDTH = 640
MAX_HEIGHT = 640


async def scale_down(src_file):
    src_file_path = os.path.join(SRC_DIR, src_file)
    target_file_path = os.path.join(TARGET_DIR, src_file)
    print(f"scale down {src_file_path} to {target_file_path}")
    image = Image.open(src_file_path)
    image.thumbnail((MAX_WIDTH, MAX_HEIGHT), Image.Resampling.LANCZOS)
    image.save(target_file_path, "PNG")

async def main():
    files = []

    # get the image files in the directory
    for file in os.listdir(SRC_DIR):
        if file.endswith(".jpg") or file.endswith(".png") or file.endswith(".jpeg"):
            files.append(file)

    async with asyncio.TaskGroup() as tg:
        for file in files:
            await tg.create_task(scale_down(file))


if __name__ == '__main__':
    asyncio.run(main())
