"""
This script automates replacing the embedded PDF file inside ADOC (zip-based) agreement documents.

During development, newly generated agreements include a PDF file that normally must be signed
through a real signing process. To streamline development and testing, this script allows you to
replace that PDF with a pre-signed or artificially signed version (e.g., generated using an LLM like ChatGPT),
so you can simulate agreement signing without performing the full signing flow.

How it works:
- You provide one or more ADOC files that contain a file named `sutartis_valid.pdf`.
- You also provide a replacement PDF file, typically containing fake or test signatures.
- For each ADOC file, the script unpacks the archive, replaces the embedded PDF, and re-packages it.

Usage instructions:
1. In the same directory as this script, create a folder named `files_to_replace/`
   and place all ADOC files you want processed inside it.
2. Place the replacement PDF in the same directory as the script, named `pdf_file_to_replace.pdf`.
   This PDF will be injected into all ADOC files that contain `sutartis_valid.pdf`.
3. Run the script using:
       python3 replace_pdf_file_in_adadocs.py
4. The script will create a new folder named `replaced_files/`, containing all processed ADOC files.

Notes:
- If an ADOC file does not contain `sutartis_valid.pdf`, it will be copied unchanged.
- macOS-generated files such as `.DS_Store` and `__MACOSX` are ignored automatically.

This tool is intended only for development and testing convenience.
"""


import os
import shutil
import zipfile
import tempfile


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SOURCE_PDF = os.path.join(BASE_DIR, "pdf_file_to_replace.pdf")
ADOC_FOLDER = os.path.join(BASE_DIR, "files_to_replace")
REPLACED_FOLDER = os.path.join(BASE_DIR, "replaced_files")

EXCLUDE_PATTERNS = {".DS_Store", "__MACOSX"}

os.makedirs(REPLACED_FOLDER, exist_ok=True)


def unzip_adoc(adoc_path: str, extract_to: str) -> None:
    """Unzip an .adoc file (zip archive) to a directory."""
    with zipfile.ZipFile(adoc_path, "r") as file:
        for member in file.namelist():
            if any(pattern in member for pattern in EXCLUDE_PATTERNS):
                continue
            file.extract(member, extract_to)


def zip_adoc(directory: str, output_path: str) -> None:
    """Zip a directory into an .adoc file."""
    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as _zip_file:
        for root, directories, files in os.walk(directory):
            directories[:] = [_directory for _directory in directories if _directory not in EXCLUDE_PATTERNS]
            files = [file for file in files if file not in EXCLUDE_PATTERNS]

            for file in files:
                full_path = os.path.join(root, file)
                arcname = os.path.relpath(full_path, directory)
                _zip_file.write(full_path, arcname=arcname)


def replace_pdf_in_adoc(adoc_path: str, output_folder: str) -> None:
    """Extract ADOC, replace PDF if exists, rezip to output folder."""
    filename = os.path.basename(adoc_path)
    print(f"Processing: {filename}")

    temp_dir = tempfile.mkdtemp()
    output_path = os.path.join(output_folder, filename)

    try:
        unzip_adoc(adoc_path, temp_dir)

        pdf_target_path = os.path.join(temp_dir, "sutartis_valid.pdf")
        if os.path.exists(pdf_target_path):
            shutil.copy2(SOURCE_PDF, pdf_target_path)
            zip_adoc(temp_dir, output_path)
            print(f" ✔️  Replaced PDF and saved to {output_path}")
        else:
            # PDF missing → just copy original ADOC
            shutil.copy2(adoc_path, output_path)
            print(f" ⚠️  Missing sutartis_valid.pdf, copied original to {output_path}")

    finally:
        shutil.rmtree(temp_dir)


def main() -> None:
    for file in os.listdir(ADOC_FOLDER):
        if not file.endswith(".adoc"):
            continue
        adoc_path = os.path.join(ADOC_FOLDER, file)
        replace_pdf_in_adoc(adoc_path, REPLACED_FOLDER)


if __name__ == "__main__":
    main()
