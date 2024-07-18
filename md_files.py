from aux import logger, md_dir_name, \
    array_separator, concat_separator, \
    link_cited, delete_unmatched_citations, automate_pdf_link_doi, automate_pdf_link_isbn, included_properties, user_defined_properties, \
    read_encoding, write_encoding, \
    has_data, make_md_link
from os import remove, listdir, rename
from os.path import join


class Markdowns:
    dir_name = md_dir_name
    yaml_separator = "---\n"
    indent = " " * 2
    current_md_files = None

    def __init__(self):
        self.edited_md_files = {"created": [], "code_changed": [], "updated_or_deleted": {}}
        logger.debug("Getting all markdown file names for Markdowns class")
        if self.dir_name is not None:
            self.current_md_files = [path for path in listdir(self.dir_name) if path.endswith(".md")]

    def create_file(self, citation_dict):
        if self.dir_name is None:
            return
        code = citation_dict["citation-code"]
        path = self._get_file_path(code)
        self.edited_md_files["created"].append(path)
        with open(path, "w", encoding=write_encoding) as f:
            f.write(self.yaml_separator + self._get_yaml_frontmatter(citation_dict) + self.yaml_separator)

    def delete_unmatched_files(self, citation_codes_lst):
        if self.dir_name is None or not delete_unmatched_citations:
            return
        for file in self.current_md_files:
            code = file[:-3] # remove .md
            if code not in citation_codes_lst:
                file_path = self._get_file_path(code)
                with open(file_path, "r", encoding=read_encoding) as f:
                    self.edited_md_files["updated_or_deleted"][file_path] = f.read()
                logger.progress(f"Deleting markdown file {file_path.rsplit('/',1)[1]} since it is missing from the citations csv")
                remove(file_path)

    def update_file(self, citation_dict):
        if self.dir_name is None:
            return
        code = citation_dict["citation-code"]
        file_path = self._get_file_path(code)
        with open(file_path, "r", encoding=read_encoding) as f:
            file_content = f.read()
        self.edited_md_files["updated_or_deleted"][file_path] = file_content
        content_lst = file_content.split(self.yaml_separator)
        content_lst[1] = self._get_yaml_frontmatter(citation_dict)
        with open(file_path, "w", encoding=write_encoding) as f:
            f.write(self.yaml_separator.join(content_lst))

    def change_citation_code(self, old_code, new_code, cited_by_lst):
        if self.dir_name is None:
            return
        old_file_path, new_file_path = [self._get_file_path(code) for code in (old_code, new_code)]
        # rename file
        rename(old_file_path, new_file_path)
        # collect old content
        with open(new_file_path, "r", encoding=read_encoding) as f:
            old_content = f.read()
            self.edited_md_files["code_changed"].append([new_file_path, old_file_path, old_content])
        # update pdf link in yaml frontmatter if necessary
        if (automate_pdf_link_doi or automate_pdf_link_isbn) and make_md_link(old_code, pdf=True) in old_content:
            with open(new_file_path, "w", encoding=write_encoding) as f:
                new_content = old_content.replace(make_md_link(old_code, pdf=True), make_md_link(new_code, pdf=True))
                f.write(new_content)
        # update md docs that cite this citation code
        if link_cited:
            for code in cited_by_lst:
                file_path = self._get_file_path(code)
                with open(file_path, "r", encoding=read_encoding) as f:
                    old_content = f.read()
                if file_path not in self.edited_md_files["updated_or_deleted"] and file_path not in self.edited_md_files["created"]:
                    self.edited_md_files["updated_or_deleted"][file_path] = old_content
                new_content = old_content.replace(make_md_link(old_code), make_md_link(new_code))
                with open(file_path, "w", encoding=write_encoding) as f:
                    f.write(new_content)
    
    def revert_files(self):
        for file_path in self.edited_md_files["created"]:
            remove(file_path)
        for new_file_path, old_file_path, old_content in self.edited_md_files["code_changed"]:
            remove(new_file_path)
            with open(old_file_path, "w", encoding=write_encoding) as f:
                f.write(old_content)
        for file_path, content in self.edited_md_files["updated_or_deleted"].items():
            with open(old_file_path, "w", encoding=write_encoding) as f:
                f.write(content)

    def _get_yaml_frontmatter(self, citation_dict, cited_links_lst=None):
        yaml_text = ""
        get_detail = lambda key, string=None: f"{key}: {citation_dict[key] if string is None else string}\n"
        make_lst = lambda lst: "\n" + self.indent + "- " + ("\n" + self.indent + "- ").join(lst)
        # add properties from citation_dict
        for prop in included_properties:
            if has_data(citation_dict[prop]):
                value = citation_dict[prop]
                if prop == "title":
                    value = "\"" + value + "\""
                elif prop == "author":
                    value = make_lst([name.replace(concat_separator, ", ") for name in value.split(array_separator)])
                yaml_text += get_detail(prop, value)
        # add link to pdf
        if (automate_pdf_link_doi and has_data(citation_dict["doi"])) or \
            (automate_pdf_link_isbn and has_data(citation_dict["isbn"])):
            yaml_text += get_detail("pdf-link", make_md_link(citation_dict['citation-code'], pdf=True))
        # add user-defined properties
        for prop, value in user_defined_properties.items():
            if isinstance(value, bool):
                value = str(value).lower()
            elif isinstance(value, list):
                value = make_lst(value)
            yaml_text += get_detail(prop, value)
        # add links to cited documents
        if cited_links_lst is not None and link_cited:
            yaml_text += get_detail("citations", make_lst((make_md_link(code) for code in cited_links_lst)))
        return yaml_text

    def _get_file_path(self, citation_code):
        return join(self.dir_name, citation_code + ".md")
