from aux import logger, md_dir_name, \
    array_separator, concat_separator, \
    link_cited, delete_unmatched_citations, automate_pdf_link_doi, automate_pdf_link_isbn, included_properties, user_defined_properties, \
    read_encoding, write_encoding, \
    has_data, make_md_link
from os import remove, listdir, rename
from os.path import join, basename, exists


class _FileCollection:
    def __init__(self, dir_name):
        self.dir_name = dir_name
        self.edited_md_files = {"created": [], "code_changed": [], "updated_or_deleted": {}}
        if self.dir_name is not None:
            self.current_md_files = [path for path in listdir(self.dir_name) if path.endswith(".md")]
    
    def record_created(self, file_path):
        self.edited_md_files["created"].append(file_path)
        self.current_md_files.append(basename(file_path))
    
    def record_code_changed(self, new_file_path, old_file_path, old_content):
        self.edited_md_files["code_changed"].append([new_file_path, old_file_path, old_content])
        self.current_md_files[self.current_md_files.index(basename(old_file_path))] = basename(new_file_path)
    
    def record_updated(self, file_path, file_content, check_created=False):
        if check_created and file_path in self.edited_md_files["created"]:
            return
        if file_path not in self.edited_md_files["updated_or_deleted"]:
            self.edited_md_files["updated_or_deleted"][file_path] = file_content
    
    def record_deleted(self, file_path, file_content):
        self.record_updated(file_path, file_content)
        self.current_md_files.pop(self.current_md_files.index(basename(file_path)))
    
    def get_created_files(self):
        return self.edited_md_files["created"]

    def get_code_change_files(self):
        return self.edited_md_files["code_changed"]
    
    def get_updated_or_deleted_files(self):
        return self.edited_md_files["updated_or_deleted"]
    
    def get_current_md_file_paths(self):
        return self.current_md_files

