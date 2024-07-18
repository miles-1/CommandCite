from crossref.restful import Works, Etiquette
from time import sleep
from aux import logger, program_headers, get_data_by_address, \
    format_title, format_isbn, format_names, format_base_citation_code, replace_special_characters, \
    openlibrary_url, googlebooks_url, \
    missing_data_string, array_separator, concat_separator, citation_code_format, header_addresses, \
    timeout, num_retries, retry_delay, \
    project_name, project_version, project_url, contact_email, \
    primary_isbn, secondary_isbn
import requests
import re
from datetime import datetime

### api classes
class _GenWorks:
    citation_dict = None
    etiquette = None

    def __init__(self, url=None):
        self.api_class_name = self.__class__.__name__
        self.api_name = self.api_class_name.replace("Works", "").lower()
        self.api_header_addresses = header_addresses[self.api_name]
        self.api_header_address_root = (self.api_header_addresses.pop("/") + ".") if "/" in self.api_header_addresses else ""
        self.url = url
        if self.api_name == "crossref":
            self.id_num_type = "doi"
        elif self.api_name in ("openlibrary", "googlebooks"):
            self.id_num_type = "isbn"

    def _request(self, id_num):
        logger.error("Not Implimented Error", f"Should not call private method _request() from base class {self.api_name}")

    def get_csv_row(self, id_num, custom_base_citation_code=None):
        logger.debug(f"Calling {self.api_name} api for {self.id_num_type} \"{id_num}\"")
        id_num = self._format_id_num(id_num)
        response = self.get_work(id_num)
        self.citation_dict = None
        if response is None:
            return None
        else:
            # make framework dict
            logger.debug(f"{self.api_class_name}: creating csv row for {self.id_num_type} \"{id_num}\"")
            if any(header not in header_addresses["info_headers"] for header in self.api_header_addresses):
                logger.error("Bad Header", f"{self.api_class_name}: in settings.json, headers exist for {self.api_name} that are absent in \"info_headers\".")
            self.citation_dict = {header: missing_data_string for header in header_addresses["info_headers"] + program_headers}
            logger.debug(f"{self.api_class_name}: adding content for \"add-date\" and \"{self.id_num_type}\" fields for {self.id_num_type} \"{id_num}\"")
            self.citation_dict["add-date"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
            self.citation_dict[self.id_num_type] = id_num
            # add in header items
            logger.debug(f"{self.api_class_name}: filling in data for other fields from response for {self.id_num_type} \"{id_num}\"")
            for header, address in self.api_header_addresses.items():
                address = self.api_header_address_root + address
                needs_processing, data = get_data_by_address(response, address)
                self.citation_dict[header] = self._process_data(header, data) if needs_processing else data
            # set code
            logger.debug(f"Creating citation code base for {self.id_num_type} \"{id_num}\"")
            self._set_base_citation_code(custom_base_citation_code)
            # return completed dict
            return self.citation_dict
    
    def _format_id_num(self, id_num):
        match self.id_num_type:
            case "isbn":
                return format_isbn(id_num)
            case "doi":
                return id_num.strip() 

    def _process_data(self, header, data):
        logger.error("Unhandled Header", f"The @ symbol was used in the address for {header} but not handled by {self.api_class_name}._process_data")

    def _set_base_citation_code(self, custom_citation_code=None):
        if isinstance(custom_citation_code, str):
            final_string = format_base_citation_code(custom_citation_code)
        else:
            matches = [(match.group(1), match.span()) for match in re.finditer(r"<([a-z\-]*?.?[a-z]*?)>", citation_code_format)]
            first_author_name = self.citation_dict["author"].split(array_separator, 1)[0]
            if first_author_name is missing_data_string:
                first_author_family_name, first_author_given_name = (missing_data_string,) * 2
            elif first_author_name.count(concat_separator) == 0:
                first_author_family_name, first_author_given_name = first_author_name, missing_data_string
            else:
                first_author_family_name, first_author_given_name = first_author_name.split(concat_separator, 1)
            special_keys = {
                "firstauthor.family": first_author_family_name,
                "firstauthor.given": first_author_given_name
            }
            bad_keys = [match[0] for match in matches if match[0] not in self.citation_dict and match[0] not in special_keys]
            if len(bad_keys) > 0:
                logger.error("Bad citation code format", f"cannot interpret <{bad_keys[0]}> in \"citation-code_format\" in settings.json")
            all_indx_cutoffs = [0] + [indx for match in matches for indx in match[1]] + [len(citation_code_format)]
            non_match_indx_ranges = list(zip(all_indx_cutoffs[::2], all_indx_cutoffs[1::2]))
            final_string = ""
            for non_match_indx_range, (group, _) in zip(non_match_indx_ranges[:-1], matches):
                final_string += citation_code_format[slice(*non_match_indx_range)] 
                final_string += str(self.citation_dict[group]) if group in self.citation_dict else special_keys[group]
            final_string += citation_code_format[slice(*non_match_indx_ranges[-1])]
            final_string = format_base_citation_code(final_string)
        self.citation_dict["citation-code"] = final_string
        logger.debug(f"Created citation code base: \"{final_string}\"")

    def get_work(self, id_num):
        id_num = id_num.rstrip()
        if id_num == "":
            logger.debug(f"{self.api_class_name}: {self.id_num_type} provided is empty. Skipping")
            return None
        for i in range(num_retries):
            logger.debug(f"{self.api_class_name}: Attempt {i+1} to retrieve {self.id_num_type} \"{id_num}\"")
            try:
                response = self._request(id_num)
                if response is None:
                    logger.progress(f"{self.api_class_name}: Received \"None\" response for {self.id_num_type} \"{id_num}\". Skipping")
                else:
                    logger.progress(f"{self.api_class_name}: Successfully retrieved data {self.id_num_type} \"{id_num}\"")
                return response
            except requests.exceptions.Timeout:
                if i == num_retries - 1:
                    logger.progress(f"{self.api_class_name}: Timeout while retrieving {self.id_num_type} \"{id_num}\". No more retries left. Moving on")
                    return None
                logger.debug(f"{self.api_class_name}: Timeout while retrieving {self.id_num_type} \"{id_num}\". Sleeping for {retry_delay} seconds")
                sleep(retry_delay)
            except Exception as e:
                logger.error(e, f"{self.api_class_name}: Exception while retrieving {self.id_num_type} \"{id_num}\"")

class CrossRefWorks(_GenWorks):
    def __init__(self):
        super().__init__()
        if all(x is not None for x in [project_name, project_version, project_url, contact_email]):
            logger.debug(f"{self.api_class_name}: polite api settings found in settings.json, using them for etiquette")
            self.etiquette = Etiquette(project_name, project_version, project_url, contact_email)
        else:
            logger.debug(f"{self.api_class_name}: polite api settings not found in settings.json, using default api")
        self.works = Works(timeout=timeout, etiquette=self.etiquette)
    
    def _request(self, id_num):
        return self.works.doi(id_num)
    
    def _process_data(self, header, data):
        # crossref types: https://crossref.gitlab.io/knowledge_base/docs/topics/content-types/
        match header:
            case "title":
                return format_title(data)  
            case "day":
                return data[2] if len(data) == 3 else missing_data_string
            case "abstract":
                return replace_special_characters(data)
            case "type":
                return "article" if data == "journal-article" else data
        super()._process_data(header, data)
                
class _ISBNWorks(_GenWorks):
    def __init__(self, url):
        super().__init__()
        self.url = url
        if all(x is not None for x in [project_name, project_version, project_url, contact_email]):
            logger.debug(f"{self.api_class_name}: polite api settings found in settings.json, sharing with api as headers")
            self.ettiquette = {
                "User-Agent": f"{project_name}/{project_version} ({project_url}; mailto:{contact_email})",
                "Accept": "application/json"
            }
        else:
            logger.debug(f"{self.api_class_name}: polite api settings not found in settings.json, using api anonymously")
    
    def _request(self, id_num):
        response = requests.get(self.url + id_num, timeout=timeout, headers=self.ettiquette)
        if response.status_code == 200:
            return self._validate(response.json())
        logger.debug(f"{self.api_class_name}: HTTP error {response.status_code} while retrieving {self.id_num_type} \"{id_num}\"")
        return None
    
    def _validate(self, response):
        logger.error("Not Implimented Error", f"Should not call private method _validate() from base class {self.api_name}")

class OpenLibraryWorks(_ISBNWorks):
    def __init__(self):
        super().__init__(openlibrary_url)
    
    def _validate(self, response):
        if not "numFound" in response or response["numFound"] != 1:
            return None
        return response
    
    def _process_data(self, header, data):
        match header:
            case "title":
                return format_title(data)  
            case "author":
                return format_names(data)
            case "year" | "month" | "day":
                if header == "year" and isinstance(data, int):
                    return data
                return getattr(datetime.strptime(data, "%b %d, %Y"), header)
            case "type":
                if data == "work":
                    return "book"
                return data
        super()._process_data(header, data)

class GoogleBooksWorks(_ISBNWorks):
    def __init__(self):
        super().__init__(googlebooks_url)
    
    def _validate(self, response):
        if "totalItems" not in response or response["totalItems"] != 1:
            return None
        return response
    
    def _process_data(self, header, data):
        match header:
            case "title":
                return format_title(data.replace(concat_separator, ": "))
            case "author":
                return format_names(data)
            case "year" | "month" | "day":
                date_format = ("year", "month", "day")
                date_lst = [int(num) for num in data.split("-")]
                date_lst_indx = date_format.index(header) + 1
                if len(date_lst) > date_lst_indx:
                    return date_lst[date_lst_indx]
                return missing_data_string
            case "type":
                if data == "books#volume":
                    return "book"
                return data
        super()._process_data(header, data)
       
### wrapper class

class CiteWorks:
    doi_api, isbn_api1, isbn_api2 = (None,) * 3

    def get_csv_row(self, id_num, id_num_type, custom_base_code=None):
        citation_dict = None
        if id_num_type == "doi":
            self._init_doi_api()
            citation_dict = self.doi_api.get_csv_row(id_num, custom_base_citation_code=custom_base_code)
        elif id_num_type == "isbn":
            self._init_isbn_api()
            citation_dict = self.isbn_api1.get_csv_row(id_num, custom_base_citation_code=custom_base_code)
            if citation_dict is None and self.isbn_api2 is not None:
                citation_dict = self.isbn_api2.get_csv_row(id_num, custom_base_citation_code=custom_base_code)
        return citation_dict
    
    def _init_doi_api(self):
        if self.doi_api == None:
            self.doi_api = CrossRefWorks()

    def _init_isbn_api(self):
        # primary
        if primary_isbn == "openlibrary":
            if self.isbn_api1 is None:
                self.isbn_api1 = OpenLibraryWorks()
        elif primary_isbn == "googlebooks":
            if self.isbn_api1 is None:
                self.isbn_api1 = GoogleBooksWorks()
        else:
            logger.error("Invalid Primary isbn api", f"The primary isbn api provided must be \"openlibrary\" or \"googlebooks\", but found {primary_isbn}")
        # secondary
        if secondary_isbn == "openlibrary" and secondary_isbn != primary_isbn:
            if self.isbn_api2 is None:
                self.isbn_api2 = OpenLibraryWorks()
        elif secondary_isbn == "googlebooks" and secondary_isbn != primary_isbn:
            if self.isbn_api2 is None:
                self.isbn_api2 = GoogleBooksWorks()
        elif secondary_isbn is not None:
            logger.error("Invalid Secondary isbn api", f"The secondary isbn api provided must be \"openlibrary\", \"googlebooks\", or \"null\", and cannot be a repeat of the primary, but found {primary_isbn}")