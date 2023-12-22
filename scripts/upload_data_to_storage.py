import json
import os
import urllib.parse
import datetime

import django
import requests

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "vitrina.settings")
django.setup()

import csv
import hashlib
import subprocess
import yaml
from pathlib import Path
from typer import run, Option

from django.conf import settings


def run_spinta_command(base_dir, resource, target, session, no_create_task, state, state_file_path):
    env = os.environ.copy()
    env['SPINTA_CONFIG'] = str(base_dir / "config.yml")

    result = subprocess.run(
        [settings.SPINTA_EXECUTABLE, '--tb=native', "push", str(Path(base_dir) / "manifest.csv"),
         "--no-progress-bar", "-o", settings.SPINTA_SERVER_NAME],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        text=True
    )
    if result.returncode != 0:
        error_text = handle_error(result.stderr)
        if not no_create_task:
            task_url = urllib.parse.urljoin(target, f'partner/api/1/tasks/{resource["id"]}/')
            response = session.post(task_url, data={'error_text': error_text,
                                                    'title': 'Klaida keliant duomenis į saugyklą',
                                                    'app_name': 'vitrina_resources',
                                                    'model_name': 'DatasetDistribution',
                                                    'task_type': 'ERROR_DISTRIBUTION',
                                                    'org_id': resource["organization_id"]})
            response_json = response.json()
            print(response_json)
        else:
            print(error_text)
    else:
        url_text = f'partner/api/1/distribution/id/{resource["id"]}/create-distribution/'
        create_url = urllib.parse.urljoin(target, url_text)
        response = session.post(create_url, data={'dataset_id': resource["dataset_id"]})
        response_json = response.json()
        state['last_update'] = datetime.datetime.now().isoformat()
        with open(state_file_path, 'w') as f:
            json.dump(state, f)
        print(response_json)


def handle_error(stderr):
    lines = stderr.splitlines()
    start = next((i for i, line in enumerate(lines) if line.startswith('Traceback')), None)
    if start is not None:
        end = next((i for i, line in enumerate(lines[start:], start) if not line.startswith(' ')
                    and not line.startswith('Traceback')), None)
        if end is not None and end != start:
            return lines[end]


def main(
        target: str = Option("http://localhost:8001", help=(
                "target server url"
        )),
        config_file: str = Option(os.path.expanduser('~/.config/vitrina/data_upload.json')),
        no_create_task: bool = Option(False, "--no-create-task", help="Do not create a task for errors")
):
    apikey = ""
    if os.path.exists(config_file):
        with open(config_file, 'r') as config:
            data = json.load(config)
            apikey = data.get('apikey')

    distribution_url = urllib.parse.urljoin(target, 'partner/api/1/distributions/')
    session = requests.Session()
    session.headers.update({'Authorization': 'ApiKey {}'.format(apikey)})

    response = session.get(distribution_url)
    data = response.json()

    for resource in data:
        print(json.dumps(resource, indent=4, sort_keys=True))
        sha1 = hashlib.sha1(str(resource['id']).encode()).hexdigest()
        base_dir = Path(settings.SPINTA_PATH) / sha1[:2] / sha1[2:4] / sha1[4:]
        base_dir.mkdir(parents=True, exist_ok=True)
        config = {
            "env": "production",
            "data_path": str(base_dir),
            "default_auth_client": "default",
            "keymaps": {
                "default": {
                    "type": "sqlalchemy",
                    "dsn": f"sqlite:///{base_dir / 'keymap.db'}"
                }
            },
            "manifest": "default",
            "manifests": {
                "default": {
                    "type": "csv",
                    "path": str(base_dir / "manifest.csv"),
                    "backend": "default",
                    "keymap": "default",
                    "mode": "internal"
                }
            },
            "accesslog": {
                "type": "file",
                "file": str(base_dir / "accesslog.json")
            }
        }
        with open(base_dir / 'config.yml', 'w') as f:
            yaml.dump(config, f, default_flow_style=False)

        state_file_path = base_dir / 'state.json'
        state = {}
        if state_file_path.exists():
            with open(state_file_path, 'r') as f:
                state = json.load(f)

        last_update_str = state.get('last_update', '')
        if last_update_str:
            last_update = datetime.datetime.strptime(last_update_str, "%Y-%m-%dT%H:%M:%S")
        else:
            last_update = datetime.datetime.min

        if datetime.datetime.now() - last_update > datetime.timedelta(hours=resource['update_interval']):
            pass
        else:
            continue

        tabular_url = urllib.parse.urljoin(target, f'partner/api/1/distribution/id/{resource["id"]}/tabular-data/')
        response = session.get(tabular_url)
        tabular_data = response.json()
        first_item = tabular_data[0] if tabular_data else None

        if first_item is not None:
            with open(base_dir / 'manifest.csv', 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(first_item.keys())

                for row in tabular_data:
                    writer.writerow(row.values())
        else:
            continue
        run_spinta_command(base_dir, resource, target, session, no_create_task, state, state_file_path)


if __name__ == '__main__':
    run(main)
