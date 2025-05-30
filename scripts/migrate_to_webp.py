# Script to migrate .jpg images to .webp format
# Usage: python3 -m scripts.migrate_to_webp
#
# Requirements:
#   - Pillow library (pip install Pillow)
#
# The script will convert all .jpg files in the specified directory
# and its subdirectories to .webp format with default quality settings.

import os
import time
from concurrent.futures import ThreadPoolExecutor

from PIL import Image


def count_jpg_files(source_dir):
    count = 0
    for _, _, files in os.walk(source_dir):
        count += len([f for f in files if f.endswith(".jpg")])
    return count


def convert_images(jpg_path, webp_path):
    with Image.open(jpg_path) as img:
        img.save(webp_path, "webp", quality=100, method=6)
    os.remove(jpg_path)


def migrate_to_webp(source_dir):
    executor = ThreadPoolExecutor(max_workers=16, thread_name_prefix="ImageConverter")
    futures = []

    total_files = count_jpg_files(source_dir)
    queued = 0
    for root, _, files in os.walk(source_dir):
        for file in files:
            if file.endswith(".jpg"):
                jpg_path = os.path.join(root, file)
                webp_path = os.path.splitext(jpg_path)[0] + ".webp"
                future = executor.submit(convert_images, jpg_path, webp_path)
                futures.append((jpg_path, future))
                queued += 1
                print(f"Queuing task {queued}/{total_files}", end="\r")

    print("\nWaiting for tasks to finish...")
    executor.shutdown(wait=True)

    # Check for failures
    failures = []
    for jpg_path, future in futures:
        try:
            future.result()  # This will raise any exception from the worker
        except Exception as e:
            failures.append((jpg_path, str(e)))

    # Report results
    print(f"\nSuccessfully converted: {total_files - len(failures)}")
    if failures:
        print(f"\nFailed conversions ({len(failures)}):")
        for jpg_path, error in failures:
            print(f"  {jpg_path}: {error}")
    print("Done.")


if __name__ == "__main__":
    t = time.time()
    migrate_to_webp("assets/imagecache/")
    print(f"Finished in {time.time() - t:.2f} seconds.")
