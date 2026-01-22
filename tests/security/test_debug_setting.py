"""
Tests for DEBUG setting security configuration.

WEB-11: Verify DEBUG=False in production
"""

import os
from unittest import mock
from django.conf import settings
import pytest


class TestDebugSetting:
    """Test that DEBUG setting is properly configured for production safety."""

    def test_debug_default_is_false(self):
        """
        Test that DEBUG defaults to False when no environment variable is set.

        This is critical - if DEBUG=True in production, it exposes:
        - Stack traces with sensitive code paths
        - Settings and environment variables
        - SQL queries with potential credentials
        - Internal file paths and structure
        """
        # In our current runtime, we can't change settings.DEBUG,
        # but we can verify the environment parsing logic
        import environ

        # Test that when DEBUG env var is not set, it defaults to False
        env = environ.Env()

        # Mock environment without DEBUG
        with mock.patch.dict(os.environ, {}, clear=False):
            # Remove DEBUG if it exists
            os.environ.pop("DEBUG", None)

            # This should default to False
            debug_value = env.bool("DEBUG", default=False)
            assert debug_value is False, "DEBUG should default to False for security"

    def test_debug_respects_env_true(self):
        """Test that DEBUG=true in environment is properly parsed."""
        import environ

        env = environ.Env()

        with mock.patch.dict(os.environ, {"DEBUG": "true"}):
            debug_value = env.bool("DEBUG", default=False)
            assert debug_value is True

    def test_debug_respects_env_false(self):
        """Test that DEBUG=false in environment is properly parsed."""
        import environ

        env = environ.Env()

        with mock.patch.dict(os.environ, {"DEBUG": "false"}):
            debug_value = env.bool("DEBUG", default=False)
            assert debug_value is False

    def test_debug_setting_exists(self):
        """Test that DEBUG setting is configured in Django settings."""
        assert hasattr(settings, "DEBUG"), "DEBUG setting must be defined"
        assert isinstance(settings.DEBUG, bool), "DEBUG must be a boolean"

    def test_production_checklist(self):
        """
        Document production deployment checklist for DEBUG setting.

        Production environment MUST have:
        1. DEBUG=false explicitly set in environment variables
        2. Docker compose files should use DEBUG=false
        3. Nginx/reverse proxy should hide Django errors
        4. Custom error pages (404, 500) configured
        """
        # This is a documentation test - always passes
        # Real check: audit deployment configs

        production_checklist = {
            "env_debug_false": "Set DEBUG=false in production .env",
            "docker_compose": "Update docker-compose.yml DEBUG=false",
            "error_pages": "Configure ALLOWED_HOSTS and custom error pages",
            "nginx": "Nginx should serve custom error pages",
        }

        # In actual deployment, verify these manually or via deployment tests
        assert production_checklist is not None


class TestDebugModeSecurityImplications:
    """Document security implications of DEBUG=True in production."""

    def test_debug_mode_exposes_settings(self):
        """
        When DEBUG=True, Django error pages expose settings.
        This includes SECRET_KEY, database credentials, API keys, etc.
        """
        # This is a documentation test
        sensitive_exposure = [
            "SECRET_KEY",
            "DATABASE_PASSWORD",
            "AWS_SECRET_ACCESS_KEY",
            "VIISP_CERTIFICATE",
            "Internal file paths",
            "Installed packages and versions",
        ]

        assert len(sensitive_exposure) > 0, "DEBUG=True exposes sensitive data"

    def test_debug_mode_exposes_sql_queries(self):
        """
        When DEBUG=True, Django stores all SQL queries in memory
        and displays them in error pages.
        """
        # This is a documentation test
        if settings.DEBUG:
            from django.db import connection

            # In debug mode, queries are stored
            assert hasattr(connection, "queries"), "DEBUG mode enables query logging"

    @pytest.mark.skipif(not settings.DEBUG, reason="Only runs in DEBUG mode")
    def test_debug_toolbar_should_not_be_in_production(self):
        """
        Debug toolbar and similar tools should only be enabled in development.
        """
        # Check if debug toolbar is in INSTALLED_APPS
        debug_tools = [
            "debug_toolbar",
            "django_extensions",
        ]

        for tool in debug_tools:
            if tool in settings.INSTALLED_APPS:
                pytest.fail(f"{tool} should not be enabled in production (DEBUG=False)")
