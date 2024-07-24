# Command Cite - a simple-to-use command-line citation manager

## Description

A command line tool that takes DOIs and ISBNs to query databases for citation details. Currently, this program uses [Crossref](https://www.crossref.org/documentation/) for DOI citations and [OpenLibrary](https://openlibrary.org/developers)/[GoogleBooks](https://developers.google.com/books/docs/overview) for ISBN citations. With information collected by these sources, a `.csv` database is created, which the user can edit if desired. In addition to this document, this program can create and manage the following:
 - Markdown (`.md`) files for each entry for notes, compatible with [Obsidian](https://www.obsidian.md)
    - Can create link between cited articles to create citation graphs
 - A citation file, either:
    - The [BibTeX](https://www.bibtex.org/) format (can be used in a variety of word processors for citations, including [Microsoft Word](https://interfacegroup.ch/how-can-i-use-my-bibtex-library-in-ms-word/) and [LaTeX](https://www.overleaf.com/learn/latex/Bibliography_management_with_bibtex))
    - The [Hayagriva](https://github.com/typst/hayagriva/blob/main/docs/file-format.md) format (used by [Typst](typst.app))

## How to Set Up

1. Start by downloading the files in this repository to a location on your computer that works best for you. 
2. Change the settings in `settings.json` so that you can specify which files are generated where. Most importantly, make sure that the directory is specified for the CSV files, the Markdown files, and the bibliography files. These directories can be specified relative to this repository or absolutely. These folders must exist before running the script, but the files will be auto-generated.
3. At any point, you can run the script in the terminal with `python /path_to_repo/main.py [arguments]`, but you may find it easier to do the following instead so that the `cite` command can be used in your terminal at any time.
   - The following assumes that Windows users are using [git bash](https://git-scm.com/download/win).
   - Create a folder within the downloaded repository, and add the path of that folder to your PATH variable (instructions for [Windows](https://stackoverflow.com/a/74571841/13597979) and [Mac](https://pimylifeup.com/macos-path-environment-variable/#permanently-setting-the-environment-path-variable-on-macos)).
   - In that folder, create a file called `cite` with the command `touch cite`.
   - Run the following commands in the terminal. Remember to change `path_to_repo` to the path to the repository. Mac users should use `python3` instead of just `python`.
   ```bash
   echo -e "#\!/bin/bash\npython /path_to_repo/main.py \"@\"" >> cite
   chmod +x cite # changes permissions to make script executable
   ```
   - Now, wherever your current working directory is for your terminal, you can use the `cite` command in your terminal as shown in the examples below.

The package dependencies for this program are:

```bash
pip install crossrefapi # crossref package for DOIs
pip install pylatexenc # OPTIONAL - for bibtex encoding
```

## Command Line Interface

To cite a document by its DOI or ISBN, run:
```bash
cite 10.1126/science.359.6377.725
cite 9780134092669
# or give several at the same time
cite 10.1126/science.359.6377.725 9780134092669 "10.1016/0304-3800(88)90071-3"
# note the quotation marks are used to escape the parentheses in the last doi
```

To set a specific `citation-code` for a citation while adding it, run:
```bash
cite 10.1126/science.359.6377.725 --setcode Hutson_2018
```

To change the `citation-code` for an existing citation, run:
```bash
cite --rename Hutson_2018a AI_reproducibility_Hutson
# note that no suffix is included for the replacement code since it will be auto-generated
```

If you change the contents of the `.csv` file and want to update the other files managed by this program, run:
```bash
cite --update Johnson_2009a # to update documents for a specific document, or
cite --update-all # to update across all citations
```

To see descriptions of all flags, run:
```bash
cite --help
```

## Settings

This program is customizable using the included `settings.json` file. Descriptions for the use of each property in the file are given in `_comment` properties. Some examples of user-adjustable settings include:

- Specify the fields inserted into `.md` files (*see `markdown.included_properties` and `markdown.user-defined_properties`*)
- Change all titles to title case by default (*see `citations_csv.title_case_titles`*)
- Change the `citation-code` format from the default `Lastname_YYYY` to custom formats (*see `citations_csv.citation-code_format`*)
- Specify if `.md` files and what type of bibliography files should be made (*see `markdown.make_md`, `bibliography.make_hayagriva`, and `bibliography.make_bibtex`*)
- Automate the creation of links to user-collected PDFs in `.md` documents (*see `markdown.automate_pdf_link`*)
- Specify what APIs should be used, and access faster API speeds by providing personal information if desired (*see `api_preference` and `polite_api`*)

## Example Usage

The following shows a series of commands that build up a citation data base on your computer. Pay attention to the comments to understand the behavior of the program with each command.

```bash
cite 10.1098/rspa.2018.0862 10.1111/j.0014-3820.2004.tb01669.x "10.1016/0304-3800(88)90071-3"
# adds articles Beven_2019a, Gandon_2004a, Caswell_1988a
# note quotation marks around final doi to sidestep issue with parentheses
```

```bash
cite 10.1111/j.1753-318X.2010.01078.x
# adds article Wilkinson_2010a
```

```bash
cite 9780684830681 --setcode Mitchell_TEST_2001 978-39-39837-114 978-111-85006-0-6
# adds books Mitchell_TEST_2001 and Geßner_2011a, but cannot find 978-111-85006-0-6 in databases (would have to be added by hand to citations csv)
```

```bash
cite --rename Mitchell_TEST_2001a Mitchell_2001
# renames citation code Mitchell_TEST_2001 to be Mitchell_2001a
# note that the argument `Mitchell_2001` omits the `a` since the citation code suffix must be added by the program
```

```bash
cite 10.1007/s00285-023-01912-w
# adds article Hanthanan_Arachchilage_2023a
```

```bash
cite --rename Hanthanan_Arachchilage_2023a Hanthanan_2023
# renames citation code Hanthanan_Arachchilage_2023a to be Hanathan_2023a
# note that the argument `Hanthanan_2023` omits the `a` since the citation code suffix must be added by the program
```

```bash
cite 10.1098/rspa.2002.0986 10.5194/hess-4-203-2000 10.5194/hess-5-1-2001
# adds articles Beven_2002a, Beven_2000a, and Beven_2001a
# the citation Beven_2019a cites these papers, so the markdown document Beven_2019a.md has links to the respective 
```

```bash
# I manually changed author name of Beven_2001a in citations csv (initially Beven*+K.) to Beven papers better: `Beven+K. J.`
cite --update Beven_2001a
# now markdown and bibliograpy documents all show Beven, K. J.
```

```bash
# in citations csv, I manually did the following: 
# - edited Wilkinson_2010a to be missing title
# - edited Mitchell_2001a to have the year, month, and day of 1936, 6, and 30, respectively
# - added a citation Laaren_2013 with title, year/month/day, publisher, isbn, and type, leaving all other entries blank
cite --update-all
# the following change after running: 
# - Wilkinson_2010a has a title again
# - markdown and bibliography files for Mitchell_2001a show the updated time
# - after ISBN is not found, Laaren_2013 is processed as normal with blanks in csv filled with NAs and markdown and bibliography entries created
```
