"""Testarch module configuration models.

This module provides Pydantic configuration models for the testarch
(Test Architect) module, enabling ATDD (Acceptance Test Driven Development)
features and eligibility detection configuration.

Usage:
    from bmad_assist.core import get_config

    config = get_config()
    if config.testarch is not None:
        atdd_mode = config.testarch.atdd_mode
        eligibility = config.testarch.eligibility
        if config.testarch.playwright:
            browsers = config.testarch.playwright.browsers
"""

from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# Valid browser options for PlaywrightConfig
VALID_BROWSERS: tuple[str, ...] = ("chromium", "firefox", "webkit")


class PlaywrightConfig(BaseModel):
    """Playwright browser testing configuration.

    Controls Playwright test execution settings including browser selection,
    display mode, and concurrency.

    Attributes:
        browsers: List of browsers to test against.
        headless: Run browsers without visible UI.
        timeout: Test timeout in milliseconds.
        workers: Number of parallel test workers.

    """

    __test__ = False  # Tell pytest this is not a test class
    model_config = ConfigDict(frozen=True)

    browsers: list[str] = Field(
        default_factory=lambda: ["chromium"],
        description="Browsers to test against: chromium, firefox, webkit",
        json_schema_extra={
            "security": "safe",
            "ui_widget": "checkbox_group",
            "options": list(VALID_BROWSERS),
        },
    )
    headless: bool = Field(
        default=True,
        description="Run browsers without visible UI",
        json_schema_extra={"security": "safe", "ui_widget": "toggle"},
    )
    timeout: int = Field(
        default=30000,
        ge=1000,
        le=300000,
        description="Test timeout in milliseconds",
        json_schema_extra={"security": "safe", "ui_widget": "number", "unit": "ms"},
    )
    workers: int = Field(
        default=1,
        ge=1,
        le=16,
        description="Number of parallel test workers",
        json_schema_extra={"security": "safe", "ui_widget": "number"},
    )

    @field_validator("browsers", mode="after")
    @classmethod
    def validate_browsers(cls, v: list[str]) -> list[str]:
        """Validate that all browsers are valid Playwright browsers."""
        invalid = [b for b in v if b not in VALID_BROWSERS]
        if invalid:
            raise ValueError(
                f"Invalid browser(s): {', '.join(invalid)}. "
                f"Valid options: {', '.join(VALID_BROWSERS)}"
            )
        return v


class EligibilityConfig(BaseModel):
    """ATDD eligibility configuration with keyword/LLM weight balancing.

    Controls how stories are assessed for ATDD eligibility when atdd_mode
    is "auto". The hybrid scoring combines keyword-based detection with
    LLM-based assessment using the configured helper provider.

    Note: The deprecated `provider` and `model` fields are ignored for
    backward compatibility. Use `providers.helper` in the main config instead.

    Attributes:
        keyword_weight: Weight for keyword-based ATDD eligibility detection.
        llm_weight: Weight for LLM-based ATDD eligibility assessment.
        threshold: Score threshold to enable ATDD in auto mode.

    """

    model_config = ConfigDict(frozen=True, extra="ignore")

    keyword_weight: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Weight for keyword-based ATDD eligibility detection",
        json_schema_extra={"security": "safe", "ui_widget": "number"},
    )
    llm_weight: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Weight for LLM-based ATDD eligibility assessment",
        json_schema_extra={"security": "safe", "ui_widget": "number"},
    )
    threshold: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Score threshold to enable ATDD in auto mode",
        json_schema_extra={"security": "safe", "ui_widget": "number"},
    )

    @model_validator(mode="after")
    def validate_weights_sum(self) -> Self:
        """Ensure keyword and LLM weights sum to 1.0 (with epsilon tolerance)."""
        total = self.keyword_weight + self.llm_weight
        if abs(total - 1.0) > 0.001:
            raise ValueError("eligibility weights must sum to 1.0")
        return self


class PreflightConfig(BaseModel):
    """Preflight check configuration for test infrastructure.

    Controls which preflight checks are run before ATDD execution.
    Each check verifies and optionally initializes test infrastructure.

    Attributes:
        test_design: Check/initialize test-design-system.md.
        framework: Check/initialize Playwright/Cypress config.
        ci: Check/initialize CI pipeline.

    """

    model_config = ConfigDict(frozen=True)

    test_design: bool = Field(
        default=True,
        description="Check/initialize test-design-system.md",
        json_schema_extra={"security": "safe", "ui_widget": "toggle"},
    )
    framework: bool = Field(
        default=True,
        description="Check/initialize Playwright/Cypress config",
        json_schema_extra={"security": "safe", "ui_widget": "toggle"},
    )
    ci: bool = Field(
        default=True,
        description="Check/initialize CI pipeline",
        json_schema_extra={"security": "safe", "ui_widget": "toggle"},
    )


class TestarchConfig(BaseModel):
    """Testarch module configuration.

    Root configuration for the Test Architect module, which integrates
    ATDD (Acceptance Test Driven Development) into the bmad-assist loop.

    Attributes:
        atdd_mode: ATDD operation mode (off/auto/on).
        eligibility: ATDD eligibility scoring configuration.
        preflight: Preflight infrastructure check configuration.
        playwright: Playwright browser testing configuration (optional).
        trace_on_epic_complete: Trace generation on epic completion.
        test_review_on_code_complete: Test quality review on code completion.

    """

    __test__ = False  # Tell pytest this is not a test class
    model_config = ConfigDict(frozen=True)

    atdd_mode: Literal["off", "auto", "on"] = Field(
        default="auto",
        description=(
            "ATDD operation mode: "
            "off=skip ATDD for all stories; "
            "auto=detect story eligibility using hybrid scoring; "
            "on=run ATDD for every story"
        ),
        json_schema_extra={"security": "safe", "ui_widget": "dropdown"},
    )
    eligibility: EligibilityConfig = Field(
        default_factory=EligibilityConfig,
        description="ATDD eligibility scoring configuration",
    )
    preflight: PreflightConfig = Field(
        default_factory=PreflightConfig,
        description="Preflight infrastructure check configuration",
    )
    playwright: PlaywrightConfig | None = Field(
        default=None,
        description="Playwright browser testing configuration (optional)",
    )
    trace_on_epic_complete: Literal["off", "auto", "on"] = Field(
        default="auto",
        description=(
            "Trace generation on epic completion: "
            "off=never run trace; "
            "auto=run if ATDD was used in epic; "
            "on=always run trace"
        ),
        json_schema_extra={"security": "safe", "ui_widget": "dropdown"},
    )
    test_review_on_code_complete: Literal["off", "auto", "on"] = Field(
        default="auto",
        description=(
            "Test quality review on code completion: "
            "off=never run test review; "
            "auto=run if ATDD was used for story; "
            "on=always run test review"
        ),
        json_schema_extra={"security": "safe", "ui_widget": "dropdown"},
    )
