#!/usr/bin/env bash
#
# reset-fixture.sh - Reset a fixture directory from its archive
#
# Usage: ./scripts/reset-fixture.sh <fixture-name>
#
# Example: ./scripts/reset-fixture.sh portfolio-project
#
# This script will:
# 1. Check if tests/fixtures/<name>/ exists
# 2. Check if matching archive exists (tar, tar.gz, tgz, zip)
# 3. Verify archive can recreate the directory
# 4. Ask for confirmation
# 5. Delete directory and extract archive
#

set -euo pipefail

FIXTURES_DIR="experiments/fixtures"

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

# Check arguments
if [[ $# -ne 1 ]]; then
    echo "Usage: $0 <fixture-name>"
    echo "Example: $0 portfolio-project"
    exit 1
fi

FIXTURE_NAME="$1"
FIXTURE_DIR="${FIXTURES_DIR}/${FIXTURE_NAME}"

# Find matching archive
find_archive() {
    local name="$1"
    for ext in tar tar.gz tgz zip; do
        candidate="${FIXTURES_DIR}/${name}.${ext}"
        if [[ -f "$candidate" ]]; then
            echo "$candidate"
            return 0
        fi
    done
    return 1
}

# Verify archive contents - check if it contains the directory or just files
verify_archive() {
    local archive="$1"
    local name="$2"

    case "$archive" in
        *.zip)
            first_entry=$(unzip -l "$archive" 2>/dev/null | awk 'NR==4 {print $4}')
            ;;
        *.tar.gz|*.tgz)
            first_entry=$(tar -tzf "$archive" 2>/dev/null | head -1)
            ;;
        *.tar)
            first_entry=$(tar -tf "$archive" 2>/dev/null | head -1)
            ;;
        *)
            error "Unknown archive format: $archive"
            ;;
    esac

    if [[ "$first_entry" == "${name}/"* ]] || [[ "$first_entry" == "${name}" ]]; then
        echo "directory"
    else
        echo "files"
    fi
}

# Check if fixture directory exists
if [[ ! -d "$FIXTURE_DIR" ]]; then
    # Directory doesn't exist - check if we can extract from archive
    if ARCHIVE=$(find_archive "$FIXTURE_NAME"); then
        echo "Fixture directory not found, but archive exists: $ARCHIVE"
        echo "This will extract the fixture from the archive."
        echo ""
        read -p "Extract? [y/N] " -n 1 -r
        echo ""
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "Aborted."
            exit 0
        fi

        # Extract directly (no deletion needed)
        info "Extracting $ARCHIVE"
        ARCHIVE_TYPE=$(verify_archive "$ARCHIVE" "$FIXTURE_NAME")

        case "$ARCHIVE" in
            *.zip)
                if [[ "$ARCHIVE_TYPE" == "files" ]]; then
                    mkdir -p "$FIXTURE_DIR"
                    unzip -q "$ARCHIVE" -d "$FIXTURE_DIR"
                else
                    unzip -q "$ARCHIVE" -d "$FIXTURES_DIR"
                fi
                ;;
            *.tar.gz|*.tgz)
                if [[ "$ARCHIVE_TYPE" == "files" ]]; then
                    mkdir -p "$FIXTURE_DIR"
                    tar -xzf "$ARCHIVE" -C "$FIXTURE_DIR"
                else
                    tar -xzf "$ARCHIVE" -C "$FIXTURES_DIR"
                fi
                ;;
            *.tar)
                if [[ "$ARCHIVE_TYPE" == "files" ]]; then
                    mkdir -p "$FIXTURE_DIR"
                    tar -xf "$ARCHIVE" -C "$FIXTURE_DIR"
                else
                    tar -xf "$ARCHIVE" -C "$FIXTURES_DIR"
                fi
                ;;
        esac

        if [[ -d "$FIXTURE_DIR" ]]; then
            file_count=$(find "$FIXTURE_DIR" -type f | wc -l)
            info "Done! Extracted $FIXTURE_DIR/ ($file_count files)"
        else
            error "Extraction failed - directory not created"
        fi
        exit 0
    else
        error "Fixture directory not found: $FIXTURE_DIR (and no archive available)"
    fi
fi

# Find matching archive for reset
ARCHIVE=""
for ext in tar tar.gz tgz zip; do
    candidate="${FIXTURES_DIR}/${FIXTURE_NAME}.${ext}"
    if [[ -f "$candidate" ]]; then
        ARCHIVE="$candidate"
        break
    fi
done

if [[ -z "$ARCHIVE" ]]; then
    error "No archive found for '${FIXTURE_NAME}' in ${FIXTURES_DIR}/"
fi

info "Found archive: $ARCHIVE"

ARCHIVE_TYPE=$(verify_archive "$ARCHIVE" "$FIXTURE_NAME")
info "Archive structure: $ARCHIVE_TYPE"

# Show what will happen
echo ""
echo "This will:"
echo "  1. Delete:  $FIXTURE_DIR/"
echo "  2. Extract: $ARCHIVE"
if [[ "$ARCHIVE_TYPE" == "files" ]]; then
    echo "     (files will be extracted into ${FIXTURE_DIR}/)"
else
    echo "     (directory will be recreated as ${FIXTURE_DIR}/)"
fi
echo ""

# Ask for confirmation
read -p "Proceed? [y/N] " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 0
fi

# Delete directory
info "Deleting $FIXTURE_DIR/"
rm -rf "$FIXTURE_DIR"

# Extract archive
info "Extracting $ARCHIVE"

case "$ARCHIVE" in
    *.zip)
        if [[ "$ARCHIVE_TYPE" == "files" ]]; then
            mkdir -p "$FIXTURE_DIR"
            unzip -q "$ARCHIVE" -d "$FIXTURE_DIR"
        else
            unzip -q "$ARCHIVE" -d "$FIXTURES_DIR"
        fi
        ;;
    *.tar.gz|*.tgz)
        if [[ "$ARCHIVE_TYPE" == "files" ]]; then
            mkdir -p "$FIXTURE_DIR"
            tar -xzf "$ARCHIVE" -C "$FIXTURE_DIR"
        else
            tar -xzf "$ARCHIVE" -C "$FIXTURES_DIR"
        fi
        ;;
    *.tar)
        if [[ "$ARCHIVE_TYPE" == "files" ]]; then
            mkdir -p "$FIXTURE_DIR"
            tar -xf "$ARCHIVE" -C "$FIXTURE_DIR"
        else
            tar -xf "$ARCHIVE" -C "$FIXTURES_DIR"
        fi
        ;;
esac

# Verify extraction
if [[ -d "$FIXTURE_DIR" ]]; then
    file_count=$(find "$FIXTURE_DIR" -type f | wc -l)
    info "Done! Restored $FIXTURE_DIR/ ($file_count files)"
else
    error "Extraction failed - directory not created"
fi
