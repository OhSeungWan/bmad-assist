"""Reporting module for dashboard generation and metrics.

Provides:
- DashboardData, ProgressData, MetricsData, AnomalyItem: Pydantic models
- generate_dashboard(): HTML dashboard generator

"""

from bmad_assist.reporting.generator import generate_dashboard
from bmad_assist.reporting.models import (
    AnomalyItem,
    CurrentEpic,
    CurrentStory,
    DashboardData,
    MetricsData,
    ProgressData,
    TopFile,
)

__all__ = [
    "AnomalyItem",
    "CurrentEpic",
    "CurrentStory",
    "DashboardData",
    "MetricsData",
    "ProgressData",
    "TopFile",
    "generate_dashboard",
]
