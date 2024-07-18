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

    try:
        # setup
        arguments = sys.argv[1:]
        update_all_entries, entries_to_update, entries_to_rename, entry_codes = verify_arguments(arguments)

        # update entries
        if update_all_entries:
            entries_to_update = csv.get_entries_needing_updating()
        if len(entries_to_update) > 0:
            for code in entries_to_update:
                # get old citation dict
                citation_dict = csv.get_entry(code)
                # get new citation dict
                if has_data(citation_dict["doi"]):
                    id_num = citation_dict["doi"]
                    id_num_type = "doi"
                elif has_data(citation_dict["isbn"]):
                    id_num = citation_dict["isbn"]
                    id_num_type = "isbn"
                new_citation_dict = api.get_csv_row(id_num, id_num_type)
                if new_citation_dict is not None:
                    # update csv
                    csv.update_entry(code, new_citation_dict)
                    new_citation_dict = csv.get_entry(code)
                    # update mds
                    md.update_file(new_citation_dict)
                    # update bibliographies
                    bibtex.create_or_update_citation(new_citation_dict)
                    hayagriva.create_or_update_citation(new_citation_dict)

        # rename entries
        if len(entries_to_rename) > 0:
            for current_code, new_base_code in entries_to_rename.items():
                # change code in csv
                cited_by = csv.get_codes_that_cite_code(current_code)
                new_code = csv.change_citation_code(current_code, new_base_code)
                # change code in md
                md.change_citation_code(current_code, new_code, cited_by)
                # change code in bibliographies
                bibtex.change_citation_code(current_code, new_code)
                hayagriva.change_citation_code(current_code, new_code)

        # make new entries
        if len(entry_codes) > 0:
            existing_codes = csv.get_all_id_nums()
            for entry_info in entry_codes:
                id_num, id_num_type = entry_info[:2]
                if id_num in existing_codes[id_num_type]:
                    logger.progress(f"The {id_num_type} {id_num} is already found in the citations csv. Skipping.")
                    continue
                citation_dict = api.get_csv_row(*entry_info)
                if citation_dict is not None:
                    # add to csv
                    citation_dict = csv.add_from_api(citation_dict)
                    # add md file
                    md.create_file(citation_dict)
                    # add bibliography entries
                    bibtex.create_or_update_citation(citation_dict)
                    hayagriva.create_or_update_citation(citation_dict)

        # delete files and entries for missing data
        citation_code_lst = csv.get_all_citation_codes()
        md.delete_unmatched_files(citation_code_lst)
        bibtex.delete_unmatched_citations(citation_code_lst)
        hayagriva.delete_unmatched_citations(citation_code_lst)

        # save file
        csv.save_file()
        bibtex.save_file()
        hayagriva.save_file()

    except Exception as e:
        # for file_class in (csv, bibtex, hayagriva):
        #     file_class.save_file(revert_to_old=True)
        # md.revert_files()
        if not isinstance(e, CommandCiteError):
            logger.error(e, "", kill=True)