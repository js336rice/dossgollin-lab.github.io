import bibtexparser
from bibtexparser.bparser import BibTexParser
from pathlib import Path
import re
from titlecase import titlecase

# optionally update
TARGET = Path("_bibliography/my-papers.bib")


def citekey_to_string(citekey):
    """Sanitize the citekey to generate a valid filename."""
    return re.sub(r"[^a-zA-Z0-9_-]", "_", citekey)


def escape_yaml_string(value):
    """Escape characters in a string to make it valid for YAML."""
    return value.replace(r"\&", "&").replace(r"\:", ":")


def format_title(title):
    """Format the title using titlecase except for content inside curly braces."""
    if not title:
        return title

    # Iteratively convert double curly braces to single
    while "{{" in title and "}}" in title:
        title = title.replace("{{", "{").replace("}}", "}")

    # Extract content inside curly braces and replace with placeholders
    preserved_texts = re.findall(r"{(.*?)}", title)
    for idx, text in enumerate(preserved_texts):
        placeholder = f"PLACEHOLDER{idx}"
        title = title.replace("{" + text + "}", placeholder)

    # Use titlecase on the rest
    title = titlecase(title)

    # Replace placeholders with original text from curly braces
    for idx, text in enumerate(preserved_texts):
        placeholder = f"PLACEHOLDER{idx}"
        title = title.replace(placeholder, text)

    return title


def format_author_name(name):
    """Format the author name considering both 'lastname, firstname' and detailed formats."""
    if "family=" in name and "given=" in name:
        family = re.search(r"family=([^,]+)", name).group(1).strip()
        given = re.search(r"given=([^,]+)", name).group(1).strip()
        prefix = ""
        if "prefix=" in name:
            prefix = re.search(r"prefix=([^,]+)", name).group(1).strip()
            use_prefix = re.search(r"useprefix=([^,]+)", name).group(1).strip()
            if use_prefix == "true":
                family = prefix + " " + family
        return given + " " + family
    elif "," in name:
        last, first = name.split(",", 1)
        return first.strip() + " " + last.strip()
    return name


def format_date(date):
    """Format the date to be in the form YYYY-MM-DD."""
    try:
        year = int(date)
        return date + "-01-01"
    except:
        return date


def get_details_from_entry(entry):
    """Retrieve the details field based on the entry type."""
    if entry["ENTRYTYPE"] == "article":
        return entry.get("journaltitle", "")
    elif entry["ENTRYTYPE"] == "inproceedings":
        if "booktitle" in entry:
            return entry["booktitle"]
        elif "eventtitle" in entry and "publisher" in entry:
            return entry["publisher"] + " " + entry["eventtitle"]
        elif "eventtitle" in entry:
            return entry["eventtitle"]
        else:
            return ""
    else:
        return entry.get("howpublished", "")


def write_metadata_to_qmd(entry, qmd_file):
    """Write the metadata of a BibTeX entry to a QMD file."""
    # Initial metadata separator
    qmd_file.write("---\n")

    # Title
    qmd_file.write(
        f"title: \"{format_title(escape_yaml_string(entry.get('title', '')))}\"\n"
    )

    # Author
    authors = entry.get("author", "").split(" and ")
    qmd_file.write("author:\n")
    for author in authors:
        formatted_author = format_author_name(author.strip())
        qmd_file.write(f"  - {formatted_author}\n")

    # Date
    date = format_date(entry.get("date", ""))
    qmd_file.write(f"date: {date}\n")

    # Details
    details = format_title(escape_yaml_string(get_details_from_entry(entry)))
    qmd_file.write(f'details: "{details}"\n')

    # Image
    has_img = False
    citekey = citekey_to_string(entry["ID"])
    for extension in ["png", "jpg", "jpeg"]:
        if has_img:
            break
        image_path = Path(f"_assets/img/pubs/{citekey}.{extension}")
        if image_path.exists():
            qmd_file.write(f"image: ../../{image_path}\n")

    # Use the about
    qmd_file.write("\nabout:\n")
    qmd_file.write("  template: solana\n")

    # Links
    if "doi" in entry or "repo" in entry or "preprint" in entry or "url" in entry:
        qmd_file.write("  links:\n")

    # DOI
    if "doi" in entry:
        doi = entry["doi"]
        is_open = entry.get("open", "") == "true"
        if is_open:
            qmd_file.write(f"    - text: 'DOI: {doi} (Open Access)'\n")
        else:
            qmd_file.write(f"    - text: 'DOI: {doi}'\n")
        qmd_file.write(f"      href: https://doi.org/{entry['doi']}\n")
        qmd_file.write(f"      icon: link\n")

    elif "url" in entry:
        url = entry["url"]
        is_open = entry.get("open", "") == "true"
        qmd_file.write(f"    - href: {url}\n")
        qmd_file.write(f"      icon: link\n")
        if is_open:
            qmd_file.write(f"      text: 'Open Access'\n")
        else:
            qmd_file.write(f"      text: 'Link'\n")

    # Repository
    if "repo" in entry:
        qmd_file.write("    - icon: github\n")
        qmd_file.write("      text: Code\n")
        qmd_file.write(f"      href: {entry['repo']}\n")

    # Preprint
    if "preprint" in entry:
        qmd_file.write("    - text: Preprint\n")
        qmd_file.write(f"      icon: file-pdf\n")
        qmd_file.write(f"      href: {entry['preprint']}\n")

    # End of metadata
    qmd_file.write("\nformat:\n  html:\n    page-layout: full\n")
    qmd_file.write("---")

    # Abstract
    if "abstract" in entry:
        qmd_file.write("\n\n")
        qmd_file.write(entry["abstract"])


def entry_to_qmd(entry):
    """Convert a BibTeX entry to QMD format."""
    citekey = citekey_to_string(entry["ID"])

    # Determine the directory based on the entry type
    if entry["ENTRYTYPE"] == "article":
        directory = "publications/article"
    elif entry["ENTRYTYPE"] == "inproceedings":
        directory = "publications/conference"
    elif entry["ENTRYTYPE"] in ["online", "preprint"]:
        directory = "publications/forthcoming"
    else:
        directory = "publications/other"

    qmd_filename = Path(directory, f"{citekey}.qmd")
    qmd_filename.parent.mkdir(parents=True, exist_ok=True)

    with open(qmd_filename, "w") as qmd_file:
        write_metadata_to_qmd(entry, qmd_file)


def create_qmd_from_bib(bib_file):
    parser = BibTexParser(common_strings=True)
    parser.ignore_nonstandard_types = False
    with open(bib_file, "r") as bibtex_file:
        bib_database = bibtexparser.load(bibtex_file, parser=parser)
    for entry in bib_database.entries:
        entry_to_qmd(entry)


if __name__ == "__main__":
    for dir in [
        "publications/article",
        "publications/conference",
        "publications/other",
        "publications/forthcoming",
    ]:
        for file in Path(dir).glob("*.qmd"):
            file.unlink()

    create_qmd_from_bib(TARGET)
