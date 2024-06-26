
### api.py

from api import CrossRefWorks, _ISBNWorks, GoogleBooksWorks, OpenLibraryWorks, _GenWorks

class _TestWorks(_GenWorks):
    def _request(self, code, code_type):
        return None

class _TestWorksISBN404(_ISBNWorks):
    def __init__(self):
        super().__init__("http://httpstat.us/404?sleep=")

_TestWorks().get_work("", "code_type")
_TestWorks().get_work("123", "code_type")
_TestWorksISBN404().get_work("1000", "code_type")
_TestWorksISBN404().get_work("3100", "code_type")
CrossRefWorks().doi("10.1126/science.359.6377.725") # real doi
CrossRefWorks().doi("10.1126/111111111111111111111111") # fake doi
OpenLibraryWorks().isbn("9780134092669") # real isbn
OpenLibraryWorks().isbn("97801340929") # fake isbn
GoogleBooksWorks().isbn("9780134092669") # real isbn
GoogleBooksWorks().isbn("97801340929") # fake isbn


