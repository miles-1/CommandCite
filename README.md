# Citation Manager

## Description

A command line tool that takes DOIs and ISBNs to query databases for citation details. Currently, this program uses [Crossref](https://www.crossref.org/documentation/) for DOI citations and [OpenLibrary](https://openlibrary.org/developers)/[GoogleBooks](https://developers.google.com/books/docs/overview) for ISBN citations. With information collected by these sources, a `.csv` database is created, which the user can edit if desired. In addition to this document, this program can create and manage the following:
 - Markdown (`.md`) files for each entry for notes, compatible with [Obsidian](https://www.obsidian.md)
    - Can create link between cited articles to create citation graphs
 - A citation file, either:
    - The [BibTeX](https://www.bibtex.org/) format (can be used in a variety of word processors for citations, including [Microsoft Word](https://interfacegroup.ch/how-can-i-use-my-bibtex-library-in-ms-word/) and [LaTeX](https://www.overleaf.com/learn/latex/Bibliography_management_with_bibtex))
    - The [Hayagriva](https://github.com/typst/hayagriva/blob/main/docs/file-format.md) format (used by [Typst](typst.app))

## How to Set Up

Start by downloading the files in this repository. Then, {{TODO}}

## Command Line Interface

To cite a document by its DOI, run:

```bash
cite 10.1126/science.359.6377.725
# or...
cite --doi 10.1126/science.359.6377.725
```

To cite a document by its ISBN, run:
```bash
cite 9780134092669
# or...
cite --isbn 9780134092669
```

To set a specific `citation-code` for a document, run:
```bash
cite 10.1126/science.359.6377.725 --setcode Hutson_2018
```

To change the `citation-code` for an existing document, run:
```bash
cite --rename Hutson_2018a AI_reproducibility_Hutson
# note that no suffix is included for the replacement code since it will be auto-generated
```

If you change the contents of the `.csv` file and want to update the other files managed by this program, run:
```bash
cite --update Johnson_2009a # to update documents for a specific document, or
cite --update-all # to update across all citations
```

If you have enabled markdown or bibliography generation, you can exclude specific citations from markdown generation or inclusion in a bibliography:
```bash
cite 10.1126/science.359.6377.725 --nomd # skips .md creation
cite 10.1126/science.359.6377.725 --nobib # skips inclusion in bibliography file
```

## Settings

This program is customizable using the included `settings.json` file. Descriptions for the use of each property in the file are given in `_comment` properties. Some examples of user-adjustable settings include:

- Specify the fields inserted into `.md` files (*see `markdown.included_properties` and `markdown.user-defined_properties`*)
- Change all titles to title case by default (*see `citations_csv.title_case_titles`*)
- Change the `citation-code` format from the default `Lastname_YYYY` to custom formats (*see `citations_csv.citation-code_format`*)
- Specify if `.md` files and what type of bibliography files should be made (*see `markdown.make_md`, `bibliography.make_hayagriva`, and `bibliography.make_bibtex`*)
- Automate the creation of links to user-collected PDFs in `.md` documents (*see `markdown.automate_pdf_link`*)
- Specify what APIs should be used, and access faster API speeds by providing personal information if desired (*see `api_preference` and `polite_api`*)
