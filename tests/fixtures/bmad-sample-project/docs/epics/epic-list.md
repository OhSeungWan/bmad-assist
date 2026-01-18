# Epic List

## Epic 1: Project Foundation & CLI Infrastructure
Developer can install and run bmad-assist with basic CLI, configuration loads correctly, project structure is ready for development.
**FRs covered:** FR35, FR36, FR37, FR38
**NFRs addressed:** NFR8, NFR9

## Epic 2: BMAD File Integration
System can read and understand BMAD project files (PRD, architecture, epics, stories) without LLM, enabling accurate project state tracking.
**FRs covered:** FR26, FR27, FR28, FR29, FR30
**NFRs addressed:** NFR6

## Epic 3: State Management & Crash Resilience
System maintains persistent state, survives crashes, and can resume work from last checkpoint - enabling fire-and-forget operation.
**FRs covered:** FR4, FR5, FR31, FR32, FR33, FR34
**NFRs addressed:** NFR1, NFR2

## Epic 4: CLI Provider Integration
System can invoke external LLM CLI tools (Claude Code, Codex, Gemini CLI), capture outputs, and handle errors - the foundation for all LLM operations.
**FRs covered:** FR6, FR7, FR8, FR9, FR10
**NFRs addressed:** NFR3, NFR5, NFR7

## Epic 5: Power-Prompts Engine
System can load and inject context-aware prompts with dynamic variables, enhancing BMAD workflow invocations with project-specific quality standards.
**FRs covered:** FR22, FR23, FR24, FR25

## Epic 6: Main Loop Orchestration
System executes the complete development cycle (create story → validate → develop → code review → retrospective), automatically transitioning between stories and epics.
**FRs covered:** FR1, FR2, FR3

## Epic 7: Multi-LLM Validation & Synthesis
System invokes multiple LLMs for validation, collects reports, and Master LLM synthesizes findings - delivering comprehensive code quality assurance.
**FRs covered:** FR11, FR12, FR13, FR14, FR15

## Epic 8: Anomaly Guardian
System detects unusual LLM outputs, pauses when needed, allows user intervention, and saves resolutions for future learning - enabling intelligent fallback.
**FRs covered:** FR16, FR17, FR18, FR19, FR20, FR21
**NFRs addressed:** NFR4

## Epic 9: Dashboard & Reporting
Developer can view progress via HTML dashboard and access detailed reports - full visibility into the development process.
**FRs covered:** FR39, FR40, FR41, FR42, FR43, FR44

---
