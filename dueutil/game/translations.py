import os
import json

from discord.ext import commands

from dueutil import util


LOCALIZATION_PATH = "dueutil/game/configs/localization/"
DEFAULT_LANGUAGE = "en"

translations = {}


def _get_translation(language: str, full_key: str) -> str:
    category, command, key = full_key.split(".")

    try:
        return translations[language][category][command][key]
    except KeyError:
        return translations.get(DEFAULT_LANGUAGE, {}).get(category, {}).get(command, {}).get(key, full_key)


def find_translation(_: commands.Context, key: str, *args, force_update: bool = False):
    """
    Finds the translation for a key in the current language

    Parameters
    ----------
    ctx: :class:`discord.ext.commands.Context`
        The context of the message
    key: :class:`str`
        The key to find
    args: :class:`list`
        The arguments to replace the key with
    force_update: :class:`bool`
        Update the translations. Defaults to false

    Returns
    -------
    translation: :class:`str`
        The translated string or the key if no translation was found
    """
    if translations == {} or force_update:
        _load()

    # Get the language of the server
    # TODO: Fetch it from serverconfigs
    language = DEFAULT_LANGUAGE

    # Get the translation
    translation = _get_translation(language, key)

    # Replace the arguments
    for arg in args:
        translation = translation.replace("{}", arg, 1)

    return translation


def _load():
    # Check if path LOCALIZATION_PATH exists
    if not os.path.exists(LOCALIZATION_PATH):
        return util.logger.warning("Localization path does not exist, skipping translations")

    temp_translations = {}
    for language in os.listdir(LOCALIZATION_PATH):
        if language == ".git":
            continue
        temp_translations[language] = {}
        for category in os.listdir(LOCALIZATION_PATH + language):
            temp_translations[language][category] = {}
            for file in os.listdir(LOCALIZATION_PATH + language + "/" + category):
                file_name = file.split(".")[0]
                temp_translations[language][category][file_name] = json.load(
                    open(LOCALIZATION_PATH + language + "/" + category + "/" + file, "r", encoding="utf-8")
                )

    translations.update(temp_translations)
    util.logger.info(f"Loaded {len(translations)} translations")


_load()
