# Experiments

The experiment framework enables systematic LLM comparison through controlled execution of BMAD workflows. It isolates fixtures, tracks metrics, and generates comparison reports to answer questions about model performance, prompt effectiveness, and workflow optimization.

## Problem

When optimizing bmad-assist workflows, you need answers to:
- Which LLM model produces better stories or code reviews?
- Does a new prompt patch improve quality or introduce regressions?
- How do different workflow sequences affect outcomes?
- What's the cost/token tradeoff between configurations?

Without controlled experiments, comparing configurations requires manual execution and subjective analysis.

## Solution

The experiment framework provides:
- **Four-axis configuration**: Fixture × Config × Patch-Set × Loop defines each experiment
- **Fixture isolation**: Deep copy ensures reproducibility and prevents cross-contamination
- **Automatic metrics collection**: Duration, tokens, cost, success rates tracked per phase
- **Manifest persistence**: Complete configuration and results captured for audit
- **Comparison reports**: Statistical comparison across runs with winner determination

## Directory Structure

Experiments require a specific directory structure in your project:

```
experiments/
├── configs/               # Config templates (LLM provider settings)
│   ├── opus-solo.yaml
│   ├── haiku-solo.yaml
│   └── opus-full.yaml
├── loops/                 # Loop templates (workflow sequences)
│   ├── fast.yaml
│   ├── standard.yaml
│   └── atdd.yaml
├── patch-sets/            # Patch-set manifests (prompt customizations)
│   ├── baseline.yaml
│   └── no-patches.yaml
├── fixtures/              # Test subject projects
│   ├── webhook-relay-001/
│   ├── simple-portfolio/
│   └── *.tar              # Archived fixtures (extracted on use)
└── runs/                  # Experiment outputs (auto-created)
    ├── run-2026-02-03-001/
    ├── run-2026-02-03-002/
    └── ...
```

Initialize this structure manually or copy from an existing bmad-assist installation.

## Config Templates

Config templates define which LLM providers to use. Location: `experiments/configs/`

### Schema

```yaml
name: opus-solo                           # Must match filename (opus-solo.yaml)
description: "Opus-only baseline"         # Human-readable description

providers:
  master:                                  # Master LLM (required)
    provider: claude-subprocess           # Provider identifier
    model: opus                           # Model identifier
    model_name: "Claude Opus"             # Display name (optional)
    settings: ~/.claude/opus.json         # Settings file path (optional)

  multi:                                   # Multi-LLM validators (optional)
    - provider: gemini
      model: gemini-2.5-flash
    - provider: codex
      model: gpt-4
```

### Supported Providers

| Provider ID | Description |
|-------------|-------------|
| `claude-subprocess` | Claude CLI with --print flag |
| `claude-sdk` | Claude SDK (primary) |
| `gemini` | Google Gemini CLI |
| `codex` | OpenAI Codex |
| `opencode` | OpenCode CLI |
| `amp` | Amp CLI |
| `copilot` | GitHub Copilot |
| `cursor-agent` | Cursor Agent |
| `kimi` | Kimi CLI (MoonshotAI) |

### Variable Resolution

Config files support variables in string values:
- `${home}` - User home directory
- `${project}` - Project root (requires `--project` flag)

Example:
```yaml
providers:
  master:
    settings: ${home}/.claude/custom.json
```

## Loop Templates

Loop templates define workflow execution sequence. Location: `experiments/loops/`

### Schema

```yaml
name: standard
description: "Full BMAD loop with validation and review"

sequence:
  - workflow: create-story
    required: true           # Failure stops experiment
  - workflow: validate-story
    required: true
  - workflow: validate-story-synthesis
    required: false          # Optional - failure logged but continues
  - workflow: dev-story
    required: true
  - workflow: code-review
    required: true
  - workflow: code-review-synthesis
    required: false
```

### Supported Workflows

| Workflow | Phase Mapping | Description |
|----------|---------------|-------------|
| `create-story` | CREATE_STORY | Story generation from epic |
| `validate-story` | VALIDATE_STORY | Multi-LLM story validation |
| `validate-story-synthesis` | VALIDATE_STORY_SYNTHESIS | Validation consensus |
| `dev-story` | DEV_STORY | Implementation phase |
| `code-review` | CODE_REVIEW | Multi-LLM code review |
| `code-review-synthesis` | CODE_REVIEW_SYNTHESIS | Review consensus |
| `retrospective` | RETROSPECTIVE | Epic retrospective |
| `atdd` | ATDD | Test-driven development |
| `test-review` | TEST_REVIEW | Test review phase |
| `test-design` | (custom) | ATDD test planning |
| `qa-plan-generate` | QA_PLAN_GENERATE | QA test plan generation |
| `qa-plan-execute` | QA_PLAN_EXECUTE | QA test execution |

