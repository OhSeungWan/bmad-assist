"""QA plan generation and execution module.

Provides automatic generation and execution of E2E test plans for completed epics.
Supports batch execution mode for large test sets (>10 tests) to prevent context
overflow and enable crash recovery with incremental saves.
"""

from bmad_assist.qa.batch_executor import (
    DEFAULT_BATCH_SIZE,
    BatchResult,
    ExecutionState,
    TestResult,
    execute_batch,
    execute_tests_in_batches,
)
from bmad_assist.qa.checker import check_missing_qa_plans, get_qa_plan_path
from bmad_assist.qa.executor import BATCH_THRESHOLD, QAExecuteResult, execute_qa_plan
from bmad_assist.qa.generator import generate_qa_plan
from bmad_assist.qa.parser import ParsedTestPlan, TestCase, parse_test_plan, parse_test_plan_file

__all__ = [
    # Constants
    "BATCH_THRESHOLD",
    "DEFAULT_BATCH_SIZE",
    # Checker
    "check_missing_qa_plans",
    "get_qa_plan_path",
    # Executor
    "execute_qa_plan",
    "QAExecuteResult",
    # Batch executor
    "execute_batch",
    "execute_tests_in_batches",
    "BatchResult",
    "ExecutionState",
    "TestResult",
    # Generator
    "generate_qa_plan",
    # Parser
    "parse_test_plan",
    "parse_test_plan_file",
    "ParsedTestPlan",
    "TestCase",
]
