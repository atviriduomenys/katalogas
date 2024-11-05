import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "vitrina.settings")
django.setup()

import requests
from tqdm import tqdm
from typer import run
from vitrina.datasets.models import Dataset
from vitrina.settings import TRANSLATION_CLIENT_ID


def main():
    """
    Translate dataset title and description
    """

    pbar = tqdm("Translating datasets", total=(
        Dataset.objects.count()
    ))
    count = 0

    for dataset in Dataset.objects.all():
        if (
            not dataset.has_translation(language_code='en') or
            (dataset.lt_title() and not dataset.en_title()) or
            (dataset.lt_description() and not dataset.en_description())
        ):
            lt_title = dataset.lt_title()
            lt_description = dataset.lt_description()

            if not dataset.has_translation(language_code='en'):
                dataset.create_translation(language_code='en')
            dataset.set_current_language('en')

            if not dataset.en_title():
                response_title = requests.post(
                    "https://vertimas.vu.lt/ws/service.svc/json/Translate",
                    json={
                        "appId": "",
                        "systemID": "smt-8abc06a7-09dc-405c-bd29-580edc74eb05",
                        "text": lt_title,
                        "options": ""
                    },
                    headers={
                        "client-id": TRANSLATION_CLIENT_ID,
                        "Content-Type": "application/json; charset=utf-8"
                    },
                )
                en_title = response_title.json()
                dataset.title = en_title

            if not dataset.en_description():
                response_desc = requests.post(
                    "https://vertimas.vu.lt/ws/service.svc/json/Translate",
                    json={
                        "appId": "",
                        "systemID": "smt-8abc06a7-09dc-405c-bd29-580edc74eb05",
                        "text": lt_description,
                        "options": ""
                    },
                    headers={
                        "client-id": TRANSLATION_CLIENT_ID,
                        "Content-Type": "application/json; charset=utf-8"
                    },
                )
                en_description = response_desc.json()
                dataset.description = en_description

            dataset.save()
            count += 1

        pbar.update(1)

    print(f'Updated dataset translations: {count}')


if __name__ == '__main__':
    run(main)