class Markdowns:
    dir_name = md_dir_name
    yaml_separator = "---\n"
    indent = " " * 2
    current_md_files = None

    def __init__(self):
        logger.debug("Getting all markdown file names for Markdowns class")
        self.file_collection = _FileCollection(self.dir_name)

    def create_file(self, citation_dict, cited_links_lst=None):
        if self.dir_name is None:
            return
        code = citation_dict["citation-code"]
        file_path = self._get_file_path(code)
        self.file_collection.record_created(file_path)
        with open(file_path, "w", encoding=write_encoding) as f:
            f.write(self.yaml_separator + self._get_yaml_frontmatter(citation_dict, cited_links_lst) + self.yaml_separator)
        logger.progress(f"Created markdown file {code}.md")

    def delete_unmatched_files(self, citation_codes_lst):
        if self.dir_name is None or not delete_unmatched_citations:
            return
        for file in self.file_collection.get_current_md_file_paths():
            code = file[:-3] # remove .md
            if code not in citation_codes_lst:
                file_path = self._get_file_path(code)
                with open(file_path, "r", encoding=read_encoding) as f:
                    self.file_collection.record_deleted(file_path, f.read())
                logger.progress(f"Deleting markdown file {file_path.rsplit('/',1)[1]} since it is missing from the citations csv")
                remove(file_path)

    def update_file(self, citation_dict, cited_links_lst=None):
        if self.dir_name is None:
            return
        code = citation_dict["citation-code"]
        file_path = self._get_file_path(code)
        new_yaml_frontmatter = self._get_yaml_frontmatter(citation_dict, cited_links_lst)
        if exists(file_path):
            with open(file_path, "r", encoding=read_encoding) as f:
                file_content = f.read()
            content_lst = file_content.split(self.yaml_separator)
            if content_lst[1] == new_yaml_frontmatter:
                logger.debug(f"No changes detected in yaml frontmatter of {code} .md, no update made")
                return
            self.file_collection.record_updated(file_path, file_content)
        else:
            content_lst = [""] * 3
            self.file_collection.record_created(file_path)
        content_lst[1] = new_yaml_frontmatter
        with open(file_path, "w", encoding=write_encoding) as f:
            f.write(self.yaml_separator.join(content_lst))
        logger.progress(f"Updated markdown file {code}.md")

    def change_citation_code(self, old_code, new_code, cited_by_lst):
        if self.dir_name is None:
            return
        old_file_path, new_file_path = [self._get_file_path(code) for code in (old_code, new_code)]
        # rename file
        rename(old_file_path, new_file_path)
        logger.progress(f"File {old_code}.md changed to {new_code}.md, and contents updated if necessary")
        # collect old content
        with open(new_file_path, "r", encoding=read_encoding) as f:
            old_content = f.read()
            self.file_collection.record_code_changed(new_file_path, old_file_path, old_content)
        # update pdf link in yaml frontmatter if necessary
        if (automate_pdf_link_doi or automate_pdf_link_isbn) and make_md_link(old_code, pdf=True) in old_content:
            with open(new_file_path, "w", encoding=write_encoding) as f:
                new_content = old_content.replace(make_md_link(old_code, pdf=True), make_md_link(new_code, pdf=True))
                f.write(new_content)
        # update md docs that cite this citation code
        if link_cited and cited_by_lst is not None:
            for code in cited_by_lst:
                file_path = self._get_file_path(code)
                with open(file_path, "r", encoding=read_encoding) as f:
                    old_content = f.read()
                self.file_collection.record_updated(file_path, old_content, check_created=True)
                new_content = old_content.replace(make_md_link(old_code), make_md_link(new_code))
                with open(file_path, "w", encoding=write_encoding) as f:
                    f.write(new_content)
                logger.progress(f"File {code}.md changed so that its citation to {old_code} was exchanged for {new_code}")
    
    def revert_files(self):
        print(self.file_collection.edited_md_files)
        for file_path in self.file_collection.get_created_files():
            remove(file_path)
        for new_file_path, old_file_path, old_content in self.file_collection.get_code_change_files():
            remove(new_file_path)
            with open(old_file_path, "w", encoding=write_encoding) as f:
                f.write(old_content)
        for file_path, content in self.file_collection.get_updated_or_deleted_files().items():
            with open(old_file_path, "w", encoding=write_encoding) as f:
                f.write(content)

    def _get_yaml_frontmatter(self, citation_dict, cited_links_lst=None):
        yaml_text = ""
        get_detail = lambda key, string=None, whitespace=" ": f"{key}:{whitespace}{citation_dict[key] if string is None else string}\n"
        make_lst = lambda lst: self.indent + "- " + ("\n" + self.indent + "- ").join(lst)
        # add properties from citation_dict
        for prop in included_properties:
            if has_data(citation_dict[prop]):
                value = str(citation_dict[prop])
                if prop == "author":
                    value = make_lst([name.replace(concat_separator, ", ") for name in value.split(array_separator)])
                    yaml_text += get_detail(prop, value, whitespace="\n")
                    continue
                elif prop == "add-date":
                    yaml_text += get_detail(prop, value)
                elif ":" in value:
                    value = "\"" + value + "\""
                yaml_text += get_detail(prop, value)
        # add link to pdf
        if (automate_pdf_link_doi and has_data(citation_dict["doi"])) or \
            (automate_pdf_link_isbn and has_data(citation_dict["isbn"])):
            yaml_text += get_detail("pdf-link", make_md_link(citation_dict['citation-code'], pdf=True))
        # add user-defined properties
        for prop, value in user_defined_properties.items():
            if isinstance(value, bool):
                value = str(value).lower()
                yaml_text += get_detail(prop, value)
            elif isinstance(value, list):
                value = make_lst(value)
                yaml_text += get_detail(prop, value, whitespace="\n")
            else:
                value = str(value)
                if ":" in value:
                    value = "\"" + value + "\""
                yaml_text += get_detail(prop, value)
        # add links to cited documents
        if link_cited and cited_links_lst is not None and len(cited_links_lst) > 0:
            yaml_text += get_detail("citations", make_lst((make_md_link(code) for code in cited_links_lst)), whitespace="\n")
        return yaml_text

    def _get_file_path(self, citation_code):
        return join(self.dir_name, citation_code + ".md")
