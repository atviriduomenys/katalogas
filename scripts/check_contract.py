import sys

from typer import Argument, run

from vitrina.smart_contracts.exceptions import InvalidAdocError
from vitrina.smart_contracts.services import has_valid_signature, get_pdf_checksum_from_adoc


def main(
    adoc_file_path: str = Argument(..., help="Path to the ADOC file"),
    expected_checksum: str = Argument(..., help="Expected SHA256 checksum for the PDF"),
) -> None:
    try:
        if has_valid_signature(adoc_file_path):
            print("Signature found")
        else:
            print("Signature not found")
        
        if get_pdf_checksum_from_adoc(adoc_file_path) == expected_checksum:
            print("Checksum matches")
        else:
            print("Checksum doesn't match")
    except InvalidAdocError as e:
        print(f"Invalid ADOC file: {e}")
        sys.exit(1)


if __name__ == "__main__":
    run(main)
