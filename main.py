from api import CrossRefWorks, GoogleBooksWorks, OpenLibraryWorks
from aux import logger, settings


from collections import defaultdict
from datetime import datetime
from os.path import exists, join, dirname
import traceback, sys
import csv, yaml
import re


try:
    pass
except Exception as e:
    logger.error(e, "unexpected error encountered")