"""Tests for Epic Browser functionality (Story 24.6).

Tests the epic details viewing functionality including:
- API endpoint GET /api/epics/{epic_id}
- Frontend JavaScript behavior specifications (skipped - require E2E testing)
"""

from pathlib import Path

import pytest
from starlette.testclient import TestClient

from bmad_assist.dashboard.server import DashboardServer


class TestEpicDetailsEndpoint:
    """Tests for GET /api/epics/{epic_id} endpoint.

    The endpoint already existed but these tests verify the contract
    expected by the Epic Browser UI (Story 24.6).
    """

    @pytest.fixture
    def server_with_epic(self, tmp_path: Path):
        """Create a server with an epic file."""
        # Create docs/epics directory
        epics_dir = tmp_path / "docs" / "epics"
        epics_dir.mkdir(parents=True, exist_ok=True)

        # Create sharded epic file
        epic_content = """---
title: Dashboard Content Browsers
status: in-progress
---

# Epic 24: Dashboard Content Browsers

## Overview

This epic implements content browser functionality for the dashboard.

## Stories

### Story 24.1: Shared Browser Infrastructure
Status: done
"""
        epic_file = epics_dir / "epic-24-dashboard-content-browsers.md"
        epic_file.write_text(epic_content)

        # Create implementation-artifacts directory with sprint-status.yaml
        impl_dir = tmp_path / "_bmad-output" / "implementation-artifacts"
        impl_dir.mkdir(parents=True, exist_ok=True)
        sprint_status = impl_dir / "sprint-status.yaml"
        sprint_status.write_text("entries: {}")

        # Create server and app
        server = DashboardServer(project_root=tmp_path)
        app = server.create_app()
        return TestClient(app)

    def test_endpoint_returns_epic_content(self, server_with_epic):
        """Test endpoint returns epic content with expected structure."""
        response = server_with_epic.get("/api/epics/24")

        assert response.status_code == 200
        data = response.json()

        # Verify required fields for Epic Browser (AC1)
        assert "id" in data
        assert "title" in data
        assert "content" in data
        assert "path" in data

        # Verify content values
        assert data["id"] == "24" or data["id"] == 24
        assert data["title"] == "Dashboard Content Browsers"
        assert "Dashboard Content Browsers" in data["content"]

    def test_endpoint_returns_404_when_not_found(self, tmp_path: Path):
        """Test endpoint returns 404 when epic file not found."""
        # Create minimal structure
        docs_dir = tmp_path / "docs" / "epics"
        docs_dir.mkdir(parents=True, exist_ok=True)

        impl_dir = tmp_path / "_bmad-output" / "implementation-artifacts"
        impl_dir.mkdir(parents=True, exist_ok=True)
        sprint_status = impl_dir / "sprint-status.yaml"
        sprint_status.write_text("entries: {}")

        # Create server and app
        server = DashboardServer(project_root=tmp_path)
        app = server.create_app()
        client = TestClient(app)

        response = client.get("/api/epics/99")

        assert response.status_code == 404
        data = response.json()
        assert "error" in data
        assert "99" in data["error"]

    def test_endpoint_handles_string_epic_ids(self, tmp_path: Path):
        """Test endpoint handles string epic IDs like 'testarch'."""
        # Create docs/epics directory
        epics_dir = tmp_path / "docs" / "epics"
        epics_dir.mkdir(parents=True, exist_ok=True)

        # Create epic file with string ID
        epic_content = """---
title: Test Architect Module
status: done
---

# Epic testarch: Test Architect Module

Test architecture epic content.
"""
        epic_file = epics_dir / "epic-testarch-test-architect.md"
        epic_file.write_text(epic_content)

        # Create implementation-artifacts
        impl_dir = tmp_path / "_bmad-output" / "implementation-artifacts"
        impl_dir.mkdir(parents=True, exist_ok=True)
        sprint_status = impl_dir / "sprint-status.yaml"
        sprint_status.write_text("entries: {}")

        # Create server and app
        server = DashboardServer(project_root=tmp_path)
        app = server.create_app()
        client = TestClient(app)

        response = client.get("/api/epics/testarch")

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Test Architect Module"

    def test_endpoint_includes_full_markdown_content(self, server_with_epic):
        """Test endpoint returns full markdown content for rendering (AC1)."""
        response = server_with_epic.get("/api/epics/24")

        assert response.status_code == 200
        data = response.json()

        # Verify full content is returned (not truncated)
        assert "## Overview" in data["content"]
        assert "## Stories" in data["content"]
        assert "### Story 24.1" in data["content"]


