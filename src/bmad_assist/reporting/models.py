"""Dashboard data models for reporting."""

from datetime import datetime

from pydantic import BaseModel, Field


class CurrentEpic(BaseModel):
    """Current epic information for dashboard display."""

    id: str
    name: str


class CurrentStory(BaseModel):
    """Current story information for dashboard display."""

    id: str
    name: str


class ProgressData(BaseModel):
    """Progress tracking data for dashboard."""

    current_phase: str
    total_epics: int
    completed_epics: int
    current_epic: CurrentEpic | None = None
    current_story: CurrentStory | None = None
    stories_completed_today: int


class TopFile(BaseModel):
    """File information for code metrics display."""

    path: str
    lines: int


class MetricsData(BaseModel):
    """Code quality metrics for dashboard."""

    total_test_count: int
    coverage_percent: float
    top_files: list[TopFile]


class AnomalyItem(BaseModel):
    """Anomaly record for Guardian tracking."""

    timestamp: datetime
    type: str
    epic_id: str
    story_id: str
    status: str  # e.g., "pending", "resolved"
    resolution_summary: str | None = None


class DashboardData(BaseModel):
    """Complete dashboard data model."""

    generated_at: datetime = Field(default_factory=datetime.now)
    progress: ProgressData
    metrics: MetricsData
    anomalies: list[AnomalyItem]
