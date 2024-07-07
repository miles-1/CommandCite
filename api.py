from crossref.restful import Works, Etiquette
from time import sleep
from aux import settings, logger, get_data_by_address
import requests
import re
from datetime import datetime


### collect settings from settings.json
try:
    logger.debug("Beginning to load settings from settings.json for api.py")
    
    logger.debug("Loading network settings from settings.json")
    timeout = settings["network"]["timeout"]
    num_retries = settings["network"]["num_retries"]
    retry_delay = settings["network"]["retry_delay"]
    
    logger.debug("Loading polite api settings from settings.json")
    project_name = settings["polite_api"]["project_name"]
    project_version = settings["polite_api"]["project_version"]
    project_url = settings["polite_api"]["project_url"]
    contact_email = settings["polite_api"]["contact_email"]
    
    logger.debug("Loading ISBN api urls from settings.json")
    openlibrary_url = settings["advanced"]["api"]["openlibrary"]["url"]
    googlebooks_url = settings["advanced"]["api"]["googlebooks"]["url"]
    
    logger.debug("Loading settings for citations csv file from settings.json")
    missing_data_string = settings["citations_csv"]["missing_data_string"]
    array_separator = settings["citations_csv"]["array_separator"]
    first_last_separator = settings["citations_csv"]["first_last_separator"]
    title_case_titles = settings["citations_csv"]["title_case_titles"]
    citation_code_format = settings["citations_csv"]["citation-code_format"]
    
    logger.debug("Loading api response data paths from settings.json")
    header_addresses = settings["advanced"]["csv_headers"]
    if any(x not in header_addresses for x in ["info_headers", "crossref", "openlibrary", "googlebooks"]):
        logger.error("settings.json file is missing required keys in advanced.csv_headers")
    logger.debug("Finished loading settings from settings.json for api.py")
except KeyError as e:
    logger.error(e, "settings.json file is missing required keys")

