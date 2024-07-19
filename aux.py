import re
import sys
import json
import traceback
from datetime import datetime
from os.path import join, dirname, isabs, exists

# settings
with open("settings.json") as settings_file:
    settings = json.load(settings_file)

# logger
class CommandCiteError(Exception):
    pass

class Log:
    log_level = settings["logging"]["log_level"]
    create_log_file = settings["logging"]["create_log_file"]

    def __init__(self):
        self.log = open("citation.log", "w") if self.create_log_file else None
        self.debug("Creating logger")
        if self.log_level < 0 or self.log_level > 2:
            self.error("ValueError", "log_level in settings.json must be between 0 and 2")
        self.debug("Logger created")
    
    def error(self, error:str|Exception, message:str, kill:bool=False):
        error_traceback = ""
        if isinstance(error, Exception):
            error = error.__class__.__name__
            error_traceback = "\n" + "-" * 30 + "\n" + traceback.format_exc()
        error_str = f">>> ERROR ({error}): {message}{error_traceback}"
        if self.create_log_file:
            self.log.write(error_str + "\n")
        print(error_str)
        if kill:
            self.log.close()
            sys.exit(2)
        else:
            raise CommandCiteError
    
    def progress(self, message:str, title_message:bool=False):
        if title_message:
            h_line, v_line = "─" * (len(message) + 2), "│"
            upper_cap = "╭" + h_line + "╮"
            lower_cap = "╰" + h_line + "╯"
            message = upper_cap + f"\n{v_line} " + message + f" {v_line}\n" + lower_cap
        if self.create_log_file:
            self.log.write(message + "\n")
        if self.log_level >= 1:
            print(message)
    
    def debug(self, message:str):
        message = f"> DEBUG: {message}"
        if self.create_log_file:
            self.log.write(message + "\n")
        if self.log_level == 2:
            print(message)

logger = Log()

def _get_path(settings_dict:dict, extension:str="", check_field:str|None=None):
    directory = settings_dict["directory"]
    directory = directory if isabs(directory) else join(dirname(sys.argv[0]), directory)
    if not exists(directory):
        logger.error("Folder Missing", f"The folder {directory} does not exist")
    complete_path = join(directory, settings_dict["filename"]) + extension if extension else directory
    return complete_path if check_field is None or settings_dict[check_field] else None

try:
    logger.debug("Beginning to load settings from settings.json for aux.py")
    # citations csv settings
    logger.debug("Loading citations csv settings from settings.json")
    csv_file_name = _get_path(settings["citations_csv"], extension=".csv")
    missing_data_string = settings["citations_csv"]["missing_data_string"]
    array_separator = settings["citations_csv"]["array_separator"]
    concat_separator = settings["citations_csv"]["concat_separator"]
    lower_case_all_caps_titles = settings["citations_csv"]["lower_case_all_caps_titles"]
    title_case_titles = settings["citations_csv"]["title_case_titles"]
    citation_code_format = settings["citations_csv"]["citation-code_format"]
    # markdown settings
    logger.debug("Loading markdown settings from settings.json")
    md_dir_name = _get_path(settings["markdown"], check_field="make_md")
    link_cited = settings["markdown"]["link_cited"]
    delete_unmatched_citations = settings["markdown"]["delete_unmatched_citations"]
    automate_pdf_link_doi = settings["markdown"]["automate_pdf_link"]["doi"]
    automate_pdf_link_isbn = settings["markdown"]["automate_pdf_link"]["isbn"]
    included_properties = settings["markdown"]["included_properties"]
    user_defined_properties = settings["markdown"]["user-defined_properties"]
    # bibliography settings
    logger.debug("Loading bibliography settings from settings.json")
    bibtex_file_name = _get_path(settings["bibliography"], extension=".bib", check_field="make_bibtex")
    hayagriva_file_name = _get_path(settings["bibliography"], extension=".yml", check_field="make_hayagriva")
    delete_unmatched_entries = settings["bibliography"]["delete_unmatched_entries"]
    # network settings
    logger.debug("Loading network settings from settings.json")
    timeout = settings["network"]["timeout"]
    num_retries = settings["network"]["num_retries"]
    retry_delay = settings["network"]["retry_delay"]
    # api preference settings
    logger.debug("Loading api preference settings from settings.json")
    primary_isbn = settings["api_preference"]["primary_isbn"]
    secondary_isbn = settings["api_preference"]["secondary_isbn"]
    # polite api settings
    logger.debug("Loading polite api settings from settings.json")
    project_name = settings["polite_api"]["project_name"]
    project_version = settings["polite_api"]["project_version"]
    project_url = settings["polite_api"]["project_url"]
    contact_email = settings["polite_api"]["contact_email"]
    # advanced settings
    logger.debug("Loading advanced settings from settings.json")
    openlibrary_url = settings["advanced"]["api"]["openlibrary"]["url"]
    googlebooks_url = settings["advanced"]["api"]["googlebooks"]["url"]
    read_encoding = settings["advanced"]["file_encoding"]["read_encoding"]
    write_encoding = settings["advanced"]["file_encoding"]["write_encoding"]
    info_headers = settings["advanced"]["csv_headers"]["info_headers"]
    header_addresses = settings["advanced"]["csv_headers"]
    if any(x not in header_addresses for x in ["crossref", "openlibrary", "googlebooks"]):
        logger.error("settings.json file is missing required keys in advanced.csv_headers")
    logger.debug("Finished loading settings from settings.json for aux.py")
