import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "vitrina.settings")
django.setup()

import json
import requests
from datetime import date, datetime
from typer import run, Option
from vitrina.tasks.models import Holiday


def main(
    date_from: str = Option(None, help=(
        "Date from when holidays should be added"
    )),
    date_to: str = Option(None, help=(
        "Date to when holidays should be added"
    ))
):
    """
    Add holiday dates to Holiday table
    """
    if not date_from:
        date_from = date.today()
    if not date_to:
        if isinstance(date_from, str):
            date_from = datetime.strptime(date_from, "%Y-%m-%d").date()
        date_to = date_from.replace(date_from.year + 1)
    res = requests.get("https://api.vilnius.lt/api/calendar/get-non-working-days", params={
        "date_from": date_from,
        "date_to": date_to
    })
    data = json.loads(res.content)
    for holiday in data.get('nonWorkingDates', []):
        if not Holiday.objects.filter(date=holiday['date'], title=holiday['name']):
            Holiday.objects.create(
                date=holiday['date'],
                title=holiday['name']
            )


if __name__ == '__main__':
    run(main)
