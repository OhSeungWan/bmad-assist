#!/usr/bin/env bash
#
# archive-fixture.sh - Archive a fixture directory
#
# Usage: ./scripts/archive-fixture.sh [options] <fixture-name>
#
# Options:
#   -t, --type <format>  Archive format: tar (default), tar.gz, tgz, zip
#
# Examples:
#   ./scripts/archive-fixture.sh portfolio-project
#   ./scripts/archive-fixture.sh -t tar.gz portfolio-project
#   ./scripts/archive-fixture.sh --type zip portfolio-project
#

set -euo pipefail

FIXTURES_DIR="experiments/fixtures"
ARCHIVE_TYPE="tar"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

error() {
    echo -e "${RED}Error:${NC} $1" >&2
    exit 1
}

warn() {
    echo -e "${YELLOW}Warning:${NC} $1" >&2
}

info() {
    echo -e "${GREEN}✓${NC} $1"
}

usage() {
    echo "Usage: $0 [options] <fixture-name>"
    echo ""
    echo "Options:"
    echo "  -t, --type <format>  Archive format: tar (default), tar.gz, tgz, zip"
    echo ""
    echo "Examples:"
    echo "  $0 portfolio-project"
    echo "  $0 -t tar.gz portfolio-project"
    echo "  $0 --type zip portfolio-project"
    exit 1
}

# Parse arguments
FIXTURE_NAME=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -t|--type)
            if [[ -z "${2:-}" ]]; then
                error "Option $1 requires an argument"
            fi
            ARCHIVE_TYPE="$2"
            shift 2
            ;;
        -h|--help)
            usage
            ;;
        -*)
            error "Unknown option: $1"
            ;;
        *)
            if [[ -n "$FIXTURE_NAME" ]]; then
                error "Too many arguments"
            fi
            FIXTURE_NAME="$1"
            shift
            ;;
    esac
done

# Validate arguments
if [[ -z "$FIXTURE_NAME" ]]; then
    usage
fi

# Validate archive type
case "$ARCHIVE_TYPE" in
    tar|tar.gz|tgz|zip)
        ;;
    *)
        error "Invalid archive type: $ARCHIVE_TYPE (valid: tar, tar.gz, tgz, zip)"
        ;;
esac

# Check zip availability if needed
if [[ "$ARCHIVE_TYPE" == "zip" ]]; then
    if ! command -v zip &> /dev/null; then
        error "zip command not found. Install with: sudo apt install zip"
    fi
fi

FIXTURE_DIR="${FIXTURES_DIR}/${FIXTURE_NAME}"
ARCHIVE="${FIXTURES_DIR}/${FIXTURE_NAME}.${ARCHIVE_TYPE}"

# Check if fixture directory exists
if [[ ! -d "$FIXTURE_DIR" ]]; then
    error "Fixture directory not found: $FIXTURE_DIR"
fi

# Check if archive already exists
if [[ -f "$ARCHIVE" ]]; then
    warn "Archive already exists: $ARCHIVE"
    read -p "Replace existing archive? [y/N] " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Aborted."
        exit 0
    fi
    rm -f "$ARCHIVE"
fi

# Count files in fixture
file_count=$(find "$FIXTURE_DIR" -type f | wc -l)
dir_size=$(du -sh "$FIXTURE_DIR" | cut -f1)

info "Archiving $FIXTURE_DIR/ ($file_count files, $dir_size)"

# Create archive
case "$ARCHIVE_TYPE" in
    tar)
        tar -cf "$ARCHIVE" -C "$FIXTURES_DIR" "$FIXTURE_NAME"
        ;;
    tar.gz|tgz)
        tar -czf "$ARCHIVE" -C "$FIXTURES_DIR" "$FIXTURE_NAME"
        ;;
    zip)
        # zip needs to be run from fixtures dir to get correct paths
        (cd "$FIXTURES_DIR" && zip -rq "${FIXTURE_NAME}.${ARCHIVE_TYPE}" "$FIXTURE_NAME")
        ;;
esac

# Verify and show result
if [[ -f "$ARCHIVE" ]]; then
    archive_size=$(du -sh "$ARCHIVE" | cut -f1)
    info "Created: $ARCHIVE ($archive_size)"
else
    error "Failed to create archive"
fi
