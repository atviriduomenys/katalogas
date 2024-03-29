import csv
import datetime
import json
import operator
import os
import sys
from functools import reduce
from itertools import chain
from itertools import groupby
from pathlib import Path
from typing import Any
from typing import Iterable
from typing import Iterator
from typing import NamedTuple
from typing import Optional
from typing import TextIO
from typing import TypedDict
from typing import Tuple
from typing import List
from typing import Dict

from typer import Argument
from typer import Option
from typer import run

import xlsxwriter
import requests
from pprintpp import pprint as pp


QUERY = '''\
query($endCursor: String) {
  repository(owner: "atviriduomenys", name: "%s") {
    issues(first: 100, after: $endCursor) {
      pageInfo {
        hasNextPage
        endCursor
      }
      nodes {
        id
        number
        state
        title
        body
        labels(first: 10) {
          nodes {
            name
            color
          }
        }
        milestone {
          number
          state
          title
        }
        repository {
          name
        }
        projectItems (first: 5) {
          nodes {
            project {
              number
              title
            }
            fieldValues(first: 10) {
              nodes {
                ... on ProjectV2ItemFieldIterationValue {
                  title
                  startDate
                  duration
                  field {
                    ... on ProjectV2IterationField {
                      name
                    }
                  }
                }
                ... on ProjectV2ItemFieldNumberValue {
                  number
                  field {
                    ... on ProjectV2Field {
                      name
                    }
                  }
                }
                ... on ProjectV2ItemFieldSingleSelectValue {
                  name
                  field {
                    ... on ProjectV2SingleSelectField {
                      name
                    }
                  }
                }
                ... on ProjectV2ItemFieldTextValue {
                  text
                  field {
                    ... on ProjectV2Field {
                      name
                    }
                  }
                }
              }
            }
          }
        }
      }
      totalCount
    }
  }
}
'''


class Card(TypedDict):
    id: str
    number: int
    title: str
    body: str
    state: str
    status: str
    repo: str
    sprint: str
    sprint_start: str
    sprint_duration: str
    estimate: int
    spent: int
    epic: str
    labels: str
    milestone: str


def main(
    files: List[str] = Argument(default=None, help=(
        "List of json files exported with `gh api graphql`."
    )),
    project: Optional[str] = Option(None, help="Project title."),
    export: Optional[Path] = Option(None, help="Export to CSV file."),
    level: int = Option(4, help=(
        "Show up to (0 - totals, 1 - repo, 2 - milestone, 3 - epic, "
        "4 - sprint, 5 - task)"
    )),
    order: bool = Option(False, help="Generate order table."),
    simple: bool = Option(False, help="Generate simple table."),
    query: str = Option('', '-q', '--query', help="Outpur GraphQL query."),
):
    if query:
        print(QUERY % query)
        return

    cards = _extract_cards(files)

    if project is None:
        _list_projects(cards)
        return

    cards = _transform_cards(cards, project)
    cards = list(cards)
    if export:
        if order:
            if export.is_dir():
                _cards_to_xlsx_order(export, cards)
            else:
                raise ValueError("Export path must be a directory.")
        elif simple:
            if export.name == '-':
                _cards_to_simple_csv(sys.stdout, cards)
            elif export.suffix == '.csv':
                with export.open('w') as f:
                    _cards_to_simple_csv(f, cards)
            else:
                raise NotImplementedError(
                    f"Don't know how to export to {export.suffix}"
                )
        else:
            if export.name == '-':
                _cards_to_csv(sys.stdout, cards, level)
            elif export.suffix == '.csv':
                with export.open('w') as f:
                    _cards_to_csv(f, cards, level)
            else:
                raise NotImplementedError(
                    f"Don't know how to export to {export.suffix}"
                )
    else:
        _cards_to_ascii(cards, level)

RawCards = Iterable[Dict[str, Any]]

def _list_projects(cards: RawCards) -> None:
    print("Choose project:")
    seen = set()
    for card in cards:
        if 'projectItems' not in card:
            pp(card)
        for project in card['projectItems']['nodes']:
            title = project['project']['title']
            if title not in seen:
                print(f"- \"{title}\"")
                seen.add(title)


