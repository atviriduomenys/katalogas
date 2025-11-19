from typer import Option, run

from vitrina.smart_contracts.services import generate_contract
from vitrina.smart_contracts.utils import generate_checksum


def main(
    template: str,
    json: str,
    output: str = Option("contract.pdf", "--output", "-o", help="Output PDF file name"),
) -> None:
    generate_contract(template, json, output)
    with open(output, "rb") as pdf_file:
        checksum = generate_checksum(pdf_file.read())
    print(f"SHA256 checksum of '{output}': {checksum}")


if __name__ == "__main__":
    run(main)
