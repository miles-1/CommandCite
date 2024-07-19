from aux import logger, hayagriva_file_name, bibtex_file_name, \
    array_separator, concat_separator, \
    read_encoding, write_encoding, \
    has_data
import re
from os.path import exists


class _Bibliography:
    delim = "\n\n"
    file_name = None
    indent = " " * 2

    def __init__(self):
        self.entry_dict, self.backup_entry_dict = {}, {}
        self.citation_class = self.__class__.__name__
        self.citation_file_type = self.citation_class[:-3].lower()
        if self.citation_file_type == "hayagriva":
            self.file_name = hayagriva_file_name
        elif self.citation_file_type == "bibtex":
            self.file_name = bibtex_file_name
        if self.file_name is not None and exists(self.file_name):
            logger.debug(f"Reading contents of {self.citation_file_type} file")
            pattern = r"@[a-z]+?{(.+?),\n" if self.citation_file_type == "bibtex" else r"(.+?):\n"
            get_code = lambda entry: re.search(pattern, entry).group(1)
            with open(self.file_name, "r", encoding=read_encoding) as f:
                file_contents = f.read()
            if file_contents.strip() != "":
                self.entry_dict = {get_code(entry): entry for entry in file_contents.split(self.delim)}
                self.backup_entry_dict = self.entry_dict.copy()
    
    def create_or_update_citation(self, citation_dict):
        if self.file_name is None:
            return
        code = citation_dict["citation-code"]
        self.entry_dict[code] = self._get_entry_text(citation_dict)
        logger.progress(f"Added {code} to {self.citation_file_type} file")

    def delete_unmatched_citations(self, citation_code_lst):
        if self.file_name is None:
            return
        pop_codes = []
        for code in self.entry_dict:
            if code not in citation_code_lst:
                logger.progress(f"Deleting {self.citation_file_type} entry {code} since it is missing from the citations csv")
                pop_codes.append(code)
        for code in pop_codes:
            self.entry_dict.pop(code)

    def change_citation_code(self, current_code, new_code):
        if self.file_name is None:
            return
        code_func = (lambda code: f"{code}:\n  ") if self.citation_file_type == "hayagriva" else (lambda code: "{" + f"{code},\n")
        self.entry_dict[new_code] = self.entry_dict[current_code].replace(code_func(current_code), code_func(new_code))
        self.entry_dict.pop(current_code)
        logger.progress(f"Changed {current_code} to {new_code} in {self.citation_file_type} file")

    def save_file(self, revert_to_old=False):
        if self.file_name is None:
            return
        current_entries = (self.backup_entry_dict if revert_to_old else self.entry_dict)
        if len(current_entries) > 0:
            with open(self.file_name, "w", encoding=write_encoding) as f:
                logger.debug(f"Writing {self.citation_file_type} file")
                file_contents = self.delim.join(current_entries.values())
                f.write(file_contents)

    def _get_entry_text(self, citation_dict):
        logger.error("Not Implemented Error", f"The class {self.citation_class} does not have an implementation of the method _get_entry_text")

class HayagrivaBib(_Bibliography):
    def _get_entry_text(self, citation_dict):
        entry_text = citation_dict["citation-code"] + ":\n"
        exists = lambda key: has_data(citation_dict[key])
        get_detail = lambda key, string=None, num=1: f"{self.indent * num}{key}:{' ' if string != '' else ''}{citation_dict[key] if string is None else string}\n"
        # citation type
        entry_text += get_detail("type", citation_dict["type"].title())
        # title
        if exists("title"):
            entry_text += get_detail("title", "\"" + citation_dict["title"] + "\"")
        # author
        if exists("author"):
            author_string = str([name.replace(concat_separator, ", ") for name in citation_dict["author"].split(array_separator)])
            entry_text += get_detail("author", author_string)
        # year, month, day
        if exists("year"):
            date_string = str(citation_dict["year"])
            if exists("month"):
                date_string += "-" + str(citation_dict["month"])
                if exists("day"):
                    date_string += "-" + str(citation_dict["day"])
            entry_text += get_detail("date", date_string)
        # page
        if exists("page"):
            entry_text += get_detail("page-range", citation_dict["page"])
        # publisher
        if exists("publisher"):
            entry_text += get_detail("publisher")
        # doi, isbn
        if exists("doi") or exists("isbn"):
            entry_text += get_detail("serial-number", "")
            entry_text += get_detail("doi" if exists("doi") else "isbn", num=2)
        # journal, abbreviated-journal, volume, issue
        if exists("journal") or exists("volume") or exists("issue"):
            entry_text += get_detail("parent", "")
            if exists("journal"):
                entry_text += get_detail("title", "", num=2)
                entry_text += get_detail("value", "\"{" + citation_dict["journal"] + "}\"", num=3)
                if exists("abbreviated-journal") and citation_dict["abbreviated-journal"] != citation_dict["journal"]:
                    entry_text += get_detail("short", "\"{" + citation_dict["abbreviated-journal"] + "}\"", num=3)
            if exists("volume"):
                entry_text += get_detail("volume", num=2)
            if exists("issue"):
                entry_text += get_detail("issue", num=2)
        return entry_text

class BibtexBib(_Bibliography):
    def _get_entry_text(self, citation_dict):
        entry_text = ""
        citation_type = citation_dict["type"]
        exists = lambda key: has_data(citation_dict[key])
        get_detail = lambda key, string=None: f"{self.indent}{key} = {{{citation_dict[key] if string is None else string}}},\n"
        # citation type
        if citation_type not in ("book", "article"):
            citation_type = "misc"
        entry_text += "@" + citation_type + "{" + citation_dict["citation-code"] + ",\n"
        # author
        if exists("author"):
            author_string = citation_dict["author"].replace(array_separator, " and ").replace(concat_separator, ", ")
            entry_text += get_detail("author", author_string)
        # title
        if exists("title"):
            entry_text += get_detail("title")
        # year, month, day
        if exists("year"):
            date_string = str(citation_dict["year"])
            if exists("month"):
                date_string = date_string + "-" + str(citation_dict["month"])
                if exists("day"):
                    date_string = date_string + "-" + str(citation_dict["day"])
            date_string = "{" + date_string + "}"
            entry_text += get_detail("date", date_string)
        # journal and abbreviated-journal
        if exists("journal"):
            journal_string = citation_dict["journal"]
            if exists("abbreviated-journal"):
                journal_string = citation_dict["abbreviated-journal"]
            entry_text += get_detail("journal", journal_string)
        # publisher
        if exists("publisher"):
            entry_text += get_detail("publisher")
        # page
        if exists("page"):
            entry_text += get_detail("pages", citation_dict["page"])
        # volume
        if exists("volume"):
            entry_text += get_detail("volume")
        # issue
        if exists("issue"):
            entry_text += get_detail("number", citation_dict["issue"])
        # doi
        if exists("doi"):
            entry_text += get_detail("doi")
        # isbn
        if exists("isbn"):
            entry_text += get_detail("isbn")
        entry_text += "}"
        return entry_text