def _extract_cards(
    files: List[str],
) -> Iterator[Card]:
    for file in files:
        with open(file) as f:
            for line in f:
                yield json.loads(line)


def _transform_cards(
    cards: Iterable[Card],
    project_title: Optional[str],
) -> Iterator[Card]:
    for card in cards:
        row = {
            'id': None,
            'number': None,
            'title': None,
            'body': '',
            'state': None,
            'status': None,
            'repo': None,
            'sprint': None,
            'estimate': None,
            'spent': None,
            'epic': None,
            'labels': [],
            'milestone': None,
        }

        row['id'] = card['id']
        row['number'] = card['number']
        row['title'] = card['title']
        row['body'] = card['body']
        row['state'] = card['state']
        row['repo'] = card['repository']['name']
        row['labels'] = [
            label['name']
            for label in card['labels']['nodes']
        ]
        if card['milestone']:
            row['milestone'] = card['milestone']['title']

        for project in card['projectItems']['nodes']:
            if (
                project_title is not None and
                project['project']['title'] != project_title
            ):
                continue

            row['project'] = project['project']['title']

            data = {}
            for field in project['fieldValues']['nodes']:
                if 'field' in field:
                    name = field['field']['name']
                    data[name] = field

            row['status'] = data.get('Status', {}).get('name')
            row['sprint'] = data.get('Iteration', {}).get('title')
            row['sprint_start'] = data.get('Iteration', {}).get('startDate')
            row['sprint_duration'] = _toint(
                data.get('Iteration', {}).get('duration')
            )
            row['estimate'] = _toint(data.get('Estimate', {}).get('number'))
            row['spent'] = _toint(data.get('Spent', {}).get('number'))
            row['epic'] = data.get('Epic', {}).get('text')

            if 'epic' not in row['labels'] and row['spent'] is None:
                row['spent'] = row['estimate']

            if row['epic']:
                row['epic'] = _toint(row['epic'].strip('#'))

            if row['title'] is None:
                row['title'] = data.get('Title')

            yield row


def _toint(v: str | int | None) -> int | None:
    if isinstance(v, int):
        return v
    return int(v) if v else None


class _Option(TypedDict):
    id: str
    name: str
    name_html: str


class _OptionSettings(TypedDict):
    options: list[_Option]


def _get_option(value: str, settings: _OptionSettings) -> str:
    options = {
        opt['id']: opt['name']
        for opt in settings['options']
    }
    if value in options:
        return options[value]


class _Iteration(TypedDict):
    id: str
    start_date: int
    duration: int
    title: str
    title_html: str


class _IterationConfiguration(TypedDict):
    start_day: int
    duration: int
    iterations: list[_Iteration]
    completed_iterations: list[_Iteration]


class _IterationSettings(TypedDict):
    configuration: _IterationConfiguration


def _get_iteration(value: str, settings: _IterationSettings) -> _Iteration:
    iterations = (
        settings['configuration'].get('iterations', []) +
        settings['configuration'].get('completed_iterations', [])
    )
    for it in iterations:
        if it['id'] == value:
            return it


def _cards_to_csv__old(f: TextIO, cards: Iterable[Card]) -> None:
    header = [
        'id',
        'number',
        'title',
        'state',
        'status',
        'repo',
        'sprint',
        'sprint_start',
        'sprint_duration',
        'estimate',
        'spent',
        'epic',
        'labels',
        'milestone',
    ]
    writer = csv.DictWriter(f, header)
    writer.writeheader()
    for card in cards:
        row = {
            **card,
            'labels': ', '.join(card['labels'])
        }
        writer.writerow(row)


