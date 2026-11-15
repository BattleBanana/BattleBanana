import json
import os
import re
from threading import Thread, get_ident

from discord.ext import tasks
from PIL import Image, ImageFile

from dueutil import dbconn, util

CACHE_DIR = "assets/imagecache/"
WEBP_EXTENSION = ".webp"
WEBP_FORMAT = "WEBP"
PARTIAL_SUFFIX = ".partial"

ImageFile.LOAD_TRUNCATED_IMAGES = True


class _CacheStats:
    """Tracks repeated usages of cached images."""

    def __init__(self):
        self.repeated_usages = {}


stats = _CacheStats()


def track_image_usage(url: str):
    """Track the usage count of a cached image."""
    if os.path.isfile(get_cached_filename(url)):
        stats.repeated_usages[url] = stats.repeated_usages.get(url, 0) + 1


def _save_image(filename: str, image: Image.Image):
    """Save an image to a file with high quality, never exposing a half-written file."""
    partial_filename = f"{filename}.{get_ident()}{PARTIAL_SUFFIX}"
    try:
        image.save(partial_filename, format=WEBP_FORMAT, lossless=True, quality=100, method=6)
        os.replace(partial_filename, filename)
    except Exception as e:
        util.logger.error(f"Failed to save image {filename}: {e}", exc_info=e)

        if os.path.isfile(partial_filename):
            os.remove(partial_filename)


def async_save_image(filename: str, image: Image.Image):
    """Save an image asynchronously."""
    Thread(target=_save_image, args=(filename, image.copy())).start()


def generate_filename(base: str, extension: str, width: int = None, height: int = None) -> str:
    """Generate a cache filename based on base name, dimensions, and extension."""
    sanitized_name = _sanitize_name(base)
    if width and height:
        sanitized_name += f"_{width}_{height}"
    return f"{CACHE_DIR}{sanitized_name}{extension}"


def _sanitize_name(base: str) -> str:
    return re.sub(r"\W+", "", base)[:128]


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
        image_data = await util.download_image(url)
        image = Image.open(image_data)
        async_save_image(filename, image)

        return image
    except Exception as e:
        util.logger.error(f"Failed to cache image from {url}: {e}", exc_info=e)
        if os.path.isfile(filename):
            os.remove(filename)

    return None


def cache_resized_image(image: Image.Image, url: str):
    """Cache a resized version of the image."""
    async_save_image(get_resized_cached_filename(url, image.width, image.height), image)


def load_cached_image(filename: str):
    """Load a cached image from disk, dropping it when it is unreadable."""
    if not os.path.isfile(filename):
        return None

    try:
        return Image.open(filename)
    except OSError as e:
        util.logger.warning(f"Removing unreadable cached image {filename}: {e}")
        os.remove(filename)

        return None


def get_cached_resized_image(url: str, width: int, height: int):
    """Retrieve a resized image from the cache."""
    if not url:
        return None

    filename = get_resized_cached_filename(url, width, height)
    return load_cached_image(filename)


def remove_cached_image(url: str):
    """Remove a cached image and its resized variants unless it's still in use."""
    if stats.repeated_usages.get(url, 0) > 1:
        stats.repeated_usages[url] -= 1
        return

    filename = get_cached_filename(url)
    if os.path.isfile(filename):
        os.remove(filename)
        util.logger.info(f"Removed cached image: {url}")

    for resized_filename in _get_resized_cached_filenames(url):
        os.remove(resized_filename)


def _get_resized_cached_filenames(url: str) -> list[str]:
    resized_name = re.compile(rf"{re.escape(_sanitize_name(url))}_\d+_\d+{re.escape(WEBP_EXTENSION)}")

    return [CACHE_DIR + entry for entry in os.listdir(CACHE_DIR) if resized_name.fullmatch(entry)]


@tasks.loop(seconds=3600)
async def save_cache_info():
    """Persist cache statistics."""
    dbconn.insert_object("stats", stats)


def _load_cache_info():
    """Load cache statistics from the database."""
    collection = dbconn.get_collection_for_object(_CacheStats)
    stats_json: dict = collection.find_one({"_id": "stats"})
    if stats_json:
        stats.repeated_usages.update(json.loads(stats_json.get("data", "{}")))
    else:
        util.logger.info("No cache data found.")


_load_cache_info()
