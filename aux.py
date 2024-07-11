import traceback
import json
import sys
import re
from os.path import join, dirname, isabs

# settings
with open("settings.json") as settings_file:
    settings = json.load(settings_file)

# logger
class Log:
    log_level = settings["logging"]["log_level"]
    create_log_file = settings["logging"]["create_log_file"]

    def __init__(self):
        self.log = open("citation.log", "w") if self.create_log_file else None
        self.debug("Creating logger")
        if self.log_level < 0 or self.log_level > 2:
            self.error("ValueError", "log_level in settings.json must be between 0 and 2")
        self.debug("Logger created")
    
    def error(self, error, message):
        error_traceback = ""
        if isinstance(error, Exception):
            error = error.__class__.__name__
            error_traceback = "\n" + "-" * 30 + "\n" + traceback.format_exc()
        error_str = f">>> ERROR ({error}): {message}{error_traceback}"
        if self.create_log_file:
            self.log.write(error_str + "\n")
            self.log.close()
        print(error_str)
        sys.exit(2)
    
    def progress(self, message):
        if self.create_log_file:
            self.log.write(message + "\n")
        if self.log_level >= 1:
            print(message)
    
    def debug(self, message):
        message = f"> DEBUG: {message}"
        if self.create_log_file:
            self.log.write(message + "\n")
        if self.log_level == 2:
            print(message)

logger = Log()

def _get_path(settings_dict, extension="", check_field=None):
    directory = settings_dict["directory"]
    directory = directory if isabs(directory) else join(dirname(sys.argv[0]), directory)
    complete_path = join(directory, settings_dict["filename"]) + extension if extension else directory
    return complete_path if not isinstance(check_field, str) or settings_dict[check_field] else None

try:
    logger.debug("Beginning to load settings from settings.json for aux.py")
    # citations csv settings
    logger.debug("Loading citations csv settings from settings.json")
    missing_data_string = settings["citations_csv"]["missing_data_string"]
    array_separator = settings["citations_csv"]["array_separator"]
    concat_separator = settings["citations_csv"]["concat_separator"]
    title_case_titles = settings["citations_csv"]["title_case_titles"]
    # file names
    logger.debug("Loading filenames from settings.json")
    csv_file_name = _get_path(settings["citations_csv"], extension=".csv")
    md_dir_name = _get_path(settings["markdown"], check_field="make_md")
    bibtex_file_name = _get_path(settings["bibliography"], extension=".bib", check_field="make_bibtex")
    hayagriva_file_name = _get_path(settings["bibliography"], extension=".yml", check_field="make_hayagriva")
    logger.debug("Finished loading settings from settings.json for aux.py")
except KeyError as e:
    logger.error(e, "settings.json file is missing required keys")

# program-managed headers
program_headers = ["citation-code", "add-date"]

# title and abstract formatting functions
def format_title(string):
    """Replaces special characters and capitalizes if specified in settings.json"""
    if string == missing_data_string:
        return string
    string = replace_special_characters(string)
    return make_smart_title_case(string) if title_case_titles else string

def remove_html_tags(string):
    """Removes any HTML tags (aka any tags with <>) from string."""
    return re.sub(r"<.*?>", "", string)

def replace_special_characters(string):
    """Replaces special characters, HTML tags, and HTML encoded characters in a string"""
    string = remove_html_tags(string)
    replacement_dict = {
        "&amp;": "&",
        "&quot;": "\"",
        "&apos;": "'",
        "&lt;": "<",
        "&gt;": ">",
        " ": " ",
        "‐": "-",
        "–": "-",
        "—": "-",
        "’": "'",
    }
    for character, replacement in replacement_dict.items():
        string = string.replace(character, replacement)
    return string

def make_smart_title_case(string):
    """Gives title case for string besides ignored words, AND replaces special characters"""
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

# author name formatting function
def format_names(names):
    return array_separator.join(split_name(name) for name in names)

def split_name(name):
    """Attempts to collect family and given name connected by the \"concat_separator\" by splitting the given string"""
    if ". " in name:
        name_lst = list(reversed(name.rsplit(". ", 1)))
        name_lst[1] += "."
    else:
        name_lst = list(reversed(name.rsplit(" ", 1)))
    return concat_separator.join(name_lst)

# isbn formatting function
def format_isbn(isbn):
    """Formats ISBNs to remove common delimiters and reduce to numbers"""
    isbn = isbn.strip().replace(" ", "").lower()
    if isbn.startswith("isbn"):
        isbn = isbn[4:]
        if isbn.startswith("-13") or isbn.startswith("-10"):
            isbn = isbn[3:]
        if isbn.startswith(":"):
            isbn = isbn[1:]
    isbn = isbn.replace("-", "")
    return isbn

# citation code functions
def format_base_citation_code(code):
    return re.sub(r"([a-z])\b", r"\1_",
                  re.sub("\\s+", "_", 
                         re.sub(r"[\\/:;*\[\]?\"'<>|]", "", 
                                code)))