def _cards_to_csv(f: TextIO, cards: Iterable[Card], level: int = 4) -> None:
    cols = [
        'total',
        'repository',
        'milestone',
        'epic',
        'sprint',
        'task',
    ]
    titles = {col: '' for col in cols}
    header = [
        'epic.estimate',
        'epic.spent',
        'epic.%',
        'task.estimate',
        'task.spent',
        'task.%',
        '#',
        'level',
    ] + cols + ['body']
    writer = csv.DictWriter(f, header)
    writer.writeheader()
    for row in _summary_totals(cards):
        titles = {
            # col: _get_csv_title(row, col, _level, titles)
            col: (
                _get_csv_title(row, col, _level, titles)
                if _level == row.level else ''
            )
            for _level, col in enumerate(cols)
        }
        if row.level - 1 > level:
            continue
        row = {
            'epic.estimate': row.estimate.epic,
            'epic.spent': row.spent.epic,
            'epic.%': _get_epic_spent_percent(row),
            'task.estimate': row.estimate.task,
            'task.spent': row.spent.task,
            'task.%': _get_task_spent_percent(row),
            '#': row.number,
            'level': row.level,
            **titles,
            'body': row.body,
        }
        writer.writerow(row)


def _get_csv_title(row, col, level, titles):
    if row.level == level:
        return row.title
    elif row.level > level:
        return titles[col]
    else:
        return ''


