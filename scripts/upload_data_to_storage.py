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
from vitrina.structure.services import _resource_models_to_tabular


def run_spinta_command(base_dir, spinta_server_name, spinta_executable):
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
        handle_error(result.stderr)


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

    url = urllib.parse.urljoin(target, 'partner/api/1/distributions')
    session = requests.Session()
    session.headers.update({'Authorization': 'ApiKey {}'.format(apikey)})

    response = session.get(url)
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

        tabular_data = _resource_models_to_tabular(resource)
        first_item = next(tabular_data, None)

        if first_item is not None:
            with open(manifest_csv_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(first_item.keys())
                writer.writerow(first_item.values())

                for row in tabular_data:
                    writer.writerow(row.values())
        else:
            continue
        run_spinta_command(base_dir, settings.SPINTA_SERVER_NAME, settings.SPINTA_EXECUTABLE)


if __name__ == '__main__':
    run(main)
