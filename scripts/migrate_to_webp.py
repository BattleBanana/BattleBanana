# Script to migrate .jpg images to .webp format
# Usage: python migrate_to_webp.py

import os

from PIL import Image


def migrate_to_webp(source_dir):
	for root, _, files in os.walk(source_dir):
		for file in files:
			if file.endswith(".jpg"):
				jpg_path = os.path.join(root, file)
				webp_path = os.path.splitext(jpg_path)[0] + ".webp"
				with Image.open(jpg_path) as img:
					img.save(webp_path, "webp")
				print(f"Converted {jpg_path} to {webp_path}")

if __name__ == "__main__":
    migrate_to_webp("assets/imagecache/")