def get_citation_code_parts(code):
    base_code = re.sub(r"[a-z]+\b", "", code)
    code_suffix = re.match(r".*?([a-z]+)\b", code)
    if code_suffix is not None:
        code_suffix = code_suffix.group(1)
    return base_code, code_suffix

def get_code_suffix_from_int(num):
    """
    Converts number (integer) to letter suffix. 
    1 gives a, 2 gives b, ... 26 gives z, 27 gives aa, ...
    """
    if not isinstance(num, int) or num < 1:
        logger.error("Incorrect Input", f"Bad input for get_code_suffix_from_int: {num}")
    suffix = ""
    while num > 0:
        num -= 1
        remainder = num % 26
        suffix = chr(remainder + ord("a")) + suffix
        num = num // 26
    return suffix

def get_int_from_code_suffix(suffix):
    """
    Converts letter suffix to number (integer).
    a gives 1, b gives 2, ... z gives 26, aa gives 27, ...
    """
    if not suffix.isalpha():
        logger.error("Incorrect Input", f"Bad input for get_int_from_code_suffix: {suffix}")
    number = 0
    for i, char in enumerate(reversed(suffix)):
        number += (ord(char) - ord("a") + 1) * (26 ** i)
    return number

def is_valid_citation_code(code):
    """Verifies if a full citation code is of a valid format."""
    base_code, code_suffix = get_citation_code_parts(code)
    return code_suffix is not None and format_base_citation_code(base_code) == base_code

# data retrieval function
def get_data_by_address(data, address):
    """Return the location at a given address, or missing_data_string if missing."""
    if match := re.match(r".*\[.*?([\.\*\[\]]).*?\].*", address):
        logger.error("Misuse of [] in Response Address", f"The [] address notation in \"csv_headers\" of settings.json should only hold individual keys or indices separated by commas, but contained a \"{match.group(1)}\".")
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
                if isinstance(data_chunk, list):
                    if len(data_chunk) > int(part):
                        data_chunk = data_chunk[int(part)]
                    else:
                        data_chunk = missing_data_string
                        break
                else:
                    logger.error("Misuse of Integer in Response Address", f"An integer in api addresses should only be used when the preceeding address fragment gives a list, where the index is less than the length of that list. Instead, the preceeding address fragment gave a {type(data_chunk)}.")
            # handle * address part
            elif part == "*":
                if isinstance(data_chunk, list):
                    new_path = ".".join(address_parts[part_indx+1:])
                    data_chunk = array_separator.join(
                        x for d in data_chunk
                        if (x := str(get_data_by_address(d, new_path)[1])) is not missing_data_string
                    )
                    break # do not continue after recursion
                else:
                    logger.error("Misuse of * in Response Address", f"The * symbol in api addresses should only be used when the preceeding address fragment gives a list. Instead, the preceeding address fragment gave a {type(data_chunk)}.")
            # handle [] address part
            elif part.startswith("[") and part.endswith("]"):
                remaining_address = "." + ".".join(address_parts[part_indx+1:]) if len(address_parts) > part_indx + 1 else ""
                parts = [p + remaining_address for p in part[1:-1].split(",")]
                data_chunk = concat_separator.join(
                    x for p in parts
                    if (x := str(get_data_by_address(data_chunk, p)[1])) is not missing_data_string
                )
                break # do not continue after recursion
            # handle dictionary keys
            else:
                if part in data_chunk:
                    data_chunk = data_chunk[part]
                else:
                    data_chunk = missing_data_string
                    break
        # if current address option is not returning missing data, return that data
        if data_chunk != missing_data_string:
            return needs_processing, data_chunk
    # if all address options returned missing data
    return needs_processing, missing_data_string

# program argument processing function
def format_arguments(args, flag="--setcode"):
    result = []
    i = 0
    while i < len(args):
        entry_code = args[i]
        if entry_code.startswith("--"):
            logger.error("Unrecognized Flag", f"The flag \"{entry_code}\" is not recognized. Only \"--update\", \"--update-all\", \"--setcode\", \"--rename\", and \"--help\" are recognized.")
        entry_code_type = get_entry_code_type(entry_code)
        if entry_code_type is None:
            logger.error("Unrecognized Argument", f"The argument {entry_code} was expected to be a DOI or an ISBN, but follows the format of neither. DOIs take the form \"10.xxxx/abcd\", whereas ISBNs are just numbers.")
        if i < len(args) - 1 and args[i+1] == flag:
            custom_base_code = format_base_citation_code(args[i+1])       
            result.append((entry_code, entry_code_type, custom_base_code))
            i += 3
        else:
            result.append((entry_code, entry_code_type, None))
            i += 1
    return result

def get_entry_code_type(code):
    if re.match(r"10\.\d{4,}/.+", code) is not None:
        return "doi"
    if format_isbn(code).isdigit():
        return "isbn"
    return None