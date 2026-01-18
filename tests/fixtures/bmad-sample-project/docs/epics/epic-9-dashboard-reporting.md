# Epic 9: Dashboard & Reporting

**Goal:** Developer can view progress via HTML dashboard and access detailed reports - full visibility into the development process.

**FRs:** FR39, FR40, FR41, FR42, FR43, FR44

## Story 9.1: Dashboard HTML Template

**As a** developer,
**I want** a Jinja2 HTML template for the dashboard,
**So that** dashboard generation is maintainable and customizable.

**Acceptance Criteria:**

**Given** `templates/dashboard.html` exists
**When** template is loaded
**Then** it contains Jinja2 variables for: progress, metrics, anomalies
**And** pure HTML/CSS (no JavaScript frameworks)
**And** responsive layout for desktop viewing

**FRs:** FR39
**Estimate:** 2 SP

---

## Story 9.2: Dashboard Data Model

**As a** developer,
**I want** a data model for dashboard content,
**So that** dashboard generation has structured input.

**Acceptance Criteria:**

**Given** DashboardData model exists
**When** model is populated
**Then** it contains: epics_progress, stories_completed_today, test_count, coverage_percent, top_files, anomaly_list
**And** all fields have type hints
**And** model can be serialized to dict for Jinja2

**FRs:** FR41, FR42
**Estimate:** 2 SP

---

## Story 9.3: Dashboard Generation

**As a** developer,
**I want** to generate HTML dashboard from current state,
**So that** progress is visible at any time.

**Acceptance Criteria:**

**Given** current state and metrics are available
**When** `generate_dashboard()` is called
**Then** Jinja2 template is rendered with data
**And** HTML is written to configured output path
**And** dashboard is self-contained (no external dependencies)

**Given** dashboard already exists
**When** new dashboard is generated
**Then** previous dashboard is overwritten atomically

**FRs:** FR39
**Estimate:** 2 SP

---

## Story 9.4: Phase Completion Dashboard Update

**As a** developer,
**I want** dashboard updated after each phase completion,
**So that** progress is always current.

**Acceptance Criteria:**

**Given** phase completes successfully
**When** state is saved
**Then** dashboard is regenerated automatically
**And** update is logged

**Given** phase fails or anomaly occurs
**When** state is saved
**Then** dashboard still updates with current status
**And** anomaly is visible in dashboard

**FRs:** FR40
**Estimate:** 1 SP

---

## Story 9.5: Progress Metrics Display

**As a** developer,
**I want** dashboard to display key progress metrics,
**So that** I can quickly assess project status.

**Acceptance Criteria:**

**Given** dashboard is generated
**When** dashboard is viewed
**Then** it displays: stories completed per day (chart/table), total test count, coverage percentage, top 10 largest files by lines
**And** metrics are clearly labeled
**And** visual hierarchy highlights important metrics

**FRs:** FR41
**Estimate:** 3 SP

---

## Story 9.6: Anomaly History Display

**As a** developer,
**I want** dashboard to display anomaly history with status,
**So that** I can track anomalies and their resolutions.

**Acceptance Criteria:**

**Given** anomalies have occurred
**When** dashboard is viewed
**Then** anomaly list shows: timestamp, type, epic/story, status (pending/resolved)
**And** resolved anomalies show resolution summary
**And** pending anomalies are highlighted

**Given** no anomalies have occurred
**When** dashboard is viewed
**Then** "No anomalies" message is displayed

**FRs:** FR42
**Estimate:** 2 SP

---

## Story 9.7: Code Review Report Generation

**As a** developer,
**I want** code review results saved as markdown reports,
**So that** review history is preserved and searchable.

**Acceptance Criteria:**

**Given** code review phase completes
**When** report is generated
**Then** markdown file is saved to `{{sprint_artifacts}}/code-reviews/code-review-{{epic}}-{{story}}-{{model}}-{{timestamp}}.md`
**And** report includes: reviewers (models), model output

**Given** multiple code reviews exist for same story
**When** reports are listed
**Then** each review is separate file with unique timestamp

**FRs:** FR43
**Estimate:** 2 SP

---

## Story 9.8: Story Validation Report Generation

**As a** developer,
**I want** story validation results saved as markdown reports,
**So that** validation history is preserved.

**Acceptance Criteria:**

**Given** story validation phase completes
**When** report is generated
**Then** markdown file is saved to `{{sprint_artifacts}}/story-validations/story-validation-{{epic}}-{{story}}-{{model}}-{{timestamp}}.md`
**And** report includes: validators (models), model output

**FRs:** FR44
**Estimate:** 2 SP

---

**Epic 9 Total:** 8 stories, 16 SP

---