except KeyError as e:
    logger.error(e, "settings.json file is missing required keys")

# program-managed headers
program_headers = ["citation-code", "add-date"]

# help string
help_string = """FLAGS:
              
--help                                     Print this message
              
--update-all                               Fill in any blanks for program-managed 
                                           headers of citations csv file for all 
                                           rows, and update markdowns and bibliography 
                                           files if they exist
              
--update [citation-code]                   Same as --update-all but instead for 
                                           specified [citation-code]
              
--rename [citation-code] [new-base-code]   Change the citation code for the 
                                           given [citation-code] to have a new one,
                                           with base code specified by [new-base-code] 
                                           (no suffix should be included)
              
[doi-or-isbn] --setcode [new-base-code]    For a given DOI or ISBN, set the citation 
                                           code to have a base code of [new-base-code]

Other than the restrictions listed below, any sequence or repetition of flags, DOIs 
or ISBNs can be given to this program.

NOTES:
              
    --help cannot be used in combination with other flags
              
    --update-all and --update cannot be used together
              
    For markdown documents, --rename only updates the specified code in file names 
    and the yaml frontmatter, not note text"""

# title and abstract formatting functions
def format_title(string:str) -> str:
    """Replaces special characters and capitalizes if specified in settings.json"""
    if string == missing_data_string:
        return string
    string = replace_special_characters(string)
    if lower_case_all_caps_titles and string.isupper():
        string = ":".join(fragment.capitalize() for fragment in string.split(":"))
    return make_smart_title_case(string) if title_case_titles else string

def remove_html_tags(string:str) -> str:
    """Removes any HTML tags (aka any tags with <>) from string."""
    return re.sub(r"<.*?>", "", string)

def replace_special_characters(string:str) -> str:
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
        "\n": "",
        "∼": "~",
        " ": " ",
    }
    for character, replacement in replacement_dict.items():
        string = string.replace(character, replacement)
    return string

def make_smart_title_case(string:str) -> str:
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
def format_names(names:list) -> str:
    return array_separator.join(split_name(name) for name in names)

def split_name(name:str) -> str:
    """Attempts to collect family and given name connected by the \"concat_separator\" by splitting the given string"""
    if ". " in name:
        name_lst = list(reversed(name.rsplit(". ", 1)))
        name_lst[1] += "."
    else:
        name_lst = list(reversed(name.rsplit(" ", 1)))
    return concat_separator.join(name_lst)

# isbn formatting function
def format_isbn(isbn:str) -> str:
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
def format_base_citation_code(code:str) -> str:
    return re.sub(r"([a-z])\b", r"\1_",
                  re.sub("\\s+", "_", 
                         re.sub(r"[\\/:;*\[\]?\"'<>|]", "", 
                                code)))

def get_citation_code_parts(code:str) -> str:
    base_code = re.sub(r"[a-z]+\b", "", code)
    code_suffix = re.match(r".*?([a-z]+)\b", code)
    if code_suffix is not None:
        code_suffix = code_suffix.group(1)
    return base_code, code_suffix

def get_code_suffix_from_int(num:int) -> str:
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

def get_int_from_code_suffix(suffix:str) -> int:
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

def is_valid_citation_code(code:str) -> bool:
    """Verifies if a full citation code is of a valid format."""
    base_code, code_suffix = get_citation_code_parts(code)
    return code_suffix is not None and format_base_citation_code(base_code) == base_code

# data retrieval and formatting functions
def get_data_by_address(data:dict|list|str|int|bool, address:str) -> tuple[bool,any]:
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

def has_data(data:str) -> bool:
    return data not in ("", missing_data_string)