def _cards_to_xlsx_order(
    path: Path,
    cards: Iterable[Card],
) -> None:
    cards = list(cards)

    titles = {
        card['number']: card['title']
        for card in cards
    }

    cards = [card for card in cards if card['status'] == 'Done']

    cards = sorted(cards, key=_get_sprint_num)

    repos = {
        'katalogas': 'Katalogo tobulinimas',
        'saugykla': 'Saugyklos tobulinimas',
    }

    formats = {
        't': {
            'align': 'center',
            'valign': 'vcenter',
        },
        'd0': {
            'num_format': 'yyyy-mm-dd',
        },
        'd': {
            'align': 'left',
            'border': 1,
            'num_format': 'yyyy-mm-dd',
        },
        'h': {
            'border': 1,
            'bg_color': '#d9d9d9',
            'valign': 'vcenter',
            'text_wrap': True,
        },
        'hb': {
            'border': 1,
            'bg_color': '#d9d9d9',
            'bold': True,
            'valign': 'vcenter',
            'text_wrap': True,
        },
        'hc': {
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
            'text_wrap': True,
        },
        'c': {
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
            'text_wrap': True,
        },
        'rb': {
            'border': 1,
            'bold': True,
            'align': 'right',
            'valign': 'vcenter',
            'text_wrap': True,
        },
        'cb': {
            'border': 1,
            'bold': True,
            'align': 'center',
            'valign': 'vcenter',
            'text_wrap': True,
        },
        'b': {
            'border': 1,
            'bold': True,
            'valign': 'vcenter',
            'text_wrap': True,
        },
        '': {
            'border': 1,
            'valign': 'vcenter',
            'text_wrap': True,
        },
    }

    wbtypes = [
        # Užduotims
        {
            'title': [
                'ATVIRŲ DUOMENŲ SĄVOKŲ ŽINYNO MODULIO SUKŪRIMAS IR '
                'ATVIRŲ DUOMENŲ PORTALO (ADP) PLĖTROS SUKURIANT '
                'INTEGRACINES SĄSAJAS',
                'PASLAUGŲ VIEŠOJO PIRKIMO–PARDAVIMO SUTARTIES '
                'NR. 6F-30(2022)',
                'UŽDUOTIS PASLAUGŲ SUTEIKIMUI',
            ],
            'date': lambda s, e: s - datetime.timedelta(days=2),
            'filename': 'S{sprint:02}U_{date:%Y-%m-%d}.xlsx',
            'A1': 'SUDERINO',
            'B1': '',
            'A2': 'Užsakovo atstovas - projekto vadovas:',
            'B2': 'Paslaugų teikėjo atstovas - projekto vadovas',
            'A3': 'Julius Belickas',
            'B3': 'Ernestas Vyšniauskas',
            'body': 1,
        },
        # Aktams
        {
            'title': [
                'ATVIRŲ DUOMENŲ SĄVOKŲ ŽINYNO MODULIO SUKŪRIMAS IR '
                'ATVIRŲ DUOMENŲ PORTALO (ADP) PLĖTROS SUKURIANT '
                'INTEGRACINES SĄSAJAS',
                'PASLAUGŲ VIEŠOJO PIRKIMO–PARDAVIMO SUTARTIES '
                'NR. 6F-30(2022)',
                'UŽDUOČIŲ PRIĖMIMO AKTAS',
            ],
            'date': lambda s, e: e + datetime.timedelta(days=2),
            'filename': 'S{sprint:02}A_{date:%Y-%m-%d}.xlsx',
            'A1': 'ĮVYKDė IR PATEIKĖ:',
            'B1': 'PATIKRINO IR PRIĖMĖ',
            'A2': 'Paslaugų teikėjo atstovas - projekto vadovas',
            'B2': 'Užsakovo atstovas - projekto vadovas:',
            'A3': 'Ernestas Vyšniauskas',
            'B3': 'Julius Belickas',
            'body': 0,
        },
    ]

    for wbtype in wbtypes:
        sprints = groupby(cards, key=_get_sprint_num)
        for sprint, tasks in sprints:
            task = next(tasks)
            tasks = chain([task], tasks)
            start, end = _get_sprint_dates(task)
            date = wbtype['date'](start, end)

            wb = xlsxwriter.Workbook(
                path / wbtype['filename'].format(
                    date=date,
                    sprint=sprint,
                )
            )
            ws = wb.add_worksheet()

            ws.set_column(0, 0, 30)
            ws.set_column(1, 1, 20)
            ws.set_column(2, 2, 80)

            fmt = {k: wb.add_format(v) for k, v in formats.items()}

            r = 1
            ws.merge_range(
                f'A{r}:C{r}',
                '\n'.join(wbtype['title']),
                fmt['t'],
            )
            ws.set_row(r-1, 60)

            r += 1
            ws.write(f'C{r}', date, fmt['d0'])

            r += 1
            ws.write(f'A{r}', 'Etapas', fmt['hb'])
            ws.write(f'B{r}', 'Pirmas', fmt['c'])

            r += 1
            ws.write(f'A{r}', 'Iteracija', fmt['hb'])
            ws.write(f'B{r}', sprint, fmt['c'])

            r += 1
            ws.merge_range(
                f'A{r}:A{r+1}',
                'Iteracijos vykdymo periodas',
                fmt['b'],
            )
            ws.write(f'B{r}', 'Pradžia', fmt[''])
            ws.write(f'C{r}', 'Pabaiga', fmt[''])

            r += 1
            ws.write(f'B{r}', start, fmt['d'])
            ws.write(f'C{r}', end, fmt['d'])

            r += 1
            ws.write(f'A{r}', 'Užduoties pavadinimas', fmt['hb'])
            ws.write(f'B{r}', 'Laiko sąnaudos, val.', fmt['hb'])
            ws.write(f'C{r}', 'Užduoties aprašymas', fmt['hb'])

            tnum = 1
            hours = 0
            epics = sorted(tasks, key=_by_epic_group)
            epics = groupby(epics, key=_by_epic_group)
            for epic, tasks in epics:
                task = next(tasks)
                tasks = chain([task], tasks)

                r += 1
                repo = repos.get(task['repo'], task['repo'])
                epic = titles.get(epic, '(no epic)')
                if epic.startswith("Kitos "):
                    ws.merge_range(
                        f'A{r}:C{r}',
                        "Kitų,  pirkimo specifikacijoje neįvardintų "
                        "Katalogo ir Saugyklos plėtros ir  patobulinimų, "
                        "kurių nebuvo galima numatyti arba apibrėžti "
                        "specifikavimo metu, paslaugų teikimas",
                        fmt['b'],
                    )
                else:
                    ws.merge_range(f'A{r}:C{r}', f"{repo}: {epic}", fmt['b'])

                for task in tasks:
                    if '---' in task['body']:
                        body = task['body'].rsplit('---', 1)[wbtype['body']]
                    else:
                        body = task['body']

                    title = task['title']

                    r += 1
                    ws.write(f'A{r}', f"{tnum}. {title}", fmt[''])
                    ws.write(f'B{r}', task['spent'], fmt['c'])
                    ws.write(f'C{r}', body, fmt[''])

                    tnum += 1
                    hours += task['spent']

            r += 1
            ws.write(f'A{r}', 'Viso val.:', fmt['rb'])
            ws.write(f'B{r}', hours, fmt['cb'])

            r += 3
            ws.write(f'A{r}', wbtype['A1'])

            r += 2
            ws.write(f'A{r}', wbtype['A2'])
            ws.write(f'C{r}', wbtype['B2'])

            r += 1
            ws.write(f'A{r}', wbtype['A3'])
            ws.write(f'C{r}', wbtype['B3'])

            wb.close()


