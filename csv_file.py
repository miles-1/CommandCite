from aux import logger, settings, csv_file_name, program_headers, \
    format_base_citation_code, get_citation_code_parts, get_code_suffix_from_int, get_int_from_code_suffix, is_valid_citation_code
from os.path import exists, dirname
from collections import defaultdict
from copy import deepcopy
import csv

try:
    logger.debug("Beginning to load settings from settings.json for csv_file.py")
    # citations csv settings
    logger.debug("Loading citations csv settings from settings.json")
    missing_data_string = settings["citations_csv"]["missing_data_string"]
    array_separator = settings["citations_csv"]["array_separator"]
    concat_separator = settings["citations_csv"]["concat_separator"]
    update_blanks_automatically = settings["citations_csv"]["update_blanks_automatically"]
    # advanced settings
    logger.debug("Loading advanced settings from settings.json")
    info_headers = settings["advanced"]["csv_headers"]["info_headers"]
    read_encoding = settings["advanced"]["file_encoding"]["read_encoding"]
    write_encoding = settings["advanced"]["file_encoding"]["write_encoding"]
    logger.debug("Finished loading settings from settings.json for csv_file.py")
except KeyError as e:
    logger.error(e, "settings.json file is missing required keys")

class CSV:
    old_entries_copy = []
    existing_entries = []
    entry_info_dict = {}
    base_citation_code_count = defaultdict(int)
    all_headers = program_headers + info_headers

    def __init__(self):
        logger.debug("Creating new CSV object")
        self.file_name = csv_file_name
        if not exists(dirname(self.file_name)):
            logger.error("Bad CSV Path", "The directory specified in \"citations_csv\" of settings.json does not exist")
        if not exists(self.file_name):
            logger.debug("No citations csv file found. New file will be created with new entries.")
        else:
            # open csv file
            logger.debug("Opening existing citations csv file")
            with open(self.file_name, "r", encoding=read_encoding) as f:
                reader = csv.DictReader(f)
            # collect entries in file
            logger.debug("Reading and collecting entries of citations csv file")
            self.all_headers = reader.fieldnames
            for entry in reader:
                if any(value != "" for value in entry.values()):
                    entry_dict = {header: "" for header in program_headers + info_headers} # make sure each row includes reqd headers
                    entry_dict.update(entry)
                    self.existing_entries.append(entry_dict)
            self.old_entries_copy = deepcopy(self.existing_entries)
            # collect citation codes
            logger.debug("Collecting entry citation codes of citations csv file")
            for entry_indx, entry in enumerate(self.existing_entries):
                citation_code = entry["citation-code"]
                if citation_code == "":
                    logger.error("Missing Citation Code", f"At least one entry (row {entry_indx}) is missing a citation code. Please manually enter a valid code for that entry, or remove the row entirely.")
                base_code, code_suffix = get_citation_code_parts(citation_code)
                if not is_valid_citation_code(citation_code):
                    message = "It is missing a suffix (i.e., a lowercase letter or a sequence of them, where \"a\" represents the first occurrence of a base code, \"b\" a second, and so forth)" \
                        if code_suffix is None else \
                        f"The code would be valid if changed to \"{format_base_citation_code(base_code) + code_suffix}\""
                    logger.error("Invalid Citation Code", f"The citation code \"{citation_code}\" is not valid. {message}")
                if citation_code in self.entry_info_dict:
                    logger.error("Repeat Citation Codes Found", f"Citation code \"{citation_code}\" found multiple times in citations csv file (found at row {self.entry_info_dict[citation_code][0]} and row {entry_indx}). Please manually input a unique and valid citation code for each row.")
                self.entry_info_dict[citation_code] = (entry_indx, self._has_empty_cells(entry))
                self.base_citation_code_count[base_code] = max(
                    get_int_from_code_suffix(code_suffix),
                    self.base_citation_code_count[base_code]
                )
    
    def add_entry(self, citation_dict):
        base_citation_code = citation_dict["citation-code"]
        logger.debug(f"Adding suffix to base citation code {base_citation_code} and adding to csv file")
        self._add_citation_code_suffix(base_citation_code, citation_dict)
        full_entry_dict = {header: "" for header in self.all_headers} # make sure each row includes current headers
        full_entry_dict.update(citation_dict)
        self.entry_info_dict[full_entry_dict["citation-code"]] = (len(self.existing_entries), self._has_empty_cells(full_entry_dict))
        self.existing_entries.append(full_entry_dict)

    def save_file(self, revert_to_old=False):
        with open(csv_file_name, "w", encoding=write_encoding, newline="") as f:
            writer = csv.DictWriter(f, fieldnames=self.all_headers)
            writer.writeheader()
            writer.writerows(self.existing_entries if not revert_to_old else self.old_entries_copy)


    def get_entry(self, citation_code):
        self._check_code_exists(citation_code)
        entry_indx, _ = self.entry_info_dict[citation_code]
        return self.existing_entries[entry_indx]
    
    def update_entry(self, citation_code, citation_dict):
        entry = self.get_entry(citation_code)
        if self._has_empty_cells(entry):
            logger.debug(f"Updating missing data in {citation_code}")
            for header, cell in entry.items():
                if cell == "":
                    entry[header] = citation_dict[header]
        else:
            logger.debug(f"No missing data found in {citation_code}")
    
    def get_entries_needing_updating(self):
        return [self.existing_entries[entry_indx] for entry_indx, has_empty_cells in self.entry_info_dict if has_empty_cells]

    def update_all_entries(self, citation_dicts_list):
        for citation_dict in citation_dicts_list:
            self.update_entry(citation_dict["citation-code"], citation_dict)

    def change_citation_code(self, current_code, new_base_code):
        logger.debug(f"Changing citation code {current_code} to have base code of {new_base_code}")
        new_base_code = format_base_citation_code(new_base_code)
        self._check_code_exists(current_code)
        entry = self.existing_entries[self.entry_info_dict[current_code][0]]
        self._add_citation_code_suffix(new_base_code, entry)
        new_code = entry["citation-code"]
        self.entry_info_dict[new_code] = self.entry_info_dict[current_code]
        self.entry_info_dict.pop(current_code)
        logger.debug(f"Citation code {current_code} changed to {new_code}")
    
    def citation_code_exists(self, code):
        return code in self.entry_info_dict

    def _add_citation_code_suffix(self, base_code, citation_dict):
        self.base_citation_code_count[base_code] += 1
        citation_dict["citation-code"] += get_code_suffix_from_int(self.base_citation_code_count[base_code])
    
    def _has_empty_cells(self, citation_dict):
        return any(citation_dict[header] == "" for header in program_headers)

    def _check_code_exists(self, code):
        if code not in self.entry_info_dict:
            logger.error("Specified Code Does Not Exist", f"The citation code \"{code}\" is not found in the citations csv file.")