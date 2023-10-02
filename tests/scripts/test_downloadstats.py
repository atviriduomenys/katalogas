import uuid
import json
from pathlib import Path
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

from typer.testing import CliRunner
from typer import Typer

from scripts.downloadstats import main
from scripts.downloadstats import find_transactions


@pytest.fixture()
def patcher():
    with patch('requests.Session') as mock:
        yield mock


def flatten(entries: list[list[str]]):
    return [
        line
        for lines in entries
        for line in lines
    ]


def run(path: Path, entries: list[list[str]]):
    log_file = path / 'accesslog.json'
    log_file.write_text('\n'.join(flatten(entries)))

    config_file = path / 'config.json'
    config_file.write_text(json.dumps({
        "auth": {
            "secret": "SECRETKEY",
        },
        "bots": [
            "SemrushBot",
        ],
    }))

    state_file = path / 'state.json'

    app = Typer()
    app.command()(main)
    runner = CliRunner()
    res = runner.invoke(
        app,
        [
            'get.data.gov.lt',
            str(log_file),
            '--config-file', str(config_file),
            '--state-file', str(state_file),
        ],
        env={
            'HOME': str(path),
        },
        catch_exceptions=False,
    )
    return res


def log(
    day='1',
    txn=None,
    objects=1,
    action='getall',
    format='html',
    agent='HTTPie/2.6.0',
    request=True,
    response=True,
):
    messages = []
    if txn is None:
        txn = str(uuid.uuid4())
    if request:
        messages.append(
            '{'
            f'"time": "2000-01-0{day}T00:00:00.000000+00:00", '
            '"pid": 1, '
            '"type": "request", '
            '"method": "GET", '
            f'"action": "{action}", '
            '"model": "datasets/example/City", '
            f'"txn": "{txn}", '
            f'"format": "{format}", '
            '"url": "http://example.com/datasets/example/City", '
            '"client": "default", '
            f'"agent": "{agent}"'
            '}'

        )
    if response:
        messages.append(
            '{'
            f'"time": "2000-01-0{day}T00:00:00.000000+00:00", '
            '"type": "response", '
            '"delta": 0.019, '
            '"memory": 0, '
            f'"objects": {objects}, '
            f'"txn": "{txn}"'
            '}'
        )
    return messages


def test_downloadstats(patcher: MagicMock, tmp_path: Path):
    res = run(tmp_path, [
        log(day='1'),
        log(day='2'),
        log(day='2', objects=5),
        log(day='2'),
        log(day='2', agent='Mozilla/5.0 (compatible; SemrushBot)'),
    ])

    assert res.exit_code == 0

    log_file = tmp_path / 'accesslog.json'
    logbytes = log_file.read_bytes()

    session = patcher.return_value

    # Only one request per day must be made
    assert session.post.call_count == 2
    assert session.post.call_args.kwargs['data'] == {
        'format': 'html',
        'model': 'datasets/example/City',
        'objects': 7,
        'requests': 3,
        'source': 'get.data.gov.lt',
        'time': '2000-01-02 00:00:00',
    }

    # Authorization must be used
    assert session.post.call_args.kwargs['headers'] == {
        'Authorization': 'ApiKey SECRETKEY',
    }

    state_file = tmp_path / 'state.json'
    assert json.loads(state_file.read_text()) == {
        'files': {
            str(tmp_path / 'accesslog.json'): {
                # Store last seen file size
                'size': len(logbytes),
                # And offset in the file
                'offset': len(logbytes),
            }
        },
        # Store all seen agents, this information will be used, to
        # update bot list in config file.
        'agents': {
            'HTTPie': 4,
            'SemrushBot': 1,
        },
    }


def test_find_transactions(tmp_path: Path):
    name = 'get.data.gov.lt'
    lines = flatten([
        log(day='1'),
        log(day='2'),
        log(day='3', txn='1', response=False),
    ])
    endpoint_url = 'endpoint_url'
    session = MagicMock()
    final_stats = {}
    bot_status_file = tmp_path / 'state.json'
    find_transactions(
        name,
        lines,
        endpoint_url,
        session,
        final_stats,
        bot_status_file,
    )

    # Only one request per day must be made
    assert session.post.call_count == 2
    assert session.post.call_args.kwargs['data'] == {
        'format': 'unknown',
        'model': 'datasets/example/City',
        'objects': 1,
        'requests': 1,
        'source': 'get.data.gov.lt',
        'time': '2000-01-02 00:00:00',
    }

    assert json.loads(bot_status_file.read_text()) == {
        'agents': {
            'HTTPie': 4,
            'SemrushBot': 1,
        },
    }

    # Test what would happen if request and response was split between batches
    lines = flatten([
        log(day='3', txn='1', request=False),
    ])
    find_transactions(
        name,
        lines,
        endpoint_url,
        session,
        final_stats,
        bot_status_file,
    )

    assert session.post.call_count == 3
    assert session.post.call_args.kwargs['data'] == {
        'format': 'unknown',
        'model': 'datasets/example/City',
        'objects': 1,
        'requests': 1,
        'source': 'get.data.gov.lt',
        'time': '2000-01-03 00:00:00',
    }
