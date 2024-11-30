import json
import os
import re
from threading import Thread

from PIL import Image

from dueutil import dbconn, tasks, util

CACHE_DIR = "assets/imagecache/"
WEBP_EXTENSION = ".webp"

class CacheStats:
    """Tracks repeated usages of cached images."""
    def __init__(self):
        self.repeated_usages = {}

stats = CacheStats()


def track_image_usage(url: str):
    """Track the usage count of a cached image."""
    if os.path.isfile(get_cached_filename(url)):
        stats.repeated_usages[url] = stats.repeated_usages.get(url, 1) + 1


def _save_image(filename: str, image: Image.Image):
    """Save an image to a file with high quality."""
    try:
        util.logger.info(f"Saving image: {image}")
        image.save(filename, exact=True, lossless=True, quality=100)
    except Exception as e:
        util.logger.error(f"Failed to save image {filename}: {e}")


def async_save_image(filename: str, image: Image.Image):
    """Save an image asynchronously."""
    Thread(target=_save_image, args=(filename, image.copy())).start()


def generate_filename(base: str, extension: str, width: int = None, height: int = None) -> str:
    """Generate a cache filename based on base name, dimensions, and extension."""
    sanitized_name = re.sub(r"\W+", "", base)[:128]
    if width and height:
        sanitized_name += f"_{width}_{height}"
    return f"{CACHE_DIR}{sanitized_name}{extension}"


def get_cached_filename(name: str) -> str:
    """Generate a standard cached image filename."""
    return generate_filename(name, WEBP_EXTENSION)


def get_resized_cached_filename(name: str, width: int, height: int) -> str:
    """Generate a resized image cache filename."""
    return generate_filename(name, WEBP_EXTENSION, width, height)


async def cache_image(url: str):
    """Cache an image from a URL."""
    filename = get_cached_filename(url)
    try:
        image_data = await util.download_file(url)
        image = Image.open(image_data)
        async_save_image(filename, image)

        return image
    except Exception as e:
        util.logger.error(f"Failed to cache image from {url}: {e}")
        if os.path.isfile(filename):
            os.remove(filename)

    return None


async def cache_resized_image(image: Image.Image, url: str):
    """Cache a resized version of the image."""
    if not image:
        return None

    filename = get_resized_cached_filename(url, image.width, image.height)
    try:
        async_save_image(filename, image)
        return image
    except Exception as e:
        util.logger.error(f"Failed to cache resized image: {e}")
        if os.path.isfile(filename):
            os.remove(filename)
        return None


def load_cached_image(filename: str):
    """Load a cached image from disk."""
    try:
        return Image.open(filename)
    except Exception:
        if os.path.isfile(filename):
            os.remove(filename)
        return None


def get_cached_resized_image(url: str, width: int, height: int):
    """Retrieve a resized image from the cache."""
    filename = get_resized_cached_filename(url, width, height)
    return load_cached_image(filename)


def remove_cached_image(url: str):
    """Remove a cached image unless it's still in use."""
    if stats.repeated_usages.get(url, 0) > 1:
        stats.repeated_usages[url] -= 1
    else:
        filename = get_cached_filename(url)
        if os.path.isfile(filename):
            os.remove(filename)
            util.logger.info(f"Removed cached image: {url}")


@tasks.task(timeout=3600)
async def save_cache_info():
    """Persist cache statistics."""
    dbconn.insert_object("stats", stats)


def _load_cache_info():
    """Load cache statistics from the database."""
    collection = dbconn.get_collection_for_object(CacheStats)
    stats_json: dict = collection.find_one({"_id": "stats"})
    if stats_json:
        stats.repeated_usages.update(json.loads(stats_json.get("data", "{}")))
    else:
        util.logger.info("No cache data found.")

_load_cache_info()