def get_date_part(date_string:str, part) -> int:
    date_formats = {
        # date_format: (has_month, has_day)
        "%b %d, %Y": (True, True),     # Jan 01, 2020
        "%B %d, %Y": (True, True),     # January 01, 2020
        "%Y-%m-%d": (True, True),      # 2020-01-01
        "%Y-%m": (True, False),        # 2020-01
        "%B %Y": (True, False),        # January 2020 
        "%Y": (False, False),          # 2020
    }
    date_obj = None
    for date_format, (has_month, has_day) in date_formats.items():
        try:
            date_obj = datetime.strptime(date_string, date_format)
            if part == "year":
                return date_obj.year
            elif part == "month" and has_month:
                return date_obj.month
            elif part == "day" and has_day:
                return date_obj.day
            break
        except ValueError:
            continue
    return missing_data_string

# yaml frontmatter link function
def make_md_link(string:str, pdf:bool=False) -> str:
    extension = ".pdf" if pdf else ""
    return f"\"[[{string}{extension}]]\""

# functions for main
def format_id_num_arguments(args:list[str], flag:str="--setcode") -> tuple:
    result = []
    i = 0
    while i < len(args):
        id_num = args[i]
        if id_num.startswith("--"):
            logger.error("Unrecognized Flag", f"The flag \"{id_num}\" is not recognized. Only \"--update\", \"--update-all\", \"--setcode\", \"--rename\", and \"--help\" are recognized.")
        id_num_type = get_id_num_type(id_num)
        if id_num_type is None:
            logger.error("Unrecognized Argument", f"The argument {id_num} was expected to be a DOI or an ISBN, but follows the format of neither. DOIs take the form \"10.xxxx/abcd\", whereas ISBNs are just numbers.")
        if i < len(args) - 1 and args[i+1] == flag:
            custom_base_code = format_base_citation_code(args[i+2])       
            result.append((id_num, id_num_type, custom_base_code))
            i += 3
        else:
            result.append((id_num, id_num_type, None))
            i += 1
    return result

def get_id_num_type(code:str) -> str|None:
    if re.match(r"10\.\d{4,}/.+", code) is not None:
        return "doi"
    if format_isbn(code).isdigit():
        return "isbn"
    return None

def verify_arguments(arguments:list[str], all_codes:list[str]) -> tuple:
    update_all_entries = False
    entries_to_update = []
    entries_to_rename = {}
    # check for arguments
    if len(arguments) == 0:
        logger.error("No Arguments", "This program requires at least one argument to run")
    if "--help" in arguments:
        print(help_string)
        sys.exit(1)
    # handle --update-all tag
    if "--update-all" in arguments:
        for _ in range(arguments.count("--update-all")):
            arguments.pop(arguments.index("--update-all"))
        if "--update" in arguments:
            logger.error("Bad Flag Use", "The \"--update\" flag is not allowed if \"--update-all\" is useds")
        update_all_entries = True
        logger.debug("All entries are set to update")
    # handle --update tag
    if "--update" in arguments:
        for _ in range(arguments.count("--update")):
            tag_indx = arguments.index("--update")
            if len(arguments) <= tag_indx + 1:
                logger.error("Bad Flag Use", "The \"--update\" flag must be followed by a valid citation code")
            citation_code = arguments[tag_indx + 1]
            if citation_code not in all_codes:
                logger.error("Code Does Not Exist", f"The \"--update\" flag must be followed by a citation code found in the citations csv, and \"{citation_code}\" was not found")
            for _ in range(2):
                arguments.pop(tag_indx) # remove tag and citation code
            if citation_code not in entries_to_update:
                entries_to_update.append(citation_code)
        logger.debug(f"The following entries are set to update: {', '.join(entries_to_update)}")
    # handle --rename tag
    if "--rename" in arguments:
        for _ in range(arguments.count("--rename")):
            tag_indx = arguments.index("--rename")
            if len(arguments) <= tag_indx + 2 or \
                arguments[tag_indx+1] not in all_codes or \
                arguments[tag_indx+2].startswith("--"):
                if len(arguments) <= tag_indx + 2:
                    extra_info = ""
                elif arguments[tag_indx+1] not in all_codes:
                    extra_info = f" However, the citation code \"{arguments[tag_indx+1]}\" was not found in the citations csv."
                else:
                    extra_info = f" However, the tag \"{arguments[tag_indx+2]}\" was found where the base code should be."
                logger.error("Bad Flag Use", f"The \"--update\" flag must be followed by (1) a citation code found in the citations csv and (2) a new base citation code (no suffix) that will serve as its replacement.{extra_info}")
            old_code, new_code = arguments[tag_indx+1], format_base_citation_code(arguments[tag_indx+2])
            if old_code in entries_to_rename:
                logger.debug(f"Code {old_code} already marked for renaming. Updating to rename to {new_code}")
            entries_to_rename[old_code] = new_code
            for _ in range(3):
                arguments.pop(tag_indx) # remove tag, citation code, and new base citation code
    # collect dois and isbns
    return update_all_entries, entries_to_update, entries_to_rename, format_id_num_arguments(arguments)