### api classes
class _GenWorks:
    def __init__(self, url=None):
        self.api_class_name = self.__class__.__name__
        self.api_name = self.api_class_name.replace("Works", "").lower()
        self.api_header_addresses = header_addresses[self.api_name]
        self.api_header_address_root = self.api_header_addresses.pop("/") if "/" in self.api_header_addresses else ""
        self.url = url
        self.citation_dict = None

    def _request(self, code, code_type):
        logger.error("Not Implimented Error", f"Should not call private method _request() from base class {self.api_name}")

    def get_csv_row(self, response, make_md=True, make_bib=True):
        logger.debug(f"{self.api_class_name}: creating csv row for data")
        # make framework dict
        program_headers = ["citation-code", "make-md", "make-bib", "add-date"]
        if any(header not in header_addresses["info_headers"] for header in self.api_header_addresses):
            logger.error("Bad Header", f"{self.api_class_name}: in settings.json, headers exist for {self.api_name} that are absent in `info_headers`.")
        self.citation_dict = {header: missing_data_string for header in header_addresses["info_headers"] + program_headers}
        self.citation_dict["make-md"], self.citation_dict["make-bib"] = make_md, make_bib
        self.citation_dict["add-date"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        # add in header items
        for header, address in self.api_header_addresses:
            address = self.api_header_address_root + address
            needs_processing, data = get_data_by_address(response, address)
            self.citation_dict[header] = self._process_data(header, data) if needs_processing else data
        # return completed dict
        return self.citation_dict

    def _process_data(self, header, data):
        logger.error("Not Implimented Error", f"Should not call private method _process_data() from base class {self.api_name}")
    
    def _set_citation_code(self, citation_dict):
        logger.debug(f"Creating citation code for \"{citation_dict['title'][:15].rstrip()}...\"")
        matches = [(match.group(1), match.span()) for match in re.finditer(r"<([a-z\-]*?.?[a-z]*?)>", citation_code_format)]
        first_author_family_name, first_author_given_name = citation_dict["author"].split(array_separator, 1)[0].split(first_last_separator)
        special_keys = {
            "firstauthor.family": first_author_family_name, 
            "firstauthor.given": first_author_given_name
        }
        bad_keys = [match[0] for match in matches if match[0] not in citation_dict or match[0] not in special_keys]
        if len(bad_keys) > 0:
            logger.error("Bad citation code format", f"cannot interpret <{bad_keys[0]}> in 'citation-code_format' in settings.json")
        all_indx_cutoffs = [0] + [indx for match in matches for indx in match[1]] + [len(citation_code_format)]
        non_match_indx_ranges = list(zip(all_indx_cutoffs[::2], all_indx_cutoffs[1::2]))
        final_string = ""
        for non_match_indx_range, (group, _) in zip(non_match_indx_ranges[:-1], matches):
            final_string += citation_code_format[slice(*non_match_indx_range)] + (citation_dict[group] if group in citation_dict else special_keys[group])
        final_string += citation_code_format[slice(*non_match_indx_ranges[-1])]
        logger.debug(f"Created citation code base: {final_string}")
        return final_string

    def get_work(self, code, code_type):
        if not code:
            logger.debug(f"{self.api_class_name}: {code_type} provided is empty. Skipping")
            return None
        for i in range(num_retries):
            logger.debug(f"{self.api_class_name}: Attempt {i+1} to retrieve {code_type}: {code}")
            try:
                response = self._request(code, code_type)
                if response is None:
                    logger.debug(f"{self.api_class_name}: Received 'None' response for {code_type}: {code}")
                else:
                    logger.debug(f"{self.api_class_name}: Successfully retrieved {code_type}: {code}")
                return response
            except requests.exceptions.Timeout:
                if i == num_retries - 1:
                    logger.debug(f"{self.api_class_name}: Timeout while retrieving {code_type}: {code}. No more retries left. Moving on")
                    return None
                logger.debug(f"{self.api_class_name}: Timeout while retrieving {code_type}: {code}. Sleeping for {retry_delay} seconds")
                sleep(retry_delay)
            except Exception as e:
                logger.error(e, f"{self.api_class_name}: Exception while retrieving {code_type}: {code}")

class CrossRefWorks(_GenWorks):
    def __init__(self):
        super().__init__()
        self.etiquette = None
        if all(x is not None for x in [project_name, project_version, project_url, contact_email]):
            logger.debug(f"{self.api_class_name}: polite api settings found in settings.json, using them for etiquette")
            self.etiquette = Etiquette(project_name, project_version, project_url, contact_email)
        else:
            logger.debug(f"{self.api_class_name}: polite api settings not found in settings.json, using default api")
        self.works = Works(timeout=timeout, etiquette=self.etiquette)
    
    def _request(self, code, code_type):
        return self.works.doi(code)
    
    def doi(self, doi):
        return super().get_work(doi, "DOI")
    
    def _process_data(self, header, data):
        # TODO
        pass

class _ISBNWorks(_GenWorks):
    def __init__(self, url):
        super().__init__()
        self.url = url
        self.ettiquette = None
        if all(x is not None for x in [project_name, project_version, project_url, contact_email]):
            logger.debug(f"{self.api_class_name}: polite api settings found in settings.json, sharing with api as headers")
            self.ettiquette = {
                "User-Agent": f"{project_name}/{project_version} ({project_url}; mailto:{contact_email})",
                "Accept": "application/json"
            }
        else:
            logger.debug(f"{self.api_class_name}: polite api settings not found in settings.json, using api anonymously")
    
    def _request(self, code, code_type):
        response = requests.get(self.url + code, timeout=timeout, headers=self.ettiquette)
        if response.status_code == 200:
            return self._validate(response.json())
        logger.debug(f"{self.api_class_name}: HTTP error {response.status_code} while retrieving {code_type}: {code}")
        return None
    
    def _validate(self, response):
        logger.error("Not Implimented Error", f"Should not call private method _validate() from base class {self.api_name}")
    
    def isbn(self, isbn):
        return super().get_work(isbn, "ISBN")

class OpenLibraryWorks(_ISBNWorks):
    def __init__(self):
        super().__init__(openlibrary_url)
    
    def _validate(self, response):
        if not "numFound" in response or response["numFound"] != 1:
            return None
        return response
    
    def _process_data(self, header, data):
        # TODO
        pass

class GoogleBooksWorks(_ISBNWorks):
    def __init__(self):
        super().__init__(googlebooks_url)
    
    def _validate(self, response):
        if "totalItems" not in response or response["totalItems"] != 1:
            return None
        return response
    
    def _process_data(self, header, data):
        # TODO
        pass
       
