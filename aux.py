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