from md_files import Markdowns
from bibliography_files import BibtexBib, HayagrivaBib
from api import CiteWorks
from csv_file import CSV
from aux import logger, verify_arguments, has_data, CommandCiteError
import sys

if __name__ == "__main__":
    csv = CSV()
    api = CiteWorks()
    md = Markdowns()
    bibtex, hayagriva = BibtexBib(), HayagrivaBib()
    all_codes = csv.get_all_citation_codes()

    try:
        # setup
        arguments = sys.argv[1:]
        update_all_entries, entries_to_update, entries_to_rename, entry_codes = verify_arguments(arguments, all_codes)

        # update entries
        if update_all_entries:
            entries_to_update = csv.get_all_citation_codes()
        if len(entries_to_update) > 0:
            logger.progress("Updating Entries", title_message=True)
            entries_that_need_updating = csv.get_entries_needing_updating()
            for code in entries_to_update:
                logger.progress(f"Checking if {code} needs to be updated")
                # get old citation dict
                citation_dict = csv.get_entry(code)
                # get new citation dict
                if entries_that_need_updating is not None and code in entries_that_need_updating:
                    new_dict_requested = True
                    if has_data(citation_dict["doi"]):
                        id_num = citation_dict["doi"]
                        id_num_type = "doi"
                    elif has_data(citation_dict["isbn"]):
                        id_num = citation_dict["isbn"]
                        id_num_type = "isbn"
                    new_citation_dict = api.get_csv_row(id_num, id_num_type)
                else:
                    new_citation_dict = citation_dict
                    new_dict_requested = False
                # update csv
                if new_dict_requested and new_citation_dict is not None:
                    csv.update_entry(code, new_citation_dict)
                elif new_dict_requested and new_citation_dict is None:
                    csv.fill_missing_cells(code)
                new_citation_dict = csv.get_entry(code)
                # update mds
                md.create_or_update_file(new_citation_dict, csv.get_codes_cited_by_code(code))
                # update bibliographies
                bibtex.create_or_update_citation(new_citation_dict)
                hayagriva.create_or_update_citation(new_citation_dict)
                logger.progress_newline()

        # rename entries
        if len(entries_to_rename) > 0:
            logger.progress("Renaming Entries", title_message=True)
            for current_code, new_base_code in entries_to_rename.items():
                # change code in csv
                cited_by = csv.get_codes_that_cite_code(current_code)
                new_code = csv.change_citation_code(current_code, new_base_code)
                # change code in md
                md.change_citation_code(current_code, new_code, cited_by)
                # change code in bibliographies
                bibtex.change_citation_code(current_code, new_code)
                hayagriva.change_citation_code(current_code, new_code)
                logger.progress_newline()

        # make new entries
        if len(entry_codes) > 0:
            logger.progress("Creating New Entries", title_message=True)
            existing_codes = csv.get_all_id_nums()
            for entry_info in entry_codes:
                id_num, id_num_type = entry_info[:2]
                if id_num in existing_codes[id_num_type]:
                    logger.progress(f"The {id_num_type} \"{id_num}\" is already found in the citations csv. Skipping.")
                    logger.progress_newline()
                    continue
                citation_dict = api.get_csv_row(*entry_info)
                if citation_dict is not None:
                    # add to csv
                    citation_dict = csv.add_from_api(citation_dict)
                    # add md file
                    code = citation_dict["citation-code"]
                    md.create_or_update_file(citation_dict, csv.get_codes_cited_by_code(code))
                    code_lst = csv.get_codes_that_cite_code(code)
                    if code_lst is not None:
                        for citing_code in csv.get_codes_that_cite_code(code):
                            citing_dict = csv.get_entry(citing_code)
                            cited_links_list = csv.get_codes_cited_by_code(citing_code)
                            md.create_or_update_file(citing_dict, cited_links_list)
                    # add bibliography entries
                    bibtex.create_or_update_citation(citation_dict)
                    hayagriva.create_or_update_citation(citation_dict)
                logger.progress_newline()

        # delete files and entries for missing data
        logger.progress("Saving Files", title_message=True)
        citation_code_lst = csv.get_all_citation_codes()
        md.delete_unmatched_files(citation_code_lst)
        bibtex.delete_unmatched_citations(citation_code_lst)
        hayagriva.delete_unmatched_citations(citation_code_lst)

        # save file
        csv.save_file()
        bibtex.save_file()
        hayagriva.save_file()
        logger.close()

    except Exception as e:
        for file_class in (csv, bibtex, hayagriva):
            file_class.save_file(revert_to_old=True)
        md.revert_files()
        if isinstance(e, CommandCiteError):
            logger.close()
        else:
            logger.error(e, "", kill=True)