def _get_sprint_num(card: Card) -> int:
    title = card['sprint']
    if title == '(no sprint)':
        return 0
    else:
        _, num = title.split()
        return int(num)


def _get_sprint_dates(card: Card) -> Tuple[datetime.date, datetime.date]:
    if card['sprint_start']:
        start = datetime.date.fromisoformat(card['sprint_start'])
        duration = card['sprint_duration']
        end = start + datetime.timedelta(days=duration)
    else:
        start = '-'
        end = '-'
    return start, end


class Hours(NamedTuple):
    epic: int | None
    task: int | None


class Summary(NamedTuple):
    number: int | None
    title: str | None
    body: str | None
    level: int
    estimate: Hours
    spent: Hours


def _ascii_header():
    print()
    print('+------ EPIC --------+-------- TASK -------+-----+-----------------------------------------------+')
    print('| Estim : Spent    % | Estim : Spent     % |   # | Repository > Milestone > Epic > Sprint > Task |')
    print('+--------------------+---------------------+-----+-----------------------------------------------+')


def _cards_to_ascii(cards: list[Card], level: int = 4) -> None:
    _ascii_header()
    for row in _summary_totals(cards):
        if row.level - 1 > level:
            continue
        indent = '  ' * row.level
        print(
            '|',
            f'{_cell(row.estimate.epic):>6}  ',
            f'{_cell(row.spent.epic):>6}  ',
            f'{_cell(_get_epic_spent_percent(row)):>3} |',
            f'{_cell(row.estimate.task):>6}  ',
            f'{_cell(row.spent.task):>6}  ',
            f'{_cell(_get_task_spent_percent(row)):>4} |',
            f'{_cell(row.number):>4} | ',
            f'{indent}{_cell(row.title)}',
            sep='',
        )


def _get_epic_spent_percent(row: Card) -> int | None:
    if (
        row.estimate.epic is not None and
        row.spent.epic is not None and
        row.estimate.epic > 0
    ):
        return int(row.spent.epic / row.estimate.epic * 100)


def _get_task_spent_percent(row: Card) -> int | None:
    if (
        row.estimate.task is not None and
        row.estimate.task > 0 and
        row.spent.task is not None and
        row.spent.task > 0
    ):
        return int(row.spent.task / row.estimate.task * 100)


def _cell(value: Any | None) -> str:
    if value is None:
        return '-'
    else:
        return value


def _summary_totals(cards: list[Card]) -> Iterator[Summary]:
    rows = list(_summary_by_repo(cards))
    yield _sum(rows, number=None, title='TOTAL', level=0)
    yield from rows


def _by_repo(card: Card):
    return card['repo'] or '(no repo)'


def _summary_by_repo(cards: list[Card]) -> Iterator[Summary]:
    cards = sorted(cards, key=_by_repo)
    groups = groupby(cards, key=_by_repo)
    for repo, rows in groups:
        if repo == '(no repo)':
            continue
        rows = list(_summary_by_milestone(list(rows)))
        yield _sum(rows, number=None, title=repo.title(), level=1)
        yield from rows


def _by_milestone(card: Card):
    return card['milestone'] or '(no milestone)'


def _by_epic_sort(card: Card):
    return card['epic'] or 0


def _by_epic_group(card: Card):
    return card['epic'] or 0


