import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "vitrina.settings")
django.setup()

import csv
import hashlib
from pathlib import Path
import yaml
from typer import run

from django.conf import settings
from vitrina.resources.models import DatasetDistribution
from vitrina.structure.services import _resource_models_to_tabular

import subprocess


def run_spinta_command(base_dir, spinta_server_name, spinta_executable):
    env = os.environ.copy()
    env['SPINTA_CONFIG'] = f"{base_dir}/config.yml"

    result = subprocess.run(
        [spinta_executable, "push", f"{base_dir}/manifest.csv", "--no-progress-bar", "-o", spinta_server_name],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        text=True
    )

    if result.returncode != 0:
        handle_error(result.stderr, base_dir)


def handle_error(stderr, base_dir):
    lines = stderr.split('\n')

    start = lines.index(next(line for line in lines if line.startswith('Traceback')))
    end = lines.index(next(line for line in lines[start:] if not line.startswith(' ')))

    error_message = '\n'.join(lines[start:end])


def main():
    for resource in DatasetDistribution.objects.filter(upload_to_storage=True):
        sha1 = hashlib.sha1(str(resource.id).encode()).hexdigest()
        base_dir = Path("{}/{}/{}/{}".format(settings.SPINTA_PATH, sha1[:2], sha1[2:4], sha1[4:]))
        os.makedirs(base_dir, exist_ok=True)
        config = {
            "env": "production",
            "data_path": str(base_dir),
            "default_auth_client": "default",
            "keymaps": {
                "default": {
                    "type": "sqlalchemy",
                    "dsn": "sqlite:///{}/keymap.db".format(base_dir)
                }
            },
            "manifest": "default",
            "manifests": {
                "default": {
                    "type": "csv",
                    "path": "{}/manifest.csv".format(base_dir),
                    "backend": "default",
                    "keymap": "default",
                    "mode": "internal"
                }
            },
            "accesslog": {
                "type": "file",
                "file": "{}/accesslog.json".format(base_dir)
            }
        }
        with open(base_dir / 'config.yml', 'w') as f:
            yaml.dump(config, f, default_flow_style=False)

        manifest_csv_path = base_dir / 'manifest.csv'
        tabular_data = _resource_models_to_tabular(resource)
        with open(manifest_csv_path, 'w', newline='') as f:
            writer = csv.writer(f)
            try:
                first_item = next(tabular_data)
            except StopIteration:
                first_item = None

            if first_item is not None:
                writer.writerow(first_item.keys())
                writer.writerow(first_item.values())

                for row in tabular_data:
                    writer.writerow(row.values())

        run_spinta_command(base_dir, settings.SPINTA_SERVER_NAME, settings.SPINTA_EXECUTABLE)


if __name__ == '__main__':
    run(main)
