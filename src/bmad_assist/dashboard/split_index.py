#!/usr/bin/env python3
"""Split index.html into partials based on line ranges.

Run this once to create initial partials from existing index.html.
"""

from pathlib import Path

STATIC = Path(__file__).parent / "static"
STATIC_SRC = Path(__file__).parent / "static-src"

# Line ranges for each partial (1-indexed, inclusive)
SPLITS = [
    ("01-head.html", 1, 35),  # DOCTYPE through <div class="flex h-screen">
    ("02-sidebar.html", 36, 248),  # <aside> sidebar
    ("03-main-header.html", 249, 279),  # <main> start + header
    ("04-terminal.html", 280, 331),  # Terminal output section
    ("05-settings-panel.html", 332, 1349),  # Settings panel (huge!)
    ("06-experiments-panel.html", 1350, 2209),  # Experiments panel (huge!)
    ("07-experiment-details.html", 2210, 2459),  # Experiment details modal
    ("08-comparison-panel.html", 2460, 2661),  # Comparison panel
    ("09-footer.html", 2662, 2688),  # Footer with controls!
    ("10-modals.html", 2689, 2900),  # Context menu, toasts, busy modal
    ("11-tail.html", 2901, 99999),  # Scripts, closing tags
]


def split() -> None:
    """Split index.html into partials."""
    STATIC_SRC.mkdir(exist_ok=True)

    index_path = STATIC / "index.html"
    lines = index_path.read_text().splitlines(keepends=True)

    for filename, start, end in SPLITS:
        # Convert to 0-indexed
        chunk = lines[start - 1 : min(end, len(lines))]
        content = "".join(chunk)

        out_path = STATIC_SRC / filename
        out_path.write_text(content)
        print(f"Created {filename}: lines {start}-{min(end, len(lines))} ({len(chunk)} lines)")


if __name__ == "__main__":
    split()
