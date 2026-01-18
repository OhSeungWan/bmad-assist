# bmad-assist

CLI tool for automating the [BMAD](https://github.com/bmad-method) development methodology with Multi-LLM orchestration.

## What is BMAD?

BMAD (Brian's Methodology for AI-Driven Development) is a structured approach to software development that leverages AI assistants throughout the entire lifecycle: from product brief to retrospective.

**bmad-assist** automates the BMAD loop with Multi-LLM orchestration:

```
            ┌─────────────────┐
            │  Create Story   │
            │    (Master)     │
            └────────┬────────┘
                     │
    ┌────────────────┼────────────────┐
    ▼                ▼                ▼
┌────────────┐ ┌────────────┐ ┌────────────┐
│  Validate  │ │  Validate  │ │  Validate  │
│  (Master)  │ │  (Gemini)  │ │  (Codex)   │
└─────┬──────┘ └─────┬──────┘ └─────┬──────┘
      │              │              │
      └──────────────┼──────────────┘
                     ▼
            ┌─────────────────┐
            │    Synthesis    │
            │    (Master)     │
            └────────┬────────┘
                     │
            ┌────────▼────────┐
            │    Dev Story    │
            │    (Master)     │
            └────────┬────────┘
                     │
    ┌────────────────┼────────────────┐
    ▼                ▼                ▼
┌────────────┐ ┌────────────┐ ┌────────────┐
│   Review   │ │   Review   │ │   Review   │
│  (Master)  │ │  (Gemini)  │ │  (Codex)   │
└─────┬──────┘ └─────┬──────┘ └─────┬──────┘
      │              │              │
      └──────────────┼──────────────┘
                     ▼
            ┌─────────────────┐
            │    Synthesis    │
            │    (Master)     │
            └────────┬────────┘
                     │
            ┌────────▼────────┐
            │  Retrospective  │
            │    (Master)     │
            └─────────────────┘
```

**Key insight:** Multiple LLMs validate/review in parallel, then Master synthesizes their findings. Only Master modifies files.

## Features

- **Multi-LLM Orchestration** - Run parallel validations/reviews with Claude Code, Gemini CLI, and Codex
- **Workflow Compiler** - Transform BMAD workflows into optimized standalone prompts
- **Patch System** - Customize workflows per-project without forking

**TODO:**
- Real-time Dashboard
- Experiment Framework
- Test Architect Integration

## Installation

```bash
# Clone the repository
git clone https://github.com/Pawel-N-pl/bmad-assist.git
cd bmad-assist

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# or: .venv\Scripts\activate  # Windows

# Install in development mode
pip install -e .
```

## Requirements

- Python 3.11+
- At least one LLM CLI tool:
  - [Claude Code](https://claude.ai/code) (recommended)
  - [Gemini CLI](https://github.com/google-gemini/gemini-cli)
  - [Codex CLI](https://github.com/openai/codex)

## Quick Start

**Before running bmad-assist on your project:**

1. Copy `_bmad/` directory from this repo to your project root
2. Ensure your project has complete documentation in `docs/`:
   - `prd.md` - Product Requirements Document
   - `architecture/` or `architecture.md` - Technical architecture decisions
   - `epics/` or `epics.md` - Epic definitions with stories
   - `project-context.md` - AI agent implementation rules
   - `ux-spec.md` (optional) - UX specifications

```bash
# Check CLI is working
bmad-assist --help

# Run the main development loop
bmad-assist run --project /path/to/your/project
```

### Try It Out

To quickly test bmad-assist, use the included `simple-portfolio` fixture:

```bash
# Unpack the fixture
./scripts/fixture-reset.sh simple-portfolio

# Run bmad-assist on the fixture project
bmad-assist run --project experiments/fixtures/simple-portfolio
```

## Project Configuration

Create `bmad-assist.yaml` in your project root:

```yaml
providers:
  master:
    provider: claude-subprocess
    model: opus
  multi:
    - provider: gemini
      model: gemini-2.5-flash
    - provider: codex
      model: o3-mini
    - provider: claude-subprocess
      model: opus
      model_name: glm-4.7           # display name in logs/reports
      settings: ~/.claude/glm.json  # custom model settings

notifications:
  enabled: true
  events:
    - story_started
    - story_completed
    - phase_completed
    - error_occurred
  providers:
    - type: telegram
      bot_token: ${TELEGRAM_BOT_TOKEN}
      chat_id: ${TELEGRAM_CHAT_ID}
    - type: discord
      webhook_url: ${DISCORD_WEBHOOK_URL}
```

## Project Structure

```
bmad-assist/
├── src/bmad_assist/      # CLI source code
│   ├── cli.py            # Typer entry point
│   ├── core/             # Config, state, loop
│   ├── compiler/         # Workflow compiler
│   ├── validation/       # Multi-LLM validation
│   └── code_review/      # Code review orchestration
├── _bmad/                # BMAD workflows (customized)
├── .bmad-assist/         # Project patches
└── tests/                # Test suite
```

## Development

```bash
# Run tests
pytest -q --tb=line --no-header

# Type checking
mypy src/

# Linting
ruff check src/
ruff format src/
```

## License

MIT

## Links

- [BMAD Method](https://github.com/bmad-method) - The methodology behind this tool
