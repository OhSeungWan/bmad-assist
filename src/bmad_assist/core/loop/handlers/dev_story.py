"""DEV_STORY phase handler.

Master LLM implements the story following TDD principles.

"""

from typing import Any

from bmad_assist.core.loop.handlers.base import BaseHandler
from bmad_assist.core.state import State


class DevStoryHandler(BaseHandler):
    """Handler for DEV_STORY phase.

    Invokes Master LLM to implement the story.

    """

    @property
    def phase_name(self) -> str:
        """Returns the name of the phase."""
        return "dev_story"

    @property
    def track_timing(self) -> bool:
        """Enable timing tracking for this handler."""
        return True

    @property
    def timing_workflow_id(self) -> str:
        """Workflow ID for timing records."""
        return "dev-story"

    def build_context(self, state: State) -> dict[str, Any]:
        """Build context for dev_story prompt template.

        Available variables: epic_num, story_num, story_id, project_path

        """
        return self._build_common_context(state)
