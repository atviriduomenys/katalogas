import csv
import json
import operator
import os
import sys
from functools import reduce
from itertools import groupby
from pathlib import Path
from typing import Any
from typing import Iterable
from typing import Iterator
from typing import NamedTuple
from typing import Optional
from typing import TextIO
from typing import TypedDict

from typer import Argument
from typer import Option
from typer import run

import requests
from pprintpp import pprint as pp


class Card(TypedDict):
    id: str
    number: int
    title: str
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
    token: str = Argument(..., help="https://github.com/settings/tokens"),
    project_id: Optional[str] = Argument(None, help=(
        "Project id (listed if not given)"
    )),
    update: Optional[bool] = Option(False, help="Update cached data."),
    export: Optional[Path] = Option(None, help="Export to CSV file."),
    level: int = Option(4, help=(
        "Show up to (0 - totals, 1 - repo, 2 - milestone, 3 - epic, "
        "4 - sprint, 5 - task)"
    ))
):
    session = requests.Session()
    session.headers['Authorization'] = f'Bearer {token}'

    if project_id is None:
        _list_projects(session)
        exit()

    cards = _extract_cached_cards(session, project_id, update=update)
    cards = _transform_cards(cards)
    cards = list(cards)
    if export:
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


def _list_projects(session: requests.Session) -> None:
    pp(session.post('https://api.github.com/graphql', json={'query': '''\
    query{
        organization(login: "atviriduomenys"){
          projectsNext(first: 10) {
            nodes {
              id
              title
            }
          }
        }
    }
    '''}).json())


def _extract_cached_cards(
    session: requests.Session,
    project_id: str,
    *,
    update: bool = False,
) -> Iterator[Card]:
    cache_dir = os.getenv('XDG_CACHE_HOME', os.path.expanduser('~/.cache'))
    cache_dir = Path(cache_dir) / 'vitrina'
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / 'github-cards.jsonl'

    if update or not cache_file.exists():
        cards = _extract_cards(session, project_id)
        with cache_file.open('w') as f:
            for card in cards:
                line = json.dumps(card)
                f.write(line + '\n')

    with cache_file.open() as f:
        for line in f:
            card = json.loads(line.strip())
            yield card


def _extract_cards(
    session: requests.Session,
    project_id: str,
) -> Iterator[Card]:
    loop = True
    cursor = None
    while loop:
        resp = session.post('https://api.github.com/graphql', json={
            'query': '''\
             query cards($project: ID!, $cursor: String) {
              node(id: $project) {
                id
                ... on ProjectNext {
                  id
                  title
                  items(first: 10, after: $cursor) {
                    nodes {
                      content {
                        ... on Issue {
                          id
                          title
                          number
                          state
                          repository {
                            name
                          }
                          milestone {
                            title
                          }
                          labels(first: 10) {
                            nodes {
                              name
                            }
                          }
                        }
                      }
                      title
                      fieldValues(first: 10) {
                        nodes {
                          value
                          projectField {
                            name
                            settings
                          }
                        }
                      }
                    }
                    edges {
                      cursor
                    }
                    pageInfo {
                      hasNextPage
                    }
                  }
                }
              }
            }
            ''',
            'variables': {
                'project': project_id,
                'cursor': cursor,
            }
        })

        resp.raise_for_status()
        project = resp.json()

        if project['data']['node'] is None:
            pp(project['errors'])
            exit()

        if project['data']['node']['items']['edges']:
            cursor = project['data']['node']['items']['edges'][-1]['cursor']
        else:
            cursor = None

        loop = project['data']['node']['items']['pageInfo']['hasNextPage']

        for card in project['data']['node']['items']['nodes']:
            yield card


def _transform_cards(cards: Iterable[Card]) -> Iterator[Card]:
    for card in cards:
        row = {
            'id': None,
            'number': None,
            'title': None,
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

        if card['content']:
            row['id'] = card['content']['id']
            row['number'] = card['content']['number']
            row['title'] = card['content']['title']
            row['state'] = card['content']['state']
            row['repo'] = card['content']['repository']['name']
            row['labels'] = [
                label['name']
                for label in card['content']['labels']['nodes']
            ]
            if card['content']['milestone']:
                row['milestone'] = card['content']['milestone']['title']

        data = {}
        for field in card['fieldValues']['nodes']:
            name = field['projectField']['name']
            value = field['value']
            if 'settings' in field['projectField']:
                settings = json.loads(field['projectField']['settings'])
                if settings:
                    if 'options' in settings:
                        value = _get_option(value, settings)
                    elif 'configuration' in settings:
                        value = _get_iteration(value, settings)
            data[name] = value

        row['status'] = data.get('Status')
        row['sprint'] = data.get('Iteration', {}).get('title')
        row['sprint_start'] = data.get('Iteration', {}).get('start_date')
        row['sprint_duration'] = _toint(
            data.
            get('Iteration', {}).
            get('duration')
        )
        row['estimate'] = _toint(data.get('Estimate'))
        row['spent'] = _toint(data.get('Time spent'))
        row['epic'] = data.get('Epic')

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
    header = [
        'epic.estimate',
        'epic.spent',
        'epic.%',
        'task.estimate',
        'task.spent',
        'task.%',
        '#',
        'level',
        'title',
    ]
    writer = csv.DictWriter(f, header)
    writer.writeheader()
    for row in _summary_totals(cards):
        if row.level - 1 > level:
            continue
        writer.writerow({
            'epic.estimate': row.estimate.epic,
            'epic.spent': row.spent.epic,
            'epic.%': _get_epic_spent_percent(row),
            'task.estimate': row.estimate.task,
            'task.spent': row.spent.task,
            'task.%': _get_task_spent_percent(row),
            '#': row.number,
            'level': row.level,
            'title': row.title,
        })


class Hours(NamedTuple):
    epic: int | None
    task: int | None


class Summary(NamedTuple):
    number: int | None
    title: str | None
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
        **kwargs
    )


if __name__ == '__main__':
    run(main)
