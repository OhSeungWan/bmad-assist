"""Dashboard HTML generator."""

import os
import tempfile
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from bmad_assist.reporting.models import DashboardData


def generate_dashboard(dashboard_data: DashboardData, output_path: Path) -> None:
    """Generate an HTML dashboard from DashboardData.

    The write operation is atomic using temp file + rename pattern.

    Args:
        dashboard_data: Dashboard data to render.
        output_path: Path to write the HTML file.

    """
    template_dir = Path(__file__).parent.parent / "prompts"
    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template("dashboard.html")

    html_content = template.render(
        generated_at=dashboard_data.generated_at,
        progress=dashboard_data.progress,
        metrics=dashboard_data.metrics,
        anomalies=dashboard_data.anomalies,
    )

    # Atomic write
    with tempfile.NamedTemporaryFile(
        mode="w", delete=False, encoding="utf-8", dir=output_path.parent
    ) as temp_file:
        temp_file.write(html_content)
    os.rename(temp_file.name, output_path)


if __name__ == "__main__":
    # Example usage for testing
    from datetime import datetime

    from bmad_assist.reporting.models import (
        AnomalyItem,
        CurrentEpic,
        CurrentStory,
        MetricsData,
        ProgressData,
        TopFile,
    )

    # Example Data
    example_progress = ProgressData(
        current_phase="Development",
        total_epics=5,
        completed_epics=2,
        current_epic=CurrentEpic(id="E123", name="Feature X"),
        current_story=CurrentStory(id="S456", name="Implement Login"),
        stories_completed_today=3,
    )

    example_metrics = MetricsData(
        total_test_count=150,
        coverage_percent=85.5,
        top_files=[
            TopFile(path="src/main.py", lines=500),
            TopFile(path="src/utils.py", lines=300),
        ],
    )

    example_anomalies = [
        AnomalyItem(
            timestamp=datetime(2025, 12, 17, 10, 0, 0),
            type="LLM_Response_Format_Error",
            epic_id="E123",
            story_id="S456",
            status="Pending",
            resolution_summary=None,
        ),
        AnomalyItem(
            timestamp=datetime(2025, 12, 16, 14, 30, 0),
            type="Provider_Timeout",
            epic_id="E122",
            story_id="S455",
            status="Resolved",
            resolution_summary="Increased timeout configuration for Claude provider.",
        ),
    ]

    example_dashboard_data = DashboardData(
        progress=example_progress,
        metrics=example_metrics,
        anomalies=example_anomalies,
    )

    # Define a temporary output path for demonstration
    temp_output_dir = Path("/tmp/bmad_dashboard_test")
    temp_output_dir.mkdir(exist_ok=True)
    output_html_path = temp_output_dir / "dashboard.html"

    print(f"Generating dashboard to: {output_html_path}")
    generate_dashboard(example_dashboard_data, output_html_path)
    print("Dashboard generated successfully.")
    print(f"You can view it by opening {output_html_path} in your browser.")
