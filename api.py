from crossref.restful import Works, Etiquette
from time import sleep
from aux import settings, logger
import requests

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
    logger.debug("Loading api response data paths from settings.json")
    data_paths = settings["advanced"]["csv_headers"]
    if any(x not in data_paths for x in ["crossref", "openlibrary", "googlebooks"]):
        logger.error("settings.json file is missing required keys in advanced.csv_headers")
    logger.debug("Finished loading settings from settings.json for api.py")
except KeyError as e:
    logger.error(e, "settings.json file is missing required keys")

### API classes
class _GenWorks:
    def __init__(self, url=None):
        self.api_class_name = self.__class__.__name__
        self.api_name = self.api_class_name.replace("Works", "").lower()
        self.data_paths = data_paths[self.api_name]
        self.data_path_root = self.data_paths.pop("/") if "/" in self.data_paths else ""
        self.url = url

    def _request(self, code, code_type):
        pass

    def get_csv_row(self, response):
        pass

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
    
    def get_csv_row(self, response):
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
        pass
    
    def isbn(self, isbn):
        return super().get_work(isbn, "ISBN")

class OpenLibraryWorks(_ISBNWorks):
    def __init__(self):
        super().__init__(openlibrary_url)
    
    def _validate(self, response):
        if not "numFound" in response or response["numFound"] != 1:
            return None
        return response
    
    def get_csv_row(self, response):
        # TODO
        pass

class GoogleBooksWorks(_ISBNWorks):
    def __init__(self):
        super().__init__(googlebooks_url)
    
    def _validate(self, response):
        if "totalItems" not in response or response["totalItems"] != 1:
            return None
        return response
    
    def get_csv_row(self, response):
        # TODO
        pass
       
