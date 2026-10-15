import json
import os
import subprocess
import sys

import pytest
from django.urls import reverse
from django_webtest import DjangoTestApp


@pytest.mark.django_db
def test_landing_loads_umami_when_configured(app: DjangoTestApp, settings):
    settings.UMAMI_SCRIPT_URL = "/stats.js"
    settings.UMAMI_WEBSITE_ID = "8f2c1a3e-0000-4000-8000-000000000001"

    response = app.get(reverse("home"))

    script = response.html.find("script", attrs={"data-website-id": settings.UMAMI_WEBSITE_ID})
    assert script is not None
    assert script["src"] == "/stats.js"


@pytest.mark.django_db
def test_landing_does_not_load_umami_when_not_configured(app: DjangoTestApp, settings):
    settings.UMAMI_SCRIPT_URL = ""
    settings.UMAMI_WEBSITE_ID = ""

    response = app.get(reverse("home"))

    assert response.html.find("script", attrs={"data-website-id": True}) is None


def csp_directives(umami_script_url: str) -> dict:
    code = (
        "import json, vitrina.settings as settings; "
        "print(json.dumps({"
        "'enforced': settings.CONTENT_SECURITY_POLICY['DIRECTIVES'], "
        "'report_only': settings.CONTENT_SECURITY_POLICY_REPORT_ONLY['DIRECTIVES']}, default=str))"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        env={**os.environ, "UMAMI_SCRIPT_URL": umami_script_url},
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout.strip().splitlines()[-1])


def test_csp_allows_absolute_umami_origin():
    directives = csp_directives("http://localhost:3000/script.js")

    for policy in directives.values():
        assert "http://localhost:3000" in policy["script-src"]
        assert "http://localhost:3000" in policy["connect-src"]


def test_csp_is_unchanged_for_relative_umami_path():
    assert csp_directives("/stats.js") == csp_directives("")
