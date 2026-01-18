"""Sprint status management module.

This module provides comprehensive sprint-status management including:
- Entry type classification for merge/reconciliation decisions
- Canonical Pydantic models for normalized sprint-status representation
- Schema-tolerant parsing of multiple sprint-status format variants
- Artifact scanning for stories, code reviews, validations, retrospectives
- Evidence-based status inference from project artifacts
- Reconciliation engine for 3-way merge operations
- Atomic writes with comment preservation
- State-to-SprintStatus synchronization
- Interactive repair dialog for high divergence scenarios

Public API:
    - EntryType: Enum for sprint-status entry classification
    - classify_entry: Function to classify entries by key pattern
    - SprintStatusMetadata: Metadata header fields model
    - SprintStatusEntry: Single status entry model
    - SprintStatus: Container model with entries and helpers
    - FormatVariant: Enum for detected sprint-status format types
    - detect_format: Function to determine format variant from data
    - parse_sprint_status: Main entry point for parsing sprint-status files
    - ArtifactIndex: Container with indexed artifacts and query methods
    - StoryArtifact: Dataclass for story file metadata
    - CodeReviewArtifact: Dataclass for code review file metadata
    - ValidationArtifact: Dataclass for validation report metadata
    - RetrospectiveArtifact: Dataclass for retrospective file metadata
    - InferenceConfidence: Enum for confidence levels in status inference
    - InferenceResult: Dataclass for inference results with evidence
    - infer_story_status: Infer story status from artifacts
    - infer_story_status_detailed: Infer with full evidence audit trail
    - infer_epic_status: Infer epic status from story statuses
    - infer_all_statuses: Batch inference for all stories
    - StatusChange: Record of a single status change during reconciliation
    - ReconciliationResult: Full result with merged status and change log
    - ConflictResolution: Enum for conflict resolution strategies
    - reconcile: Main entry point for 3-way merge reconciliation
    - SyncResult: Dataclass with state-to-sprint sync statistics
    - SyncCallback: Type alias for sync callback functions
    - PHASE_TO_STATUS: Mapping from Phase to ValidStatus
    - sync_state_to_sprint: Core sync function
    - trigger_sync: Convenience function for full sync cycle
    - register_sync_callback: Register callback for after-save hooks
    - clear_sync_callbacks: Clear callbacks for test isolation
    - invoke_sync_callbacks: Invoke all registered callbacks
    - RepairSummary: Summary of proposed repair changes for dialog
    - RepairDialogResult: Result of repair confirmation dialog
    - RepairDialog: Protocol for dialog implementations
    - CLIRepairDialog: CLI dialog with Rich formatting and timeout
    - DashboardRepairDialog: Auto-cancel placeholder for dashboard
    - get_repair_dialog: Factory for getting dialog by context
"""

from .classifier import EntryType, classify_entry
from .dialog import (
    CLIRepairDialog,
    DashboardRepairDialog,
    RepairDialog,
    RepairDialogResult,
    RepairSummary,
    get_repair_dialog,
)
from .generator import (
    GeneratedEntries,
    generate_from_epics,
    generate_story_key,
    generate_story_slug,
)
from .inference import (
    InferenceConfidence,
    InferenceResult,
    infer_all_statuses,
    infer_epic_status,
    infer_story_status,
    infer_story_status_detailed,
)
from .models import (
    SprintStatus,
    SprintStatusEntry,
    SprintStatusMetadata,
    ValidStatus,
)
from .parser import FormatVariant, detect_format, parse_sprint_status
from .reconciler import (
    ConflictResolution,
    ReconciliationResult,
    StatusChange,
    reconcile,
)
from .repair import (
    RepairMode,
    RepairResult,
    ensure_sprint_sync_callback,
    repair_sprint_status,
)
from .scanner import (
    ArtifactIndex,
    CodeReviewArtifact,
    RetrospectiveArtifact,
    StoryArtifact,
    ValidationArtifact,
)
from .sync import (
    PHASE_TO_STATUS,
    SyncCallback,
    SyncResult,
    clear_sync_callbacks,
    get_sync_callbacks,
    invoke_sync_callbacks,
    register_sync_callback,
    sync_state_to_sprint,
    trigger_sync,
)
from .writer import has_ruamel, write_sprint_status

__all__ = [
    "EntryType",
    "classify_entry",
    "GeneratedEntries",
    "generate_from_epics",
    "generate_story_key",
    "generate_story_slug",
    "SprintStatusMetadata",
    "SprintStatusEntry",
    "SprintStatus",
    "ValidStatus",
    "FormatVariant",
    "detect_format",
    "parse_sprint_status",
    "ArtifactIndex",
    "StoryArtifact",
    "CodeReviewArtifact",
    "ValidationArtifact",
    "RetrospectiveArtifact",
    "InferenceConfidence",
    "InferenceResult",
    "infer_story_status",
    "infer_story_status_detailed",
    "infer_epic_status",
    "infer_all_statuses",
    "StatusChange",
    "ReconciliationResult",
    "ConflictResolution",
    "reconcile",
    "has_ruamel",
    "write_sprint_status",
    # Sync module (Story 20.9)
    "SyncResult",
    "SyncCallback",
    "PHASE_TO_STATUS",
    "sync_state_to_sprint",
    "trigger_sync",
    "register_sync_callback",
    "clear_sync_callbacks",
    "invoke_sync_callbacks",
    "get_sync_callbacks",
    # Repair module (Story 20.10)
    "RepairMode",
    "RepairResult",
    "repair_sprint_status",
    "ensure_sprint_sync_callback",
    # Dialog module (Story 20.12)
    "RepairSummary",
    "RepairDialogResult",
    "RepairDialog",
    "CLIRepairDialog",
    "DashboardRepairDialog",
    "get_repair_dialog",
]
