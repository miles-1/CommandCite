from aux import logger, settings, md_dir_name
from os import remove, listdir, rename
from os.path import join

try:
    logger.debug("Beginning to load settings from settings.json for biblography_files.py")
    # citations csv settings
    logger.debug("Loading citations csv settings from settings.json")
    missing_data_string = settings["citations_csv"]["missing_data_string"]
    array_separator = settings["citations_csv"]["array_separator"]
    concat_separator = settings["citations_csv"]["concat_separator"]
    # md settings
    logger.debug("Loading markdown settings from settings.json")
    link_cited = settings["markdown"]["link_cited"]
    delete_unmatched_citations = settings["markdown"]["delete_unmatched_citations"]
    automate_pdf_link_doi = settings["markdown"]["automate_pdf_link"]["doi"]
    automate_pdf_link_isbn = settings["markdown"]["automate_pdf_link"]["isbn"]
    included_properties = settings["markdown"]["included_properties"]
    user_defined_properties = settings["markdown"]["user-defined_properties"]
    # advanced settings
    logger.debug("Loading advanced settings from settings.json")
    info_headers = settings["advanced"]["csv_headers"]["info_headers"]
    read_encoding = settings["advanced"]["file_encoding"]["read_encoding"]
    write_encoding = settings["advanced"]["file_encoding"]["write_encoding"]
    delete_unmatched_entries = settings["bibliography"]["delete_unmatched_entries"]
    logger.debug("Finished loading settings from settings.json for biblography_files.py")
except KeyError as e:
    logger.error(e, "settings.json file is missing required keys")

class Markdowns:
    dir_name = md_dir_name
    yaml_separator = "---\n"
    indent = " " * 2

    def __init__(self):
        logger.debug("Getting all markdown file names for Markdowns class")
        self.current_md_files = [path for path in listdir(self.dir_name) if path.endswith(".md")]

    def create_file(self, citation_dict):
        if self.dir_name is None:
            return
        code = citation_dict["citation-code"]
        path = self._get_file_path(code)
        with open(path, "w", encoding=write_encoding) as f:
            f.write(self.yaml_separator + self._get_header_yaml(citation_dict) + self.yaml_separator)

    def delete_unmatched_files(self, citation_codes_lst):
        if self.dir_name is None or not delete_unmatched_citations:
            return
        for file in self.current_md_files:
            code = file[:-3]
            if code not in citation_codes_lst:
                remove(self._get_file_path(code))

    def update_file(self, citation_dict):
        if self.dir_name is None:
            return
        code = citation_dict["citation-code"]
        path = self._get_file_path(code)
        with open(path, "r", encoding=read_encoding) as f:
            content_lst = f.read().split(self.yaml_separator)
        content_lst[1] = self._get_header_yaml(citation_dict)
        with open(path, "w", encoding=write_encoding) as f:
            f.write(self.yaml_separator.join(content_lst))

    def change_citation_code(self, current_code, new_code, citing_codes):
        if self.dir_name is None:
            return
        old_name, new_name = [self._get_file_path(code) for code in (current_code, new_code)]
        rename(old_name, new_name)
        if automate_pdf_link_doi or automate_pdf_link_isbn:
            with open(new_name, "r", encoding=read_encoding) as f:
                content = f.read().replace(current_code + ".pdf", new_code + ".pdf")
            with open(new_name, "w", encoding=write_encoding) as f:
                f.write(content)
        if link_cited:
            for code in citing_codes:
                file_name = self._get_file_path(code)
                with open(file_name, "r", encoding=read_encoding) as f:
                    content = f.read().replace(f"\"[[{current_code}]]\"", f"\"[[{new_code}]]\"")
                with open(file_name, "w", encoding=write_encoding) as f:
                    f.write(content)
    
    def _get_header_yaml(self, citation_dict, cited_links_lst=None):
        yaml_text = ""
        get_detail = lambda key, string=None: f"{key}: {citation_dict[key] if string is None else string}\n"
        make_lst = lambda lst: "\n" + self.indent + "- " + ("\n" + self.indent + "- ").join(lst) + "\n"
        # add properties from citation_dict
        for prop in included_properties:
            if citation_dict[prop] not in ("", missing_data_string):
                value = citation_dict[prop]
                if prop == "title":
                    value = "\"" + value + "\""
                elif prop == "author":
                    value = make_lst([name.replace(concat_separator, ", ") for name in value.split(array_separator)])
                yaml_text += get_detail(prop, value)
        # add link to pdf
        if (automate_pdf_link_doi and citation_dict["doi"] not in ("", missing_data_string)) or \
            (automate_pdf_link_isbn and citation_dict["isbn"] not in ("", missing_data_string)):
            yaml_text += get_detail("pdf-link", f"\"[[{citation_dict['citation-code'] + ".pdf"}]]\"")
        # add user-defined properties
        for prop, value in user_defined_properties.items():
            if isinstance(value, bool):
                value = str(value).lower()
            elif isinstance(value, list):
                value = make_lst(value)
            yaml_text += get_detail(prop, value)
        # add links to cited documents
        if cited_links_lst is not None and link_cited:
            yaml_text += get_detail("citations", make_lst((f"\"[[{code}]]\"" for code in cited_links_lst)))
        pass

    def _get_file_path(self, citation_code):
        return join(self.dir_name, citation_code + ".md")