Workflow names accept both kebab-case (`create-story`) and snake_case (`create_story`).

## Patch-Set Manifests

Patch-sets define which prompt patches to apply. Location: `experiments/patch-sets/`

### Schema

```yaml
name: baseline
description: "Production patches from project"

patches:
  create-story: ${project}/.bmad-assist/patches/create-story.patch.yaml
  validate-story: ${project}/.bmad-assist/patches/validate-story.patch.yaml
  dev-story: null           # null = no patch, use raw workflow
  code-review: ${project}/.bmad-assist/patches/code-review.patch.yaml

workflow_overrides:          # Alternative workflow implementations (optional)
  atdd: /path/to/custom-atdd-workflow/
```

### Patch Resolution

1. If `workflow_overrides[workflow]` exists, use that directory
2. If `patches[workflow]` is a path, copy patch to fixture snapshot
3. If `patches[workflow]` is `null`, use raw BMAD workflow (no patch)
4. If workflow not listed, no patch applied

## Fixtures

Fixtures are complete project directories for experiment execution. Location: `experiments/fixtures/`

### Discovery

Fixtures are discovered by scanning for **directories** (not files):
- Only subdirectories of `experiments/fixtures/` are considered
- Tar archives (`.tar`, `.tar.gz`, `.tar.bz2`) are extracted on use
- Hidden directories (`.hidden-*`) are ignored
- Directory name becomes fixture ID (must match pattern `^[a-zA-Z_][a-zA-Z0-9_-]*$`)

### Optional Metadata

Add a `.bmad-assist.yaml` or `bmad-assist.yaml` in fixture root:

```yaml
fixture:
  name: "Auth Microservice"           # Display name (defaults to directory name)
  description: "E-commerce auth API"  # Human-readable description
  tags:                               # Categorization tags
    - go
    - microservices
    - quick
  difficulty: medium                  # easy | medium | hard
  estimated_cost: "$0.50"             # Must match $X.XX pattern
```

If no metadata file exists, defaults are used (ID as name, empty description/tags).

### Fixture Structure

A well-formed fixture includes:

```
my-fixture/
├── .bmad-assist.yaml          # Optional metadata
├── bmad-assist.yaml           # Project config (required for loop)
├── docs/
│   ├── prd.md
│   ├── architecture.md
│   └── epics/
│       └── epic-1.md
├── _bmad/                     # BMAD module config
│   └── bmm/
│       └── config.yaml
├── _bmad-output/              # Implementation artifacts
│   └── implementation-artifacts/
│       ├── sprint-status.yaml
│       └── stories/
└── [source code]              # Language-specific source
```

## CLI Commands

### Run Single Experiment

Execute one experiment with specified configuration:

```bash
bmad-assist experiment run \
  -f minimal \              # Fixture ID
  -c opus-solo \            # Config template
  -P baseline \             # Patch-set manifest
  -l standard               # Loop template
```

**Options:**

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `-f`, `--fixture` | string | required | Fixture ID |
| `-c`, `--config` | string | required | Config template name |
| `-P`, `--patch-set` | string | required | Patch-set manifest name |
| `-l`, `--loop` | string | required | Loop template name |
| `-p`, `--project` | path | `.` | Project directory |
| `-o`, `--output-dir` | path | auto | Custom output directory |
| `-v`, `--verbose` | flag | false | Enable debug logging |
| `-n`, `--dry-run` | flag | false | Validate without executing |
| `--qa` | flag | false | Include Playwright tests |
| `--fail-fast` | flag | false | Stop on first story failure |

**QA Modes:**
- Without `--qa`: Runs CLI tests only (category A)
- With `--qa`: Runs CLI + Playwright tests (category A+B)

**Exit Codes:**
- `0` - Experiment completed successfully
- `1` - Runtime error or experiment failed
- `2` - Configuration error (missing template, invalid name)

### Batch Experiments

Run multiple experiments (cartesian product of fixtures × configs):

