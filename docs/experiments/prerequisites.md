# Experiment Framework Prerequisites

This document lists the required tools for running the bmad-assist experiment framework, including fixture scoring and quality analysis.

## Required Tools

### Python Environment

The bmad-assist CLI requires Python 3.11+ with the package installed:

```bash
# Verify Python version
python --version  # Should be 3.11+

# Install bmad-assist (if not already)
pip install -e .
```

### Go Toolchain

Required for scoring Go-based fixtures (build verification, unit tests, linting).

**Ubuntu/Debian:**
```bash
sudo apt update && sudo apt install -y golang-go
```

**macOS:**
```bash
brew install go
```

**Verify installation:**
```bash
go version  # Should output go version (1.20+ recommended)
```

### Go Quality Tools

Required for complete code quality scoring (complexity analysis, security scanning).

```bash
# Complexity analyzer
go install github.com/fzipp/gocyclo/cmd/gocyclo@latest

# Security scanner
go install github.com/securego/gosec/v2/cmd/gosec@latest
```

These tools install to `~/go/bin`. Add this directory to your PATH:

```bash
# Add to ~/.bashrc or ~/.zshrc
export PATH=$PATH:$HOME/go/bin

# Apply changes
source ~/.bashrc  # or source ~/.zshrc
```

**Verify installation:**
```bash
gocyclo --version
gosec --version
```

### Playwright (for UI fixtures)

Required for scoring fixtures with UI components.

```bash
# Install Playwright
pip install playwright

# Install browsers
playwright install
```

## Verification

Run the following to verify your environment is correctly configured:

```bash
# Check all tools are available
go version
gocyclo --version
gosec --version

# Run a test scorecard
bmad-assist test scorecard webhook-relay-001
```

Expected output should show scores for all categories without "skipped" markers in code_quality section.

## Scoring Without Prerequisites

If required tools are not installed, the scorer will:

1. **Functionality (build, tests):** Score 0 with error message indicating missing tool
2. **Code Quality (linting, complexity, security):** Score 0 with `skipped: true` and `reason` field

This ensures honest scoring - no false positives for unverified code quality.

## Tool Summary

| Tool | Purpose | Scoring Impact |
|------|---------|----------------|
| `go` | Build, test, lint (go vet) | functionality.build, functionality.unit_tests, code_quality.linting |
| `gocyclo` | Cyclomatic complexity | code_quality.complexity |
| `gosec` | Security vulnerability scan | code_quality.security |
| `playwright` | UI/UX testing | ui_ux (when applicable) |

## Troubleshooting

### "go: command not found"

Go is not installed or not in PATH. Install via package manager (see above).

### "gocyclo: command not found" / "gosec: command not found"

Tools installed but `~/go/bin` not in PATH. Add to your shell config:

```bash
echo 'export PATH=$PATH:$HOME/go/bin' >> ~/.bashrc
source ~/.bashrc
```

### Scorecard shows "skipped: true" for code_quality

One or more Go tools are not installed or not in PATH. Run verification commands above.

### go.sum checksum mismatch

Fixture has corrupted go.sum. This is valid test data - the fixture was generated with issues. Do not manually fix fixtures.

### Import cycle errors

Fixture has architectural issues in generated code. This is valid test data showing LLM-generated code quality.
