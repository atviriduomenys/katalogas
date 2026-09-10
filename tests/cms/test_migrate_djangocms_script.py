"""The container's migration gate, driven through a fake python3.

scripts/migrate_djangocms.sh asks manage.py for the upgrade state and decides
whether to migrate at all. The state function has tests of its own; these pin
the shell branches, which nothing else exercises.
"""

import os
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "migrate_djangocms.sh"


def run_gate(tmp_path, state):
    log = tmp_path / "calls.log"
    fake = tmp_path / "python3"
    fake.write_text(
        f'#!/bin/sh\ncase "$*" in\n  *djangocms_upgrade_state*) echo "{state}" ;;\n  *) echo "$*" >> "{log}" ;;\nesac\n'
    )
    fake.chmod(0o755)
    env = {**os.environ, "PATH": f"{tmp_path}{os.pathsep}{os.environ['PATH']}"}
    result = subprocess.run(["bash", str(SCRIPT)], cwd=tmp_path, env=env, capture_output=True, text=True)
    calls = log.read_text().splitlines() if log.exists() else []
    return result, calls


@pytest.mark.parametrize("state", ["complete", "fresh"])
def test_a_finished_or_fresh_database_is_migrated(tmp_path, state):
    result, calls = run_gate(tmp_path, state)

    assert result.returncode == 0, result.stderr
    assert calls == ["manage.py migrate --skip-checks -v 2"]


@pytest.mark.parametrize("state", ["pending", "legacy_pages", "inconsistent", "something-else"])
def test_anything_the_migration_tool_has_not_finished_is_refused(tmp_path, state):
    """No migrate at all - not even the blog stage this image used to run itself."""
    result, calls = run_gate(tmp_path, state)

    assert result.returncode == 1
    assert calls == []


def test_the_refusal_says_where_to_go(tmp_path):
    result, _ = run_gate(tmp_path, "pending")

    assert "notes/migrations/djangocms" in result.stderr
