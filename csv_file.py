from aux import logger, csv_file_name, program_headers, \
    info_headers, read_encoding, write_encoding, \
    array_separator, missing_data_string, \
    format_base_citation_code, get_citation_code_parts, get_code_suffix_from_int, get_int_from_code_suffix, is_valid_citation_code, has_data
from os.path import exists
from collections import defaultdict
from copy import deepcopy
from datetime import datetime
import csv

class _EntryRow:
    def __init__(self, csv_headers=[]):
        self.row_lst = []
        self.code_dict = {}
        self.base_citation_code_count = defaultdict(int)
        required_headers = program_headers + info_headers
        if not isinstance(csv_headers, list):
            csv_headers = []
        self.headers = tuple(required_headers + list(set(csv_headers) - set(required_headers)))

    def add_from_file(self, citation_dict):
        # handle manually entered dicts
        if not has_data(citation_dict["add-date"]):
            citation_dict["add-date"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        if not has_data(citation_dict["type"]):
            if has_data(citation_dict["doi"]):
                citation_dict["type"] = "article"
            elif has_data(citation_dict["isbn"]):
                citation_dict["type"] = "book"
            else:
                citation_dict["type"] = "article"
        # add to row_lst
        code, row_indx, has_empty_cells = self._add_to_row_lst(citation_dict)
        # handle errors
        if code == "":
            logger.error("Missing Citation Code", f"An entry (row {row_indx}) is missing a citation code. Please manually enter a valid code for that entry, or remove the row entirely.")
        base_code, code_suffix = get_citation_code_parts(code)
        if not is_valid_citation_code(code):
            message = "It is missing a suffix (i.e., a lowercase letter or a sequence of them, where \"a\" represents the first occurrence of a base code, \"b\" a second, and so forth)" \
                if code_suffix is None else \
                f"The code would be valid if changed to \"{format_base_citation_code(base_code) + code_suffix}\""
            logger.error("Invalid Citation Code", f"The citation code \"{code}\" is not valid. {message}")
        if code in self.code_dict:
            logger.error("Repeat Citation Codes Found", f"Citation code \"{code}\" found multiple times in citations csv file (found at row {self.code_dict[code][0]} and row {row_indx}). Please manually input a unique and valid citation code for the repeat rows.")
        # add to code_dict
        self.code_dict[code] = (row_indx, has_empty_cells)
        # add to base_citation_code_count
        self.base_citation_code_count[base_code] = max(
            get_int_from_code_suffix(code_suffix),
            self.base_citation_code_count[base_code]
        )
    
    def add_from_api(self, citation_dict):
        base_citation_code = citation_dict["citation-code"]
        logger.debug(f"Adding suffix to base citation code {base_citation_code} and adding to csv file")
        self._add_citation_code_suffix(base_citation_code, citation_dict)
        code, row_indx, has_empty_cells = self._add_to_row_lst(citation_dict)
        self.code_dict[code] = (row_indx, has_empty_cells)
        logger.progress(f"Added citation code {code} to entry, and added entry to citations csv file")
        return citation_dict
    
    def _add_to_row_lst(self, citation_dict):
        full_dict = {header: "" for header in self.headers}
        full_dict.update(citation_dict)
        self.row_lst.append(full_dict)
        code, row_indx, has_empty_cells = full_dict["citation-code"], len(self.row_lst) - 1, self.has_empty_program_cells(full_dict)
        return code, row_indx, has_empty_cells

    def __getitem__(self, code):
        self._check_code_exists(code)
        row_indx = self.code_dict[code][0]
        return self.row_lst[row_indx]

    def has_empty_program_cells(self, code_or_dict):
        if isinstance(code_or_dict, str):
            code = code_or_dict
            citation_dict = self[code]
        else:
            citation_dict = code_or_dict
        return any(citation_dict[header] == "" for header in info_headers)

    def change_citation_code(self, current_code, new_base_code):
        logger.debug(f"Changing citation code {current_code} to have base code of {new_base_code}")
        citation_dict = self[current_code]
        self._add_citation_code_suffix(new_base_code, citation_dict, new_code=True)
        new_code = citation_dict["citation-code"]
        self.code_dict[new_code] = self.code_dict[current_code]
        self.code_dict.pop(current_code)
        logger.progress(f"Citation code {current_code} changed to {new_code} in citations csv")
        return new_code
    
    def fill_missing_cells(self, code):
        citation_dict = self[code]
        if self.has_empty_program_cells(citation_dict):
            for header in info_headers:
                if citation_dict[header] == "":
                    citation_dict[header] = missing_data_string
            logger.debug(f"Filling empty cells of {code} in citations csv")

    def get_rows(self, copy=False):
        return deepcopy(self.row_lst) if copy else self.row_lst
    
    def get_headers(self):
        return self.headers
    
    def get_codes(self):
        return tuple(self.code_dict.keys())
    
    def get_entries_needing_updating(self):
        return tuple(code for code, (_, has_empty_cells) in self.code_dict.items() if has_empty_cells)

    def get_id_nums(self):
        id_nums = {"doi": [], "isbn": []}
        for row in self.row_lst:
            for id_num_type in ("doi", "isbn"):
                if has_data(row[id_num_type]):
                    id_nums[id_num_type].append(row[id_num_type])
        return id_nums
    
    def get_codes_that_cite_code(self, code):
        code_lst = []
        id_num = self[code]["doi"]
        if not has_data(id_num):
            return None
        for row_dict in self.row_lst:
            code, cited_dois = row_dict["citation-code"], row_dict["cited-dois"]
            if has_data(cited_dois) and id_num in cited_dois.split(array_separator):
                code_lst.append(code)
        return code_lst if len(code_lst) > 0 else None
    
    def get_codes_cited_by_code(self, code):
        code_lst = []
        cited_dois = self[code]["cited-dois"]
        if not has_data(cited_dois):
            return None
        cited_dois = cited_dois.split(array_separator)
        for row_dict in self.row_lst:
            code, id_num = row_dict["citation-code"], row_dict["doi"]
            if id_num in cited_dois:
                code_lst.append(code)
        return sorted(code_lst) if len(code_lst) > 0 else None

    def _add_citation_code_suffix(self, base_code, citation_dict, new_code=True):
        self.base_citation_code_count[base_code] += 1
        if new_code:
            citation_dict["citation-code"] = base_code
        citation_dict["citation-code"] += get_code_suffix_from_int(self.base_citation_code_count[base_code])
    
    def _check_code_exists(self, code):
        if code not in self.code_dict:
            logger.error("Specified Code Does Not Exist", f"The citation code \"{code}\" is not found in the citations csv file.")


class CSV:
    old_entries_copy = None

    def __init__(self):
        logger.debug("Creating new CSV object")
        self.file_name = csv_file_name
        if not exists(self.file_name):
            logger.debug("No citations csv file found. New file will be created with new entries.")
            self.entry_rows = _EntryRow()
        else:
            # open csv file
            logger.debug("Opening existing citations csv file")
            with open(self.file_name, "r", encoding=read_encoding) as f:
                reader = csv.DictReader(f)
                self.entry_rows = _EntryRow(reader.fieldnames)
                for entry in reader:
                    if any(value != "" for value in entry.values()):
                        self.entry_rows.add_from_file(entry)
            # collect entries in file
            logger.debug("Reading and collecting entries of citations csv file")
            self.old_entries_copy = self.entry_rows.get_rows(copy=True)
        self.all_headers = self.entry_rows.get_headers()
    
    def add_from_api(self, citation_dict):
        return self.entry_rows.add_from_api(citation_dict)

    def save_file(self, revert_to_old=False):
        current_rows = self.entry_rows.get_rows()
        if (revert_to_old and self.old_entries_copy is None) or len(current_rows) == 0:
            return
        with open(csv_file_name, "w", encoding=write_encoding, newline="") as f:
            writer = csv.DictWriter(f, fieldnames=self.all_headers)
            writer.writeheader()
            writer.writerows(
                self.old_entries_copy
                if revert_to_old
                else current_rows
            )

    def get_entry(self, citation_code):
        return self.entry_rows[citation_code]
    
    def update_entry(self, citation_code, new_citation_dict):
        old_citation_dict = self.get_entry(citation_code)
        if self.entry_rows.has_empty_program_cells(old_citation_dict):
            for header, cell in old_citation_dict.items():
                if cell == "":
                    old_citation_dict[header] = new_citation_dict[header]
            logger.progress(f"Updated missing data in {citation_code} in citations csv file")
        else:
            logger.debug(f"No missing data found in {citation_code}")
    
    def fill_missing_cells(self, code):
        self.entry_rows.fill_missing_cells(code)
    
    def get_entries_needing_updating(self):
        return self.entry_rows.get_entries_needing_updating()

    def get_all_id_nums(self):
        return self.entry_rows.get_id_nums()
    
    def get_all_citation_codes(self):
        return self.entry_rows.get_codes()
    
    def change_citation_code(self,current_code, new_base_code):
        return self.entry_rows.change_citation_code(current_code, new_base_code)
    
    def get_codes_that_cite_code(self, code):
        return self.entry_rows.get_codes_that_cite_code(code)
    
    def get_codes_cited_by_code(self, code):
        return self.entry_rows.get_codes_cited_by_code(code)
