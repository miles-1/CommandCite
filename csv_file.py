from aux import logger, settings, csv_file_name
from os.path import exists, dirname
import csv

class CSV:
    def __init__(self):
        self.file_name = csv_file_name
        if not exists(dirname(self.file_name)):
            logger.error("Bad CSV Path", "The directory specified in `citations_csv` of settings.json does not exist")
        if exists(self.file_name):
            with open(self.file_name, "r") as f:
                reader = csv.DictReader(f)
        else:
            reader = None
        self.headers = reader.fieldnames if reader is not None else None
        self.existing_content = list(reader)
        # TODO: make dict that keeps track of the number of citation codes
    
    def add_entry(self, citation_dict):
        # TODO
        pass