@pytest.mark.skip(reason="Frontend spec - requires E2E/Playwright testing")
class TestViewEpicDetailsBrowserState:
    """Frontend specification tests for viewEpicDetails browser state initialization.

    These tests document expected frontend behavior. They are SKIPPED because:
    - Python unit tests cannot verify JavaScript behavior
    - Actual verification requires E2E testing with Playwright/Selenium

    See tree-view.js:viewEpicDetails() for implementation.
    """

    def test_browser_state_created_before_modal_open(self):
        """Specification: viewEpicDetails should create browser state before showing modal.

        Story 24.6 AC2: Modal includes Raw/Rendered toggle button group.
        This requires browser state to be initialized before modal.show = true.

        Expected sequence:
        1. fetch /api/epics/{id}
        2. contentModal.browser = window.contentBrowserComponent().createBrowserState()
        3. contentModal.title = ...
        4. contentModal.content = ...
        5. contentModal.type = 'markdown'
        6. contentModal.show = true
        """
        pass

    def test_browser_state_defaults_to_rendered(self):
        """Specification: Browser state should default to 'rendered' view.

        Story 24.6 AC2: Toggle defaults to "Rendered" view.
        createBrowserState() returns { view: 'rendered', projectRoot: null }.
        """
        pass

    def test_toggle_resets_on_each_modal_open(self):
        """Specification: Toggle should reset to Rendered on each modal open.

        Story 24.6 AC2: resets on each modal open via createBrowserState().
        Each call to viewEpicDetails creates a fresh browser state object.
        """
        pass


@pytest.mark.skip(reason="Frontend spec - requires E2E/Playwright testing")
class TestEpicModalToggleAndCopy:
    """Frontend specification tests for epic modal Raw/Rendered toggle and Copy button.

    These tests document expected frontend behavior. They are SKIPPED because:
    - Python unit tests cannot verify JavaScript behavior
    - Actual verification requires E2E testing with Playwright/Selenium

    See 10-modals.html contentModal section for implementation.
    """

    def test_toggle_switches_views_instantly(self):
        """Specification: Toggle should switch views instantly (< 100ms).

        Story 24.6 AC2: Toggle switches views instantly (synchronous Alpine.js state change).
        No async operations - just contentModal.browser.view = 'rendered' or 'raw'.
        """
        pass

    def test_rendered_view_shows_markdown_with_syntax_highlighting(self):
        """Specification: Rendered view should display rendered markdown with Shiki highlighting.

        Story 24.6 AC2: Markdown rendered with headers, lists, tables, code blocks
        with Shiki syntax highlighting.

        Uses formatMarkdownContent() with Shiki highlighter.
        """
        pass

    def test_raw_view_shows_plain_markdown(self):
        """Specification: Raw view should display plain markdown source.

        Story 24.6 AC2: Raw view: Plain markdown source in monospace font.
        Uses <pre class="whitespace-pre-wrap font-mono"><code x-text="...">
        """
        pass

    def test_copy_button_copies_raw_content(self):
        """Specification: Copy button should copy raw markdown regardless of view mode.

        Story 24.6 AC3: Clicking copies RAW (unrendered) markdown to clipboard
        regardless of current view mode.

        Copy button calls copyRawContent(contentModal.content, showToast).
        """
        pass

    def test_copy_button_shows_tooltip(self):
        """Specification: Copy button should have tooltip "Copies raw content".

        Story 24.6 AC3: Modal includes Copy button with tooltip "Copies raw content".
        The :title attribute is set to "Copies raw content" when browser state exists.
        """
        pass

    def test_copy_button_shows_toast_on_success(self):
        """Specification: Toast notification should appear on successful copy.

        Story 24.6 AC3: Toast notification on successful copy.
        copyRawContent() calls showToast('Copied to clipboard!').
        """
        pass


@pytest.mark.skip(reason="Frontend spec - requires E2E/Playwright testing")
class TestEpicModalErrorHandling:
    """Frontend specification tests for epic modal error handling.

    These tests document expected frontend behavior. They are SKIPPED because:
    - Python unit tests cannot verify JavaScript behavior
    - Actual verification requires E2E testing with Playwright/Selenium

    See tree-view.js:viewEpicDetails() for implementation.
    """

    def test_error_shows_toast_not_modal(self):
        """Specification: Error should show toast and NOT open modal.

        Story 24.6 AC4: If epic file not found, show toast "Failed to load epic details".
        Modal should not open on error.

        viewEpicDetails catches error, calls showToast(), does NOT set contentModal.show.
        """
        pass

    def test_http_error_shows_toast(self):
        """Specification: HTTP errors should show toast message.

        On non-ok response, viewEpicDetails shows toast with error message.
        """
        pass


@pytest.mark.skip(reason="Frontend spec - requires E2E/Playwright testing")
class TestContextMenuViewEpicDetails:
    """Frontend specification tests for context menu "View details" action.

    These tests document expected frontend behavior. They are SKIPPED because:
    - Python unit tests cannot verify JavaScript behavior
    - Actual verification requires E2E testing with Playwright/Selenium

    See context-menu.js:getContextActions() for implementation.
    """

    def test_view_details_action_exists_for_epics(self):
        """Specification: "View details" action should exist in epic context menu.

        getContextActions('epic', item) returns array with first action:
        { icon: '📄', label: 'View details', action: 'view-epic', testId: 'action-view-epic' }
        """
        pass

    def test_view_details_triggers_viewEpicDetails(self):
        """Specification: "View details" action should call viewEpicDetails(item.id).

        executeAction with action='view-epic' calls this.viewEpicDetails(item?.id).
        """
        pass
