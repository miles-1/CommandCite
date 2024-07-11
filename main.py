from api import CrossRefWorks, GoogleBooksWorks, OpenLibraryWorks
from csv_file import CSV
from aux import logger, settings, is_valid_citation_code, format_arguments, format_base_citation_code
import sys

try:
    logger.debug("Loading settings from settings.json into main.py")
    update_blanks_automatically = settings["citations_csv"]["update_blanks_automatically"]
    logger.debug("Finished loading settings from settings.json into main.py")
except KeyError as e:
    logger.error(e, "Missing keys in settings.json")

def verify_arguments(arguments):
    update_all_entries = False
    entries_to_update = []
    entries_to_rename = {}
    # check for arguments
    if len(arguments) == 0:
        logger.error("No Arguments", "This program requires at least one argument to run")
    if "--help" in arguments:
        print("""Tags and their use:
--help                                     Print this message
--update-all                               Fill in any blanks for program-managed headers of citations csv file for all rows, and update markdowns and bibliography files if they exist
--update [citation-code]                   Same as --update-all but instead for specified [citation-code]
--rename [citation-code] [new-base-code]   Change the citation code for the given [citation-code] to have a new one, with base code specified by [new-base-code] (no suffix should be included)
[doi-or-isbn] --setcode [new-base-code]    For a given DOI or ISBN, set the citation code to have a base code of [new-base-code]

Note that --help can only be run alone, and --update-all and --update cannot be used together. Other than that, any sequence or repetition of DOIs or ISBNs can be given to this program.""")
        sys.exit(1)
    # handle --update-all tag
    if "--update-all" in arguments or update_blanks_automatically:
        for _ in range(arguments.count("--update-all")):
            arguments.pop(arguments.index("--update-all"))
        if "--update" in arguments:
            logger.error("Bad Flag Use", "The \"--update\" flag is not allowed if \"--update-all\" is used or \"update_blanks_automatically\" is enabled in settings.json")
        update_all_entries = True
        logger.debug("All entries are set to update")
    # handle --update tag
    if "--update" in arguments:
        for _ in range(arguments.count["--update"]):
            tag_indx = arguments.index("--update")
            if len(arguments) <= tag_indx + 1:
                logger.error("Bad Flag Use", "The \"--update\" flag must be followed by a valid citation code")
            citation_code = arguments[tag_indx + 1]
            if not is_valid_citation_code(citation_code):
                logger.error("Bad Flag Use", f"The \"--update\" flag must be followed by a valid citation code, and \"{citation_code}\" is an invalid citation code")
            for _ in range(2):
                arguments.pop(tag_indx) # remove tag and citation code
            entries_to_update.append(citation_code)
        logger.debug(f"The following entries are set to update: {', '.join(entries_to_update)}")
    # handle --rename tag
    if "--rename" in arguments:
        for _ in range(arguments.count("--rename")):
            tag_indx = arguments.index("--rename")
            if len(arguments) <= tag_indx + 2 or not is_valid_citation_code(arguments[tag_indx+1]) or arguments[tag_indx+2].startswith("--"):
                if len(arguments) <= tag_indx + 2:
                    extra_info = ""
                elif not is_valid_citation_code(arguments[tag_indx+1]):
                    extra_info = f" However, the citation code \"{arguments[tag_indx+1]}\" is not valid."
                else:
                    extra_info = f" However, the tag \"{arguments[tag_indx+2]}\" was found where the base code should be."
                logger.error("Bad Flag Use", f"The \"--update\" flag must be followed by a valid citation code and a new base citation code (no suffix) that will serve as its replacement.{extra_info}")
            entries_to_rename[arguments[tag_indx + 1]] = format_base_citation_code(arguments[tag_indx + 2])
            for _ in range(3):
                arguments.pop(tag_indx) # remove tag, citation code, and new base citation code
    # collect dois and isbns
    return update_all_entries, entries_to_update, entries_to_rename, format_arguments(arguments)

try:
    arguments = sys.argv[1:]
    update_all_entries, entries_to_update, entries_to_rename, entry_codes = verify_arguments(arguments)
    csv = CSV()
    if update_all_entries:
        entries_to_update = csv.get_entries_needing_updating()
    if len(entries_to_update) > 0:
        # TODO: update each code, update mds and bibs
        pass
    if len(entries_to_rename) > 0:
        for current_code, new_base_code in entries_to_rename.items():
            csv.change_citation_code(current_code, new_base_code)
    if len(entry_codes) > 0:
        # TODO: add new entry codes, add mds, add to bibs
        pass
    csv.save_file()
except Exception as e:
    csv.save_file(revert_to_old=True)
    logger.error(e, "unexpected error encountered")