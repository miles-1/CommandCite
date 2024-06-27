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

# aux functions

def smart_title_case(string):
    # TODO
    pass

def isbn_formatting(isbn):
    # TODO
    pass

def get_code_suffix_from_int(int):
    # TODO
    pass

def get_int_from_code_suffix(suffix):
    # TODO
    pass

def getDataByAddress(data, path):
    # TODO
    NA = "N/A"
    path_options = path.split("|")
    for option in path_options:
        option_parts = option.split("/")
        value = data
        for part in option_parts:
            if value == NA:
                break
            elif value == []:
                value = NA
                break
            elif part.isdigit():
                if len(value) > int(part):
                    value = value[int(part)]
                else:
                    value = NA
            else:
                value = value.get(part, NA)
        if value != NA:
            return value
    return value
