"""Tests for Story 24.11 - Fix Template→Prompt Terminology.

These tests verify consistent "Prompt" terminology throughout the dashboard:
1. Error messages use "Prompt not found" not "Template not found"
2. Modal titles use "Prompt:" not "Template:"
3. Toast notifications use "prompt" not "template"
4. Story 24.2 AC3 comments exist for traceability
"""

from pathlib import Path

import pytest


# Shared fixtures to read source files
@pytest.fixture
def context_menu_content() -> str:
    """Read context-menu.js content for frontend terminology verification."""
    context_menu_path = (
        Path(__file__).parent.parent.parent
        / "src/bmad_assist/dashboard/static-src/js/components/context-menu.js"
    )
    return context_menu_path.read_text(encoding="utf-8")


@pytest.fixture
def content_routes_content() -> str:
    """Read routes/content.py for backend terminology verification."""
    content_routes_path = (
        Path(__file__).parent.parent.parent
        / "src/bmad_assist/dashboard/routes/content.py"
    )
    return content_routes_path.read_text(encoding="utf-8")


@pytest.fixture(scope="session")
def static_src_files() -> dict[str, str]:
    """Read all static-src HTML and JS files for comprehensive terminology check.

    Includes:
    - All HTML partials (*.html)
    - Top-level JS files (js/*.js) - alpine-init.js, utils.js, shiki-highlighter.js
    - Component JS files (js/components/*.js)
    """
    static_src_dir = (
        Path(__file__).parent.parent.parent
        / "src/bmad_assist/dashboard/static-src"
    )
    files = {}
    for html_file in static_src_dir.glob("*.html"):
        files[html_file.name] = html_file.read_text(encoding="utf-8")
    # Include top-level JS files (alpine-init.js, utils.js, shiki-highlighter.js)
    for js_file in (static_src_dir / "js").glob("*.js"):
        files[f"js/{js_file.name}"] = js_file.read_text(encoding="utf-8")
    # Include component JS files
    for js_file in (static_src_dir / "js/components").glob("*.js"):
        files[f"js/components/{js_file.name}"] = js_file.read_text(encoding="utf-8")
    return files


class TestBackendPromptTerminology:
    """Tests verifying backend uses 'Prompt' not 'Template' terminology (AC 1)."""

    def test_404_error_uses_prompt_not_template(
        self, content_routes_content: str
    ) -> None:
        """AC1: Error message should say 'Prompt not found' not 'Template not found'."""
        # Should contain the correct terminology
        assert "Prompt not found for phase:" in content_routes_content
        # Should NOT contain wrong terminology
        assert "Template not found" not in content_routes_content

    def test_story_24_2_ac3_comment_present(
        self, content_routes_content: str
    ) -> None:
        """AC1: Story 24.2 AC3 comment should exist for traceability."""
        assert "Story 24.2 AC3" in content_routes_content

    def test_no_template_in_error_messages(
        self, content_routes_content: str
    ) -> None:
        """AC1: No user-facing error messages should contain 'template'."""
        # Find all JSONResponse error lines
        lines = content_routes_content.split("\n")
        for i, line in enumerate(lines):
            if '{"error":' in line or '"error":' in line:
                # Check for template terminology (case insensitive)
                line_lower = line.lower()
                if "template" in line_lower:
                    # Allow "output-template" as it's an XML element name
                    if "output-template" not in line_lower:
                        pytest.fail(
                            f"Line {i + 1} contains 'template' in error message: {line}"
                        )


class TestFrontendPromptTerminology:
    """Tests verifying frontend uses 'Prompt' not 'Template' terminology (AC 2)."""

    def test_modal_title_uses_prompt(self, context_menu_content: str) -> None:
        """AC2: Modal title should be 'Prompt: ${phase}' not 'Template: ${phase}'."""
        # Find openPromptBrowser call
        assert "Prompt: ${phase}" in context_menu_content
        assert "Template: ${phase}" not in context_menu_content

    def test_404_toast_uses_prompt(self, context_menu_content: str) -> None:
        """AC2: Toast on 404 should say 'Prompt not found' not 'Template not found'."""
        assert "Prompt not found for phase:" in context_menu_content
        # Check case variations
        assert "Template not found" not in context_menu_content
        assert "template not found" not in context_menu_content

    def test_error_toast_uses_prompt(self, context_menu_content: str) -> None:
        """AC2: Error toast should say 'Failed to fetch prompt' not 'template'."""
        assert "Failed to fetch prompt" in context_menu_content
        assert "Failed to fetch template" not in context_menu_content

    def test_all_story_24_2_ac3_comments_present(
        self, context_menu_content: str
    ) -> None:
        """AC2: All Story 24.2 AC3 traceability comments should exist."""
        # Find viewPrompt function
        view_prompt_start = context_menu_content.find("async viewPrompt(")
        assert view_prompt_start != -1, "viewPrompt function not found"

        # Get the function body (up to next function or class method)
        view_prompt_end = context_menu_content.find(
            "\n        /**", view_prompt_start + 100
        )
        view_prompt_section = context_menu_content[view_prompt_start:view_prompt_end]

        # Should have Story 24.2 AC3 comments
        ac3_count = view_prompt_section.count("Story 24.2 AC3")
        assert ac3_count >= 3, (
            f"Expected at least 3 'Story 24.2 AC3' comments in viewPrompt, found {ac3_count}"
        )


