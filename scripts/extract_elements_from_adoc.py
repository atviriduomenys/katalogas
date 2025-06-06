from typer import Argument, run

from vitrina.smart_contracts.services import extract_elements_from_adoc


SCOPES_REGEX = r"\buapi:/\S+"
TEMPLATE_CHECKSUM_REGEX = r"(?:^|\s)template_checksum:\S+"
JSON_CHECKSUM_REGEX = r"(?:^|\s)json_checksum:\S+"


def main(
    adoc_file: str = Argument(..., help="Path to the ADOC file to extract scopes from"),
):
    if results := extract_elements_from_adoc(adoc_file, SCOPES_REGEX):
        print("Found scopes elements:")
        for uri in results:
            print(f" - {uri}")
    else:
        print("No scopes elements found.")

    if result := extract_elements_from_adoc(adoc_file, TEMPLATE_CHECKSUM_REGEX):
        checksum = result[0].replace("template_checksum:", "")
        print(f"Found template checksum: {checksum}")
    else:
        print("No template checksum found.")

    if result := extract_elements_from_adoc(adoc_file, JSON_CHECKSUM_REGEX):
        checksum = result[0].replace("json_checksum:", "")
        print(f"Found json checksum: {checksum}")
    else:
        print("No json checksum found.")


if __name__ == "__main__":
    run(main)
