"""Dashboard smoke tests.

Basic E2E tests to verify dashboard loads and core elements are present.
These tests require Playwright and a running dashboard server.

Run with:
    pytest tests/e2e/ -m e2e
"""

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from playwright.sync_api import Page

pytestmark = pytest.mark.e2e


class TestDashboardSmoke:
    """Smoke tests for dashboard UI."""

    def test_main_page_loads(self, page: "Page", dashboard_server: str) -> None:
        """Main page loads without errors."""
        page.goto(dashboard_server)

        # Check page loaded (title or main content)
        assert page.title() or page.locator("body").is_visible()

    def test_has_navigation(self, page: "Page", dashboard_server: str) -> None:
        """Navigation elements are present."""
        page.goto(dashboard_server)

        # Should have some nav structure (tabs, links, etc.)
        # Dashboard uses HTMX + Alpine.js with tabs
        nav = page.locator("nav, [role='tablist'], .tabs")
        assert nav.count() > 0 or page.locator("a").count() > 0

    def test_status_section_visible(self, page: "Page", dashboard_server: str) -> None:
        """Sprint status section is visible."""
        page.goto(dashboard_server)

        # Wait for initial DOM load (don't use networkidle - SSE keeps connection open)
        page.wait_for_load_state("domcontentloaded")

        # Give HTMX a moment to fetch content
        page.wait_for_timeout(1000)

        # Should show some status-related content
        body_text = page.locator("body").inner_text()
        # Either "status", "sprint", "epic", or "stories" should appear
        assert any(
            keyword in body_text.lower()
            for keyword in ["status", "sprint", "epic", "stories", "queue"]
        )

    def test_no_js_errors(self, page: "Page", dashboard_server: str) -> None:
        """Page loads without JavaScript errors."""
        errors: list[str] = []

        def handle_error(error: str) -> None:
            errors.append(str(error))

        page.on("pageerror", handle_error)
        page.goto(dashboard_server)

        # Wait for DOM and give JS time to execute
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_timeout(1000)

        assert not errors, f"JavaScript errors: {errors}"

    def test_api_status_endpoint(self, page: "Page", dashboard_server: str) -> None:
        """API status endpoint returns valid response."""
        response = page.request.get(f"{dashboard_server}/api/status")

        assert response.ok
        data = response.json()
        assert isinstance(data, dict)

    def test_footer_controls_visible(self, page: "Page", dashboard_server: str) -> None:
        """Footer control buttons are visible (Start, Pause, Experiments, Settings)."""
        page.goto(dashboard_server)
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_timeout(500)

        # Footer should be visible
        footer = page.locator("main > footer")
        assert footer.is_visible(), "Footer element not visible"

        # All control buttons should be present (use footer scope for Start/Pause)
        start_btn = footer.locator("button:has-text('Start')")
        pause_btn = footer.locator("button:has-text('Pause')")
        experiments_btn = page.locator("[data-testid='experiments-button']")
        settings_btn = page.locator("[data-testid='settings-button']")

        assert start_btn.is_visible(), "Start button not visible"
        assert pause_btn.is_visible(), "Pause button not visible"
        assert experiments_btn.is_visible(), "Experiments button not visible"
        assert settings_btn.is_visible(), "Settings button not visible"

    def test_settings_panel_opens(self, page: "Page", dashboard_server: str) -> None:
        """Settings panel opens when clicking Settings button."""
        page.goto(dashboard_server)
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_timeout(500)

        # Click Settings button
        page.locator("[data-testid='settings-button']").click()
        page.wait_for_timeout(300)

        # Settings panel should be visible
        settings_panel = page.locator("[data-testid='settings-panel']")
        assert settings_panel.is_visible(), "Settings panel did not open"

    def test_experiments_panel_opens(self, page: "Page", dashboard_server: str) -> None:
        """Experiments panel opens when clicking Experiments button."""
        page.goto(dashboard_server)
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_timeout(500)

        # Click Experiments button
        page.locator("[data-testid='experiments-button']").click()
        page.wait_for_timeout(300)

        # Experiments panel should be visible
        experiments_panel = page.locator("[data-testid='experiments-panel']")
        assert experiments_panel.is_visible(), "Experiments panel did not open"