class TestNoWrongTemplateTerminology:
    """Tests verifying no user-facing 'template' strings for prompts (AC 3)."""

    def test_no_template_modal_title_pattern(
        self, static_src_files: dict[str, str]
    ) -> None:
        """AC3: No 'Template: ${' patterns in any static-src files."""
        for filename, content in static_src_files.items():
            if "Template: ${" in content:
                pytest.fail(
                    f"File {filename} contains 'Template: ${{' pattern - "
                    "should use 'Prompt: ${'"
                )

    def test_no_template_not_found_pattern(
        self, static_src_files: dict[str, str]
    ) -> None:
        """AC3: No 'template not found' patterns in any static-src files."""
        for filename, content in static_src_files.items():
            content_lower = content.lower()
            if "template not found" in content_lower:
                pytest.fail(
                    f"File {filename} contains 'template not found' - "
                    "should use 'prompt not found'"
                )

    def test_no_failed_to_fetch_template_pattern(
        self, static_src_files: dict[str, str]
    ) -> None:
        """AC3: No 'Failed to fetch template' patterns in any static-src files."""
        for filename, content in static_src_files.items():
            content_lower = content.lower()
            if "failed to fetch template" in content_lower:
                pytest.fail(
                    f"File {filename} contains 'failed to fetch template' - "
                    "should use 'failed to fetch prompt'"
                )

    def test_output_template_section_is_acceptable(
        self, static_src_files: dict[str, str]
    ) -> None:
        """AC3 Exception: 'Output Template' section header is acceptable.

        The 'Output Template' label in the Prompt Browser describes the XML
        <output-template> element content - this is correct terminology as
        it refers to the template structure, not the prompt itself.
        """
        tail_content = static_src_files.get("11-tail.html", "")
        assert "Output Template" in tail_content, (
            "Expected 'Output Template' section header in 11-tail.html"
        )
        # This is acceptable - it's describing the XML output-template element

    def test_experiment_templates_are_acceptable(
        self, static_src_files: dict[str, str]
    ) -> None:
        """AC3 Exception: Experiment templates (config/loop/patch-set) are acceptable.

        These are a different concept - configuration templates, not prompts.
        Experiment templates define experiment configurations (configs, loops, patch-sets),
        which is distinct from "prompt templates" which this story addresses.
        """
        experiments_panel = static_src_files.get("06-experiments-panel.html", "")
        assert experiments_panel, "experiments-panel.html should exist"

        # Verify experiment panel uses "template" in the experiment context
        # (config/loop/patch-set templates, NOT prompt-related terminology)
        experiments_js = static_src_files.get("js/components/experiments.js", "")
        assert experiments_js, "experiments.js should exist"

        # Verify experiment templates use proper experiment terminology
        assert "selectedTemplate:" in experiments_js, (
            "experiments.js should track selected template"
        )
        # Verify experiments panel doesn't use prompt-related error messages
        assert "prompt not found" not in experiments_panel.lower(), (
            "experiments-panel.html should not contain prompt error terminology"
        )

    def test_alpine_template_tags_are_acceptable(
        self, static_src_files: dict[str, str]
    ) -> None:
        """AC3 Exception: Alpine.js <template> HTML tags are acceptable.

        These are structural HTML elements, not related to prompt terminology.
        """
        # Verify Template: patterns are either:
        # 1. "Output Template" (section header describing XML output-template element)
        # 2. In experiments.js (experiment config/loop/patch-set templates)
        for filename, content in static_src_files.items():
            if "Template:" in content:
                # Check for acceptable uses
                is_output_template = "Output Template" in content
                is_experiments_js = "experiments.js" in filename
                is_selected_template = "selectedTemplate:" in content

                if not (is_output_template or is_experiments_js or is_selected_template):
                    pytest.fail(
                        f"File {filename} contains 'Template:' pattern that is not "
                        "an acceptable exception - should use 'Prompt:'"
                    )


class TestBuiltStaticHtml:
    """Tests verifying the built static/index.html has correct terminology.

    Note: The built index.html is a concatenation of static-src/*.html files.
    JavaScript files (static-src/js/**/*.js) are NOT embedded in index.html;
    they are loaded via <script src="/js/..."> tags and served separately.
    Therefore, JS-specific terminology tests should use static_src_files fixture.
    """

    @pytest.fixture
    def built_index_content(self) -> str:
        """Read the built static/index.html file."""
        index_path = (
            Path(__file__).parent.parent.parent
            / "src/bmad_assist/dashboard/static/index.html"
        )
        if not index_path.exists():
            pytest.skip("static/index.html not built yet")
        return index_path.read_text(encoding="utf-8")

    def test_no_template_not_found_in_built_html(
        self, built_index_content: str
    ) -> None:
        """Verify built HTML has no 'template not found' patterns.

        Note: JS files are loaded separately, so this checks HTML partials only.
        """
        content_lower = built_index_content.lower()
        # Should not have wrong terminology in HTML partials
        assert "template not found" not in content_lower

    def test_no_failed_to_fetch_template_in_built_html(
        self, built_index_content: str
    ) -> None:
        """Verify built HTML has no 'Failed to fetch template' patterns.

        Note: JS files are loaded separately, so this checks HTML partials only.
        """
        content_lower = built_index_content.lower()
        assert "failed to fetch template" not in content_lower

    def test_no_template_modal_title_in_built_html(
        self, built_index_content: str
    ) -> None:
        """Verify built HTML has no 'Template: ${' modal title patterns.

        Note: JS files are loaded separately, so this checks HTML partials only.
        """
        assert "Template: ${" not in built_index_content

    def test_output_template_section_in_built_html(
        self, built_index_content: str
    ) -> None:
        """Verify 'Output Template' section header exists (acceptable exception)."""
        # The Output Template section describes XML output-template element content
        assert "Output Template" in built_index_content

    def test_context_menu_js_script_tag_present(
        self, built_index_content: str
    ) -> None:
        """Verify context-menu.js is loaded (contains Prompt terminology)."""
        # JS files are separate, so verify the script tag exists
        assert "context-menu.js" in built_index_content