def _summary_by_milestone(cards: list[Card]) -> Iterator[Summary]:
    tasks = [
        card
        for card in cards
        if 'epic' not in card['labels']
    ]
    tasks = sorted(tasks, key=_by_epic_sort)
    tasks = {
        epic: list(tasks)
        for epic, tasks in groupby(tasks, key=_by_epic_group)
    }

    epics = [
        card
        for card in cards
        if 'epic' in card['labels']
    ]
    epics = sorted(epics, key=_by_milestone)
    groups = groupby(epics, key=_by_milestone)
    for milestone, rows in groups:
        rows = list(_summary_by_epic(rows, tasks))
        yield _sum(rows, number=None, title=milestone, level=2)
        yield from rows

    epics = {epic['number'] for epic in epics}
    tasks = [
        epic_tasks
        for epic, epic_tasks in tasks.items()
        if epic not in epics
    ]
    tasks = reduce(operator.add, tasks, [])
    rows = list(_summary_by_sprint(tasks))
    yield _sum(rows, number=None, title='(no epic)', level=3)._replace(level=2)
    yield from rows


def _summary_by_epic(
    epics: list[Card],
    tasks: dict[
        str,  # epic
        list[Card],
    ],
) -> Iterator[Summary]:
    for epic in epics:
        rows = tasks.get(epic['number'], [])
        rows = list(_summary_by_sprint(rows))
        yield _sum(
            rows,
            number=epic['number'],
            title=epic['title'],
            level=3,
            estimate=epic['estimate'],
            spent=epic['spent'],
        )
        yield from rows


def _by_sprint(card: Card):
    return card['sprint'] or '(no sprint)'


def _summary_by_sprint(tasks: list[Card]) -> Iterator[Summary]:
    sprints = {
        _by_sprint(task): task
        for task in tasks
    }
    tasks = sorted(tasks, key=_by_sprint)
    groups = groupby(tasks, key=_by_sprint)
    for sprint, rows in groups:
        rows = list(_summary_by_task(rows))
        if sprints[sprint]['sprint_start']:
            start = sprints[sprint]['sprint_start']
            duration = sprints[sprint]['sprint_duration']
            title = f'{sprint} ({start}, {duration} days)'
        else:
            title = sprint
        yield _sum(rows, number=None, title=title, level=4)
        yield from rows


def _task_sort_key(task: Card) -> str:
    return task['title']


def _summary_by_task(tasks: list[Card]) -> Iterator[Summary]:
    for task in sorted(tasks, key=_task_sort_key):
        if 'epic' in task['labels']:
            continue
        yield Summary(
            number=task['number'],
            title=task['title'],
            body=task['body'],
            level=5,
            estimate=Hours(
                epic=None,
                task=task['estimate']
            ),
            spent=Hours(
                epic=None,
                task=task['spent']
            ),
        )


def _sum(
    rows: list[Summary],
    *,
    level: int,
    estimate: int | None = 0,
    spent: int | None = 0,
    body: str = '',
    **kwargs,
) -> Summary:
    estimate_epic = estimate or 0
    estimate_task = 0
    spent_epic = spent or 0
    spent_task = 0
    for row in rows:
        if row.level == level + 1:
            estimate_epic += row.estimate.epic or 0
            estimate_task += row.estimate.task or 0
            spent_epic += row.spent.epic or 0
            spent_task += row.spent.task or 0
    return Summary(
        estimate=Hours(
            epic=estimate_epic,
            task=estimate_task
        ),
        spent=Hours(
            epic=spent_epic,
            task=spent_task
        ),
        level=level,
        body=body,
        **kwargs
    )



def _cards_to_simple_csv(f: TextIO, cards: Iterable[Card]) -> None:
    header = [
        'repo',
        'epic #',
        'task #',
        'task',
        'sprint',
        'estimate',
        'spent',
        'status',
        'state',
    ]
    writer = csv.DictWriter(f, header)
    writer.writeheader()
    for card in sorted(cards, key=lambda c: (
        (c['sprint_start'] or ''),
        c['repo'],
        f"{(c['epic'] or 0):04}",
        c['title'],
    )):
        if 'epic' in card['labels']:
            continue
        row = {
            'repo': card['repo'],
            'epic #': card['epic'],
            'task #': card['number'],
            'task': card['title'],
            'sprint': (
                f"{card['sprint']} ({card['sprint_start']})"
                if card['sprint'] else '-'
            ),
            'estimate': card['estimate'],
            'spent': card['spent'],
            'status': card['status'],
            'state': card['state'],
        }
        writer.writerow(row)


if __name__ == '__main__':
    run(main)
