#!/bin/bash
# Setup benchmark fixture directories

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
FIXTURES_DIR="$PROJECT_ROOT/tests/fixtures"

PROJECTS=(
  "auth-service"
  "component-library"
  "cli-dashboard"
  "markdown-notes"
  "test-data-gen"
  "webhook-relay"
)

echo "Setting up benchmark fixture directories..."
echo "Project root: $PROJECT_ROOT"
echo ""

for project in "${PROJECTS[@]}"; do
  echo "Creating: $project"

  # Create directory structure
  mkdir -p "$FIXTURES_DIR/${project}/docs/epics"
  mkdir -p "$FIXTURES_DIR/${project}/docs/sprint-artifacts/benchmarks"
  mkdir -p "$FIXTURES_DIR/${project}/.bmad-assist/cache"
  mkdir -p "$FIXTURES_DIR/${project}/src"

  # Create initial state
  cat > "$FIXTURES_DIR/${project}/.bmad-assist/state.yaml" << 'EOF'
phase: CREATE_STORY
epic: 1
story: 1
workflow_id: null
session_id: null
EOF

  # Create bmad-assist config
  cat > "$FIXTURES_DIR/${project}/bmad-assist.yaml" << 'EOF'
# bmad-assist configuration
# Copy provider settings from your global config or customize here

providers:
  master:
    provider: claude-subprocess
    model: opus

  multi:
    - provider: claude-subprocess
      model: sonnet
    - provider: gemini
      model: gemini-2.5-pro
    - provider: codex
      model: gpt-5.2

benchmarking:
  enabled: true
  extraction_provider: claude
  extraction_model: haiku
EOF

  # Create sprint-status.yaml placeholder
  cat > "$FIXTURES_DIR/${project}/docs/sprint-artifacts/sprint-status.yaml" << 'EOF'
# Sprint status - will be populated after epics are generated
epics: []
current_epic: 1
current_story: 1
phase: documentation
EOF

  echo "  ✓ Created directory structure"
  echo "  ✓ Created state.yaml"
  echo "  ✓ Created bmad-assist.yaml"
done

echo ""
echo "Done! Created ${#PROJECTS[@]} fixture directories."
echo ""
echo "Next steps:"
echo "1. Run the parallel generation commands from docs/benchmark-generation-guide.md"
echo "2. Or use: claude \"Generate docs for [project]\" in each terminal"