```bash
bmad-assist experiment batch \
  --fixtures minimal,complex \
  --configs opus-solo,haiku-solo \
  --patch-set baseline \
  --loop standard
```

**Options:**

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--fixtures` | string | required | Comma-separated fixture IDs |
| `--configs` | string | required | Comma-separated config names |
| `--patch-set` | string | required | Patch-set for all runs |
| `--loop` | string | required | Loop template for all runs |
| `-j`, `--parallel` | int | 1 | Concurrent runs (1-4, MVP: sequential only) |
| `-n`, `--dry-run` | flag | false | Show combinations without running |

Batch mode runs experiments sequentially. Failed experiments are logged but don't stop the batch.

### List Runs

Display completed experiment runs:

```bash
# List all runs
bmad-assist experiment list

# Filter by status and fixture
bmad-assist experiment list --status completed --fixture minimal

# Limit results
bmad-assist experiment list -n 10
```

**Options:**

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `-s`, `--status` | string | all | Filter: completed, failed, cancelled, running, pending |
| `-f`, `--fixture` | string | all | Filter by fixture name |
| `-c`, `--config` | string | all | Filter by config name |
| `-n`, `--limit` | int | 20 | Maximum runs to display |

### Show Run Details

Display detailed information for a specific run:

```bash
bmad-assist experiment show run-2026-02-03-001
```

Output includes:
- Status and timing
- Configuration (fixture, config, patch-set, loop)
- Results summary (stories attempted/completed/failed)
- Metrics (total cost, tokens, duration)
- Phase-by-phase breakdown table

### Compare Runs

Generate comparison report for 2-10 runs:

```bash
# Compare two runs, output to stdout
bmad-assist experiment compare run-001 run-002

# Compare three runs, save to file
bmad-assist experiment compare run-001 run-002 run-003 \
  --output comparison.md

# JSON output for programmatic use
bmad-assist experiment compare run-001 run-002 \
  --format json -o comparison.json
```

**Options:**

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `-o`, `--output` | path | stdout | Output file path |
| `-f`, `--format` | string | markdown | Output format: markdown or json |

**Comparison Metrics:**

| Metric | Direction | Description |
|--------|-----------|-------------|
| `total_cost` | lower better | Total API cost |
| `total_tokens` | lower better | Total tokens used |
| `total_duration_seconds` | lower better | Total execution time |
| `stories_completed` | higher better | Successfully completed stories |
| `stories_failed` | lower better | Failed stories |
| `success_rate` | higher better | completed / (completed + failed) |

### List Templates

Display available templates across all axes:

```bash
# Show all templates
bmad-assist experiment templates

# Filter by type
bmad-assist experiment templates --type config
bmad-assist experiment templates --type loop
bmad-assist experiment templates --type patch-set
bmad-assist experiment templates --type fixture
```

## Run Output Structure

Each experiment creates a run directory:

```
experiments/runs/run-2026-02-03-001/
├── manifest.yaml             # Complete configuration and results
├── metrics.yaml              # Aggregated metrics
├── state.yaml                # Loop state (for crash recovery)
├── output/                   # Run output artifacts
└── fixture-snapshot/         # Isolated copy of fixture
    ├── .bmad-assist/
    │   └── patches/          # Patches copied here
    ├── _bmad/
    ├── _bmad-output/
    ├── docs/
    └── [source files]
```

### Manifest Schema

```yaml
run_id: run-2026-02-03-001
started: "2026-02-03T10:30:00+00:00"
completed: "2026-02-03T11:45:30+00:00"
status: completed                      # pending | running | completed | failed | cancelled
schema_version: "1.0"

input:                                  # What user requested
  fixture: minimal
  config: opus-solo
  patch_set: baseline
  loop: standard

resolved:                               # What was actually used (with paths)
  fixture:
    name: minimal
    source: /path/to/experiments/fixtures/minimal
    snapshot: ./fixture-snapshot
  config:
    name: opus-solo
    source: /path/to/experiments/configs/opus-solo.yaml
    providers:
      master:
        provider: claude-subprocess
        model: opus
      multi: []
  patch_set:
    name: baseline
    source: /path/to/experiments/patch-sets/baseline.yaml
    patches:
      create-story: /path/to/patches/create-story.patch.yaml
      dev-story: null
  loop:
    name: standard
    source: /path/to/experiments/loops/standard.yaml
    sequence:
      - create-story
      - validate-story
      - dev-story
      - code-review

