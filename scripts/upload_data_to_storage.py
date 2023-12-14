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

    base_dir_path = Path(base_dir)
    manifest_path = base_dir_path / "manifest.csv"

    result = subprocess.run(
        [spinta_executable, "push", str(manifest_path), "--no-progress-bar", "-o", spinta_server_name],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        text=True
    )
    print(result)
    if result.returncode != 0:
        handle_error(result.stderr, base_dir)


def handle_error(stderr, base_dir):
    lines = stderr.splitlines('\n')
    try:
        start = lines.index(next(line for line in lines if line.startswith('Traceback')))
        end = lines.index(next(line for line in lines[start:] if not line.startswith(' ')))
        error_message = '\n'.join(lines[start:end])
        print(error_message)  # Print the error message
    except StopIteration:
        print("No traceback found in stderr")
        print(lines)
    except ValueError:
        print("Default value not found in lines")
        print(lines)


def main():
    for resource in DatasetDistribution.objects.filter(upload_to_storage=True):
        sha1 = hashlib.sha1(str(resource.id).encode()).hexdigest()
        base_dir = Path(settings.SPINTA_PATH) / sha1[:2] / sha1[2:4] / sha1[4:]
        base_dir.mkdir(parents=True, exist_ok=True)
        config = {
            "env": "production",
            "data_path": str(base_dir),
            "default_auth_client": "default",
            "keymaps": {
                "default": {
                    "type": "sqlalchemy",
                    "dsn": f"sqlite:///{base_dir}/keymap.db"
                }
            },
            "manifest": "default",
            "manifests": {
                "default": {
                    "type": "csv",
                    "path": f"{base_dir}/manifest.csv",
                    "backend": "default",
                    "keymap": "default",
                    "mode": "internal"
                }
            },
            "accesslog": {
                "type": "file",
                "file": f"{base_dir}/accesslog.json"
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
