"""BMAD file parsing, state reconciliation, and discrepancy correction module.

Provides functionality to parse BMAD markdown files with YAML frontmatter
without requiring LLM invocation, detect discrepancies between internal
state and BMAD files, and correct those discrepancies.

The module is organized into:

- parser: BMAD markdown file parsing with frontmatter
- state_reader: Project state reading from BMAD files
- discrepancy: Discrepancy detection between internal state and BMAD files
- correction: Discrepancy correction by updating BMAD files
- reconciler: Re-exports all public APIs for backwards compatibility

Example usage:
    >>> from bmad_assist.bmad import (
    ...     parse_bmad_file,
    ...     read_project_state,
    ...     detect_discrepancies,
    ...     correct_all_discrepancies,
    ... )

"""

from .correction import (
    ConfirmCallback,
    CorrectionAction,
    CorrectionResult,
    correct_all_discrepancies,
    correct_discrepancy,
)
from .discrepancy import (
    Discrepancy,
    StateComparable,
    detect_discrepancies,
)
from .parser import (
    BmadDocument,
    EpicDocument,
    EpicStory,
    parse_bmad_file,
    parse_epic_file,
)
from .state_reader import (
    ProjectState,
    read_project_state,
)

__all__ = [
    # parser
    "BmadDocument",
    "EpicDocument",
    "EpicStory",
    "parse_bmad_file",
    "parse_epic_file",
    # state_reader
    "ProjectState",
    "read_project_state",
    # discrepancy
    "Discrepancy",
    "StateComparable",
    "detect_discrepancies",
    # correction
    "ConfirmCallback",
    "CorrectionAction",
    "CorrectionResult",
    "correct_all_discrepancies",
    "correct_discrepancy",
]
