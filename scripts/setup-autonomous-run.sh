#!/usr/bin/env bash
# Setup autonomous bmad-assist run for Epic 20
#
# This script prepares a separate project copy for bmad-assist to edit,
# avoiding the "editing yourself" problem.
#
# Usage: ./scripts/setup-autonomous-run.sh [epic] [story]
# Example: ./scripts/setup-autonomous-run.sh 20 1

set -euo pipefail

# Configuration
SOURCE_DIR="/home/pawel/projects/bmad-assist-22"
TARGET_DIR="/home/pawel/projects/bmad-assist-22-mad"
EPIC="${1:-20}"
STORY="${2:-1}"

echo "=============================================="
echo "  bmad-assist Autonomous Run Setup"
echo "=============================================="
echo ""
echo "Source (runner):  $SOURCE_DIR"
echo "Target (edited):  $TARGET_DIR"
echo "Starting at:      Epic $EPIC, Story $EPIC.$STORY"
echo ""

# Check if source exists
if [[ ! -d "$SOURCE_DIR" ]]; then
    echo "ERROR: Source directory not found: $SOURCE_DIR"
    exit 1
fi

# Check if target already exists
if [[ -d "$TARGET_DIR" ]]; then
    echo "WARNING: Target directory already exists: $TARGET_DIR"
    read -p "Delete and recreate? [y/N] " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Removing existing target..."
        rm -rf "$TARGET_DIR"
    else
        echo "Aborted."
        exit 1
    fi
fi

# Step 1: Copy project
echo ""
echo "[1/4] Copying project..."
cp -r "$SOURCE_DIR" "$TARGET_DIR"
echo "      Done: $TARGET_DIR"

# Step 2: Remove git remote (safety)
echo ""
echo "[2/4] Removing git remote origin (safety measure)..."
cd "$TARGET_DIR"
if git remote get-url origin &>/dev/null; then
    git remote remove origin
    echo "      Done: remote 'origin' removed"
else
    echo "      Skipped: no remote 'origin' found"
fi

# Step 3: Create state.yaml
echo ""
echo "[3/4] Creating .bmad-assist/state.yaml..."
mkdir -p "$TARGET_DIR/.bmad-assist"
cat > "$TARGET_DIR/.bmad-assist/state.yaml" << EOF
current_epic: $EPIC
current_story: "$EPIC.$STORY"
current_phase: create_story
completed_stories: []
completed_epics: []
started_at: null
updated_at: null
anomalies: []
testarch_preflight: null
atdd_ran_for_story: false
atdd_ran_in_epic: false
EOF
echo "      Done: state.yaml created for Epic $EPIC, Story $EPIC.$STORY"

# Step 4: Verify setup
echo ""
echo "[4/4] Verifying setup..."
echo "      Target directory: $(du -sh "$TARGET_DIR" | cut -f1)"
echo "      Git status: $(cd "$TARGET_DIR" && git status --porcelain | wc -l) uncommitted files"
echo "      State file: $(cat "$TARGET_DIR/.bmad-assist/state.yaml" | head -3 | tr '\n' ' ')"

# Final instructions
echo ""
echo "=============================================="
echo "  Setup Complete!"
echo "=============================================="
echo ""
echo "To start the autonomous run:"
echo ""
echo "  cd $SOURCE_DIR"
echo "  source .venv/bin/activate"
echo "  bmad-assist run --project $TARGET_DIR"
echo ""
echo "To monitor changes in target:"
echo ""
echo "  cd $TARGET_DIR && git status"
echo "  cd $TARGET_DIR && git diff"
echo ""
echo "To compare source vs target:"
echo ""
echo "  diff -r $SOURCE_DIR/src $TARGET_DIR/src"
echo ""
