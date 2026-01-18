"""Workflow-specific compiler modules.

Each workflow (create-story, validate-story, etc.) has its own module
in this package implementing the WorkflowCompiler protocol.

Available workflows:
- create_story: Compiler for the create-story workflow
- validate_story: Compiler for adversarial story validation (Multi-LLM)
- validate_story_synthesis: Compiler for Master synthesis of validator findings
- code_review: Compiler for adversarial code review (Multi-LLM)
- code_review_synthesis: Compiler for Master synthesis of code review findings
- dev_story: Compiler for story development workflow
- retrospective: Compiler for epic retrospective workflow
- testarch_atdd: Compiler for ATDD (Acceptance Test Driven Development) workflow
- testarch_trace: Compiler for traceability matrix and quality gate workflow
- testarch_test_review: Compiler for test quality review workflow
- qa_plan_generate: Compiler for QA plan generation workflow
- qa_plan_execute: Compiler for QA plan execution workflow

Note: metrics-extraction is now embedded directly in bmad_assist.benchmarking.extraction
to eliminate BMAD workflow dependencies and ensure version-agnostic operation.
"""
