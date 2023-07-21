import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "vitrina.settings")
django.setup()

import json
import requests
from tqdm import tqdm
from typer import run

from vitrina.orgs.models import Organization


def main():
    """
    Import organizations.
    """

    codes = [110, 930, 950, 130, 111, 951]
    query = '|'.join([f'forma.kodas={code}' for code in codes])
    res = requests.get(f"https://get.data.gov.lt/datasets/gov/rc/jar/iregistruoti/JuridinisAsmuo?{query}")
    data = json.loads(res.content)
    organizations = data.get('_data', [])

    pbar = tqdm("Importing organizations", total=(len(organizations)))
    Organization.fix_tree(fix_paths=True)
    with pbar:
        for org in organizations:
            title = org.get('ja_pavadinimas')
            code = org.get('ja_kodas')
            address = org.get('pilnas_adresas')
            if code and not Organization.objects.filter(company_code=org.get('ja_kodas')):
                Organization.add_root(
                    title=title,
                    company_code=code,
                    address=address,
                )
            pbar.update(1)


if __name__ == '__main__':
    run(main)
