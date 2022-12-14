import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "vitrina.settings")
django.setup()

import json
import requests
from typer import run, Argument
from vitrina.tasks.models import Holiday


def main(
    date_from: str = Argument(..., help=(
        "Date from when holidays should be added"
    )),
    date_to: str = Argument(..., help=(
        "Date to when holidays should be added"
    ))
):
    """
    Add holiday dates to Holiday table
    """
    res = requests.get("https://api.vilnius.lt/api/calendar/get-non-working-days", params={
        "date_from": date_from,
        "date_to": date_to
    })
    data = json.loads(res.content)
    for holiday in data.get('nonWorkingDates', []):
        if not Holiday.objects.filter(date=holiday['date']):
            Holiday.objects.create(
                date=holiday['date']
            )


if __name__ == '__main__':
    run(main)