results:
  stories_attempted: 2
  stories_completed: 2
  stories_failed: 0
  retrospective_completed: true
  qa_completed: false
  phases:
    - phase: create-story
      story: "1.1"
      epic: 1
      status: completed
      duration_seconds: 45.3
      tokens: 2500
      cost: 0.05
      error: null
    # ... more phases

metrics:
  total_cost: 0.47
  total_tokens: 15840
  total_duration_seconds: 342.5
  avg_tokens_per_phase: 1980.0
  avg_cost_per_phase: 0.059
```

### Metrics File

```yaml
run_id: run-2026-02-03-001
collected_at: "2026-02-03T11:46:00+00:00"

summary:
  total_cost: 0.47
  total_tokens: 15840
  total_duration_seconds: 342.5
  avg_tokens_per_phase: 1980.0
  avg_cost_per_phase: 0.059
  stories_completed: 2
  stories_failed: 0

phases:
  - phase: create-story
    story: "1.1"
    status: completed
    duration_seconds: 45.3
    tokens: 2500
    cost: 0.05
```

## Fixture Isolation

When an experiment runs, the fixture is deep-copied to prevent mutation:

### Isolation Process

1. Check for tar archive (`{fixture}.tar`, `.tar.gz`, `.tar.bz2`)
2. If tar exists: extract to `runs/{run_id}/fixture-snapshot/`
3. Otherwise: recursive directory copy with filters

### Skip Patterns

These directories and files are **not** copied:
- `.git/` - Git repository data
- `__pycache__/` - Python bytecode cache
- `.venv/` - Virtual environment
- `node_modules/` - Node.js dependencies
- `.pytest_cache/` - Pytest cache
- `*.pyc`, `*.pyo` - Python bytecode files

Dotfiles (`.gitignore`, `.env.example`) **are** copied.

### Symlink Handling

| Symlink Type | Behavior |
|--------------|----------|
| Internal (within fixture) | Dereferenced (content copied) |
| External (outside fixture) | Skipped with warning |
| Broken | Skipped with warning |
| Directory symlink | Recursively dereferenced |

### Verification

After copy, verification checks:
- File count matches source
- Total size matches source
- At least one `.md` or `.yaml` file exists (content validation)

## Quality Scorecards

Scorecards assess fixture quality after experiments. Location: `experiments/analysis/scorecards/`

### Generating Scorecards

```bash
bmad-assist test scorecard webhook-relay-001
```

### Scorecard Schema

```yaml
fixture: webhook-relay-001
generated_at: "2026-02-03T14:30:00+00:00"
generator_version: "1.0"
mode: automated

scores:
  completeness:                        # 25% weight
    weight: 25
    score: 22.5
    details:
      stories_completed:
        max: 10
        score: 10.0
        metric: "2/2"
      no_todos:
        max: 5
        score: 5.0
        metric: 0
      no_placeholders:
        max: 5
        score: 5.0
        patterns_found: []
      no_empty_files:
        max: 5
        score: 2.5
        metric: 1

  functionality:                       # 25% weight
    weight: 25
    score: 20.0
    details:
      build:
        max: 10
        score: 10.0
        success: true
        command: "go build ./..."
      unit_tests:
        max: 10
        score: 8.0
        metric: "8/10"
        passed: 8
        failed: 2
        skipped: 0
      behavior_tests:
        max: 5
        score: 2.0
        metric: "2/5"

  code_quality:                        # 20% weight
    weight: 20
    score: 16.0
    details:
      linting:
        max: 8
        score: 8.0
        tool: "go vet"
        errors: 0
        warnings: 2
      complexity:
        max: 6
        score: 5.0
        tool: "gocyclo"
        average: 4.2
        max_function: "handleWebhook:12"
      security:
        max: 6
        score: 3.0
        tool: "gosec"
        high: 0
        medium: 1
        low: 3

  documentation:                       # 15% weight
    weight: 15
    score: 12.0

  ui_ux:                               # 15% weight (skipped if N/A)
    weight: 15
    score: null
    applicable: false

totals:
  raw_score: 70.5
  max_possible: 85                     # 100 - 15 (ui_ux not applicable)
  weighted_score: 82.9
  grade: B

notes: "Good overall quality. Consider improving test coverage."
recommendations:
  - "Add tests for edge cases in handleWebhook"
  - "Fix medium-severity security finding in auth module"
