import traceback
import json
import sys

# settings
with open("settings.json") as settings_file:
    settings = json.load(settings_file)

# logger
class Log:
    def __init__(self):
        self.log_level = settings["logging"]["log_level"]
        self.debug("Creating logger")
        if self.log_level < 0 or self.log_level > 2:
            self.error("ValueError", "log_level in settings.json must be between 0 and 2")
        self.debug("Logger created")
    
    def error(self, error, message):
        explanation = ""
        if isinstance(error, Exception):
            error = error.__class__.__name__
            explanation = ": " + str(error)
            explanation = explanation if explanation != error else ""
        print(f">>> ERROR ({error}): {message}{explanation}")
        print("-"*30)
        traceback.print_exc()
        sys.exit(1)
    
    def progress(self, message):
        if self.log_level >= 1:
            print(message)
    
    def debug(self, message):
        if self.log_level == 2:
            print(f"> DEBUG: {message}")

logger = Log()

logger.debug("Beginning to load settings from settings.json for aux.py")
try:
    missing_data_string = settings["citations_csv"]["missing_data_string"]
    array_separator = settings["citations_csv"]["array_separator"]
    first_last_separator = settings["citations_csv"]["first_last_separator"]
except KeyError as e:
    logger.error(e, "settings.json file is missing required keys")
logger.debug("Finished loading settings from settings.json for aux.py")

# aux functions

def smart_title_case(string):
    """Gives title case for string besides ignored words"""
    lower_words = [
        "a",
        "an",
        "and",
        "as",
        "at",
        "but",
        "by",
        "for",
        "from",
        "if",
        "in",
        "into",
        "like",
        "near",
        "nor",
        "of",
        "off",
        "on",
        "once",
        "onto",
        "or",
        "so",
        "than",
        "that",
        "the",
        "to",
        "when",
        "with",
        "yet",
    ]
    words = string.split(" ")
    for i in range(len(words)):
        if i == 0 or i == len(words) - 1 or words[i] not in lower_words:
            words[i] = words[i].capitalize()
    return " ".join(words)

def isbn_formatting(isbn):
    """Formats ISBNs to remove common delimiters and reduce to numbers"""
    isbn = isbn.replace("-", "").replace(" ", "").lower()
    if isbn.startswith("isbn"):
        isbn = isbn[4:]
        if isbn.startswith(":"):
            isbn = isbn[1:]
    return isbn

def get_code_suffix_from_int(num):
    """
    Converts number (integer) to letter suffix. 
    1 gives a, 2 gives b, ... 26 gives z, 27 gives aa, ...
    """
    suffix = ""
    while num > 0:
        num -= 1
        remainder = num % 26
        suffix = chr(remainder + ord("a")) + suffix
        num = num // 26
    return suffix

def get_int_from_code_suffix(suffix):
    """Reverse operation of get_code_suffix_from_int"""
    number = 0
    for i, char in enumerate(reversed(suffix)):
        number += (ord(char) - ord("a") + 1) * (26 ** i)
    return number

def get_data_by_address(data, address):
    """Return the location at a given address, or missing_data_string if missing."""
    address_options = address.split("|")
    for address in address_options:
        if needs_processing := address.endswith("@"):
            address = address[:-1]
        data_chunk = data
        address_parts = address.split(".")
        for part_indx, part in enumerate(address_parts):
            # handle missing data
            if data_chunk == []:
                data_chunk = missing_data_string
                break
            # handle integer address part
            elif part.isdigit():
                if isinstance(data_chunk, list) and len(data_chunk) > int(part):
                    data_chunk = data_chunk[int(part)]
                else:
                    logger.error("Misuse of Integer in Response Address", f"An integer in api addresses should only be used when the preceeding address fragment gives a list. Instead, the preceeding address fragment gave a {type(data_chunk)}.")
            # handle * address part
            elif part == "*":
                if isinstance(data_chunk, list):
                    new_path = ".".join(address_parts[part_indx+1:])
                    data_chunk = array_separator.join(get_data_by_address(d, new_path)[1] for d in data_chunk)
                else:
                    logger.error("Misuse of * in Response Address", f"The * symbol in api addresses should only be used when the preceeding address fragment gives a list. Instead, the preceeding address fragment gave a {type(data_chunk)}.")
            # handle [] address part
            elif part.startswith("[") and part.endswith("]"):
                remaining_address = "." + address_parts[part_indx+1:] if len(address_parts) > part_indx + 1 else "" # not tested
                parts = [p + remaining_address for p in part[1:-1].split(",")]
                data_chunk = first_last_separator.join(get_data_by_address(data_chunk, p)[1] for p in parts)
                break
            # handle dictionary keys
            else:
                if part in data_chunk:
                    data_chunk = data_chunk[part]
                else:
                    logger.error("Missing Key in api Response", f"The response data is missing the key {part} when it was asked for")
        # if current address option is not returning missing data, return that data
        if data_chunk != missing_data_string:
            return needs_processing, data_chunk
    # if all address options returned missing data
    return needs_processing, missing_data_string
