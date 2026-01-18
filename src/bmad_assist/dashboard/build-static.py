#!/usr/bin/env python3
"""Build dashboard static files by concatenating partials.

Usage:
    python build-static.py          # Build index.html from partials
    python build-static.py --watch  # Watch for changes and rebuild

Partials are in static-src/ and are concatenated in order to produce static/index.html.
"""

import sys
from pathlib import Path

STATIC_SRC = Path(__file__).parent / "static-src"
STATIC_OUT = Path(__file__).parent / "static"

# Order of partials to concatenate
PARTIALS_ORDER = [
    "01-head.html",
    "02-sidebar.html",
    "03-main-header.html",
    "04-terminal.html",
    "05-settings-panel.html",
    "06-experiments-panel.html",
    "07-experiment-details.html",
    "08-comparison-panel.html",
    "09-footer.html",
    "10-modals.html",
    "11-tail.html",
]


def build() -> None:
    """Concatenate all partials into index.html."""
    output_lines: list[str] = []

    for partial_name in PARTIALS_ORDER:
        partial_path = STATIC_SRC / partial_name
        if not partial_path.exists():
            print(f"WARNING: Missing partial: {partial_name}")
            continue

        content = partial_path.read_text()
        # Note: Don't add HTML comments - they can break HTML when split
        # boundaries fall inside tags or attributes
        output_lines.append(content)
        if not content.endswith("\n"):
            output_lines.append("\n")

    output = "".join(output_lines)
    output_path = STATIC_OUT / "index.html"
    output_path.write_text(output)
    print(f"Built {output_path} ({len(output):,} bytes)")


def watch() -> None:
    """Watch for changes and rebuild."""
    try:
        from watchdog.events import FileSystemEventHandler
        from watchdog.observers import Observer
    except ImportError:
        print("Install watchdog for watch mode: pip install watchdog")
        sys.exit(1)

    class RebuildHandler(FileSystemEventHandler):
        def on_modified(self, event):
            if event.src_path.endswith(".html"):
                print(f"Changed: {event.src_path}")
                build()

    observer = Observer()
    observer.schedule(RebuildHandler(), str(STATIC_SRC), recursive=False)
    observer.start()
    print(f"Watching {STATIC_SRC} for changes...")

    try:
        import time

        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


if __name__ == "__main__":
    if "--watch" in sys.argv:
        watch()
    else:
        build()
