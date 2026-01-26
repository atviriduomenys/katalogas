"""
Tests for Subresource Integrity (SRI) hashes in templates.

Tests WEB-2 (External Scripts Without SRI).
"""

import re
from pathlib import Path


class TestSRIHashes:
    """Test that external CDN resources have SRI integrity hashes."""

    def test_base_template_has_chartjs_sri_hash(self):
        """Test that Chart.js in base.html has SRI integrity hash (WEB-2)."""
        base_template = Path("vitrina/templates/base.html")
        content = base_template.read_text()

        # Check for Chart.js 4.3.0 with integrity hash
        assert "chart.js@4.3.0" in content, "Chart.js 4.3.0 should be loaded"
        assert 'integrity="sha384-' in content, "Chart.js should have SRI integrity hash"
        assert 'crossorigin="anonymous"' in content, "Chart.js should have crossorigin attribute"

        # Verify the specific integrity hash for Chart.js 4.3.0
        expected_hash = "sha384-YAshAm4KKjf8V01c4sdNbPYiwU0D0Q82fjMHhKw8VvP0ecY4fxXsZAHxC4r4Ei+T"
        assert expected_hash in content, f"Chart.js should have the correct SRI hash: {expected_hash}"

    def test_users_stats_chart_has_chartjs_sri_hash(self):
        """Test that Chart.js in users_count_stats_chart.html has SRI integrity hash (WEB-2)."""
        template = Path("vitrina/users/templates/users_count_stats_chart.html")
        content = template.read_text()

        # Check for Chart.js 4.3.0 with integrity hash
        assert "chart.js@4.3.0" in content, "Chart.js 4.3.0 should be loaded"
        assert 'integrity="sha384-' in content, "Chart.js should have SRI integrity hash"
        assert 'crossorigin="anonymous"' in content, "Chart.js should have crossorigin attribute"

        # Verify the specific integrity hash for Chart.js 4.3.0
        expected_hash = "sha384-YAshAm4KKjf8V01c4sdNbPYiwU0D0Q82fjMHhKw8VvP0ecY4fxXsZAHxC4r4Ei+T"
        assert expected_hash in content, f"Chart.js should have the correct SRI hash: {expected_hash}"

    def test_users_stats_chart_no_old_jquery(self):
        """Test that old HTTP jQuery is removed from users_count_stats_chart.html (WEB-5)."""
        template = Path("vitrina/users/templates/users_count_stats_chart.html")
        content = template.read_text()

        # Check that old jQuery is NOT present
        assert "http://code.jquery.com" not in content, "Old HTTP jQuery should be removed"
        assert "jquery-1.10.0" not in content, "jQuery 1.10.0 should not be loaded"

    def test_users_stats_chart_no_old_chartjs(self):
        """Test that old Chart.js 2.9.3 is removed from users_count_stats_chart.html (WEB-2)."""
        template = Path("vitrina/users/templates/users_count_stats_chart.html")
        content = template.read_text()

        # Check that old Chart.js 2.9.3 is NOT present
        assert "chart.js@2.9.3" not in content, "Old Chart.js 2.9.3 should be removed"

    def test_no_insecure_http_cdn_resources(self):
        """Test that no external resources are loaded over HTTP (WEB-5)."""
        templates = [
            Path("vitrina/templates/base.html"),
            Path("vitrina/users/templates/users_count_stats_chart.html"),
        ]

        for template in templates:
            content = template.read_text()

            # Look for HTTP (not HTTPS) CDN URLs
            # Exclude commented lines
            lines = [line for line in content.split("\n") if not line.strip().startswith("{#")]
            content_no_comments = "\n".join(lines)

            # Check for insecure CDN patterns
            insecure_patterns = [
                r'src="http://[^"]*(?:cdn|code\.jquery|unpkg|jsdelivr)',
                r'href="http://[^"]*(?:cdn|code\.jquery|unpkg|jsdelivr)',
            ]

            for pattern in insecure_patterns:
                matches = re.findall(pattern, content_no_comments, re.IGNORECASE)
                assert not matches, (
                    f"Found insecure HTTP CDN resource in {template}: {matches}. All CDN resources must use HTTPS."
                )


class TestSRIHashIntegrity:
    """Test that SRI hashes follow correct format and security practices."""

    def test_sri_hash_format(self):
        """Test that SRI hashes use SHA-384 or stronger (not SHA-256)."""
        templates = [
            Path("vitrina/templates/base.html"),
            Path("vitrina/users/templates/users_count_stats_chart.html"),
        ]

        for template in templates:
            content = template.read_text()

            # Find all integrity attributes
            integrity_hashes = re.findall(r'integrity="([^"]+)"', content)

            for hash_value in integrity_hashes:
                # SRI hashes should use sha384 or sha512, not sha256
                assert hash_value.startswith(("sha384-", "sha512-")), (
                    f"SRI hash in {template} should use SHA-384 or SHA-512 for security: {hash_value}"
                )

                # Hash should have reasonable length (base64 encoded)
                hash_part = hash_value.split("-", 1)[1]
                assert len(hash_part) > 40, f"SRI hash seems too short in {template}: {hash_value}"

    def test_sri_has_crossorigin(self):
        """Test that resources with SRI also have crossorigin attribute."""
        templates = [
            Path("vitrina/templates/base.html"),
            Path("vitrina/users/templates/users_count_stats_chart.html"),
        ]

        for template in templates:
            content = template.read_text()

            # Find script tags with integrity
            script_blocks = re.findall(r'<script[^>]*integrity="[^"]*"[^>]*>', content, re.MULTILINE | re.DOTALL)

            for script in script_blocks:
                assert "crossorigin=" in script, (
                    f"Script with integrity must have crossorigin attribute in {template}: {script}"
                )
