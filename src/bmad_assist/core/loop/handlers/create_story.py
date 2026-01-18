"""CREATE_STORY phase handler.

Creates a new story file based on epic requirements using the Master LLM.

"""

from typing import Any

from bmad_assist.core.loop.handlers.base import BaseHandler
from bmad_assist.core.state import State


class CreateStoryHandler(BaseHandler):
    """Handler for CREATE_STORY phase.

    Invokes Master LLM to generate a new story file from epic context.

    """

    @property
    def phase_name(self) -> str:
        """Returns the name of the phase."""
        return "create_story"

    @property
    def track_timing(self) -> bool:
        """Enable timing tracking for this handler."""
        return True

    @property
    def timing_workflow_id(self) -> str:
        """Workflow ID for timing records."""
        return "create-story"

    def build_context(self, state: State) -> dict[str, Any]:
        """Build context for create_story prompt template.

        Available variables: epic_num, story_num, story_id, project_path

        """
        return self._build_common_context(state)
