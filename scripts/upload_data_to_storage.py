import json
import os
import urllib.parse

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


def run_spinta_command(base_dir, spinta_server_name, spinta_executable, resource_id, target, session):
    env = os.environ.copy()
    env['SPINTA_CONFIG'] = str(base_dir / "config.yml")

    base_dir_path = Path(base_dir)
    manifest_path = base_dir_path / "manifest.csv"
    result = subprocess.run(
        [spinta_executable, '--tb=native', "push", str(manifest_path), "--no-progress-bar", "-o", spinta_server_name],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        text=True
    )
    if result.returncode != 0:
        error_text = handle_error(result.stderr)
        task_url = urllib.parse.urljoin(target, f'partner/api/1/tasks/{resource_id}/')
        response = session.post(task_url, data={'error_text': error_text,
                                                'title': 'Klaida keliant duomenis į saugyklą',
                                                'app_name': 'vitrina_resources',
                                                'model_name': 'DatasetDistribution',
                                                'task_type': 'ERROR_DISTRIBUTION'})
        task_create_response = response.json()
        print(task_create_response)
    else:
        print('completed')


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
        config_file: str = Option(os.path.expanduser('~/.config/vitrina/data_upload.json'))
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

        manifest_csv_path = base_dir / 'manifest.csv'

        distribution_id = resource['id']
        tabular_url = urllib.parse.urljoin(target, f'partner/api/1/distribution/id/{distribution_id}/tabular-data/')
        response = session.get(tabular_url)
        tabular_data = response.json()
        first_item = tabular_data[0] if tabular_data else None

        if first_item is not None:
            with open(manifest_csv_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(first_item.keys())
                writer.writerow(first_item.values())

                for row in tabular_data:
                    writer.writerow(row.values())
        else:
            continue
        run_spinta_command(base_dir, settings.SPINTA_SERVER_NAME, settings.SPINTA_EXECUTABLE,
                           resource['id'], target, session)


if __name__ == '__main__':
    run(main)