```

## Python API

For programmatic experiment execution:

```python
from pathlib import Path
from bmad_assist.experiments import (
    ExperimentRunner,
    ExperimentInput,
    ExperimentOutput,
    ExperimentStatus,
    ComparisonGenerator,
    MetricsCollector,
    FixtureManager,
    ConfigRegistry,
    LoopRegistry,
    PatchSetRegistry,
)

# Initialize runner
experiments_dir = Path("experiments")
runner = ExperimentRunner(experiments_dir, project_root=Path("."))

# Run experiment
exp_input = ExperimentInput(
    fixture="minimal",
    config="opus-solo",
    patch_set="baseline",
    loop="standard",
    fail_fast=False,
)
output: ExperimentOutput = runner.run(exp_input)

print(f"Status: {output.status}")
print(f"Stories: {output.stories_completed}/{output.stories_attempted}")
print(f"Duration: {output.duration_seconds:.1f}s")

# Compare runs
generator = ComparisonGenerator(experiments_dir / "runs")
report = generator.compare(["run-001", "run-002"])
markdown = generator.generate_markdown(report)

# Load metrics
collector = MetricsCollector(experiments_dir / "runs" / "run-001")
metrics = collector.load()
print(f"Total cost: ${metrics.summary.total_cost:.2f}")

# List fixtures
fixtures = FixtureManager(experiments_dir / "fixtures")
for entry in fixtures.discover():
    print(f"{entry.id}: {entry.name} ({entry.difficulty})")

# Filter fixtures by tags
go_fixtures = fixtures.filter_by_tags(["go", "microservices"])
```

### Key Classes

| Class | Purpose |
|-------|---------|
| `ExperimentRunner` | Main orchestrator for experiment execution |
| `ExperimentInput` | Immutable input configuration |
| `ExperimentOutput` | Immutable results with status and metrics |
| `ConfigRegistry` | Discovers and loads config templates |
| `LoopRegistry` | Discovers and loads loop templates |
| `PatchSetRegistry` | Discovers and loads patch-set manifests |
| `FixtureManager` | Discovers and manages fixtures |
| `FixtureIsolator` | Deep-copies fixtures for isolation |
| `ManifestManager` | Manages run manifest lifecycle |
| `MetricsCollector` | Collects and aggregates metrics |
| `ComparisonGenerator` | Generates comparison reports |

## Troubleshooting

### Experiment fails immediately

**Error**: `ConfigError: Config template 'my-config' not found`

The template name doesn't match any file in `experiments/configs/`. Check:
1. File exists: `ls experiments/configs/my-config.yaml`
2. Internal `name` field matches filename stem
3. YAML is valid: `python -c "import yaml; yaml.safe_load(open('my-config.yaml'))"`

### Fixture not discovered

**Symptom**: Fixture doesn't appear in `templates` list

Check:
1. Fixture is a directory (not just tar): `ls -la experiments/fixtures/`
2. Directory name is valid (no spaces, starts with letter/underscore)
3. No `.` prefix (hidden directories are skipped)

### Isolation fails

**Error**: `IsolationError: Source path does not exist`

The fixture directory was moved or deleted. Verify:
```bash
ls experiments/fixtures/my-fixture/
```

**Error**: `IsolationError: Unsafe path in tar archive`

The tar archive contains path traversal (`..` components). Recreate the archive:
```bash
cd experiments/fixtures
rm my-fixture.tar
tar -cvf my-fixture.tar my-fixture/
```

### Comparison fails

**Error**: `ValueError: Cannot compare fewer than 2 runs`

Provide at least 2 run IDs to compare.

**Error**: `ConfigError: Run 'run-xyz' not found`

The run directory doesn't exist. List available runs:
```bash
ls experiments/runs/
```

### Metrics show 0 tokens/cost

This is expected if:
- The LLM provider doesn't report token usage
- Benchmarking extraction is disabled
- Running in test/mock mode

Enable benchmarking and configure helper provider:
```yaml
benchmarking:
  enabled: true

providers:
  helper:
    provider: claude-subprocess
    model: haiku
```

### Parallel batch not working

The `--parallel` flag is accepted but not implemented (MVP limitation). All batch runs execute sequentially.

## See Also

- [Prerequisites](experiments/prerequisites.md) - Required tools for scoring
- [Workflow Patches](workflow-patches.md) - Creating custom patches
- [Benchmarking](benchmarking.md) - LLM metrics collection
- [Configuration Reference](configuration.md) - Main configuration options
