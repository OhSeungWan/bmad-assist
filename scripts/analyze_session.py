#!/usr/bin/env python3
"""Analyze Claude Code debug session JSONL files.

Extracts key information:
- Session stats (cost, tokens, duration, turns)
- Tool usage breakdown
- Condensed message flow (intro + summary, tool calls)

Usage:
    python scripts/analyze_session.py <session.jsonl>
    python scripts/analyze_session.py <session1.jsonl> <session2.jsonl>  # compare
    python scripts/analyze_session.py ~/.bmad-assist/debug/json/*.jsonl  # batch
"""

import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class SessionStats:
    """Aggregated session statistics."""

    filepath: str
    duration_s: float = 0.0
    turns: int = 0
    total_cost: float = 0.0

    # Token breakdown
    input_tokens: int = 0  # non-cached
    cache_read: int = 0
    cache_creation: int = 0
    output_tokens: int = 0

    # Tool usage
    tools: dict[str, int] = field(default_factory=dict)

    # Messages
    messages: list[dict] = field(default_factory=list)

    @property
    def total_input(self) -> int:
        return self.input_tokens + self.cache_read + self.cache_creation

    @property
    def cache_hit_rate(self) -> float:
        if self.total_input == 0:
            return 0.0
        return self.cache_read / self.total_input * 100

    @property
    def calculated_cost(self) -> float:
        """Calculate cost using Sonnet pricing."""
        # Sonnet: $3/M input, $0.30/M cache read, $3.75/M cache create, $15/M output
        return (
            self.input_tokens * 3 / 1_000_000
            + self.cache_read * 0.30 / 1_000_000
            + self.cache_creation * 3.75 / 1_000_000
            + self.output_tokens * 15 / 1_000_000
        )


def truncate_middle(text: str, max_len: int = 500, keep_start: int = 200, keep_end: int = 200) -> str:
    """Truncate text keeping start and end, removing middle."""
    if len(text) <= max_len:
        return text

    # Find paragraph boundaries
    paragraphs = text.split("\n\n")
    if len(paragraphs) >= 3:
        # Keep first and last paragraphs
        intro = paragraphs[0]
        summary = paragraphs[-1]

        if len(intro) + len(summary) + 50 < max_len:
            return f"{intro}\n\n[...{len(text) - len(intro) - len(summary)} chars truncated...]\n\n{summary}"

    # Fallback: simple character truncation
    return f"{text[:keep_start]}\n\n[...{len(text) - keep_start - keep_end} chars truncated...]\n\n{text[-keep_end:]}"


def extract_text_content(content_blocks: list) -> str:
    """Extract text from content blocks."""
    texts = []
    for block in content_blocks:
        if block.get("type") == "text":
            texts.append(block.get("text", ""))
    return "\n".join(texts)


def format_tool_input(tool_name: str, inp: dict, max_len: int = 300) -> str:
    """Format tool input for display."""
    if tool_name == "Read":
        return inp.get("file_path", "?")

    if tool_name == "Write":
        path = inp.get("file_path", "?")
        content = inp.get("content", "")
        return f"{path} ({len(content)} chars)"

    if tool_name == "Edit":
        path = inp.get("file_path", "?")
        old = inp.get("old_string", "")[:50]
        new = inp.get("new_string", "")[:50]
        return f"{path}: '{old}...' -> '{new}...'"

    if tool_name == "Bash":
        cmd = inp.get("command", "")
        if len(cmd) > max_len:
            cmd = cmd[:max_len] + "..."
        return cmd

    if tool_name == "Grep":
        pattern = inp.get("pattern", "?")
        path = inp.get("path", ".")
        return f"'{pattern}' in {path}"

    if tool_name == "Glob":
        pattern = inp.get("pattern", "?")
        path = inp.get("path", ".")
        return f"'{pattern}' in {path}"

    if tool_name in ("Task", "SlashCommand"):
        return str(inp)[:max_len]

    # Generic fallback
    s = json.dumps(inp)
    if len(s) > max_len:
        s = s[:max_len] + "..."
    return s


def parse_session(filepath: Path) -> SessionStats:
    """Parse JSONL session file."""
    stats = SessionStats(filepath=str(filepath))

    with open(filepath) as f:
        lines = [json.loads(line) for line in f]

    for line in lines:
        line_type = line.get("type")

        # Summary line (last line with usage data)
        if "usage" in line and "total_cost_usd" in line:
            usage = line.get("usage", {})
            stats.duration_s = line.get("duration_ms", 0) / 1000
            stats.turns = line.get("num_turns", 0)
            stats.total_cost = line.get("total_cost_usd", 0)
            stats.input_tokens = usage.get("input_tokens", 0)
            stats.cache_read = usage.get("cache_read_input_tokens", 0)
            stats.cache_creation = usage.get("cache_creation_input_tokens", 0)
            stats.output_tokens = usage.get("output_tokens", 0)
            continue

        # Assistant messages
        if line_type == "assistant":
            content = line.get("message", {}).get("content", [])

            msg_entry = {"role": "assistant", "tools": [], "text": ""}

            for block in content:
                if block.get("type") == "text":
                    msg_entry["text"] = truncate_middle(block.get("text", ""))

                elif block.get("type") == "tool_use":
                    tool_name = block.get("name", "unknown")
                    tool_input = block.get("input", {})

                    # Count tools
                    stats.tools[tool_name] = stats.tools.get(tool_name, 0) + 1

                    # Record tool call
                    msg_entry["tools"].append({
                        "name": tool_name,
                        "input": format_tool_input(tool_name, tool_input),
                    })

            if msg_entry["text"] or msg_entry["tools"]:
                stats.messages.append(msg_entry)

        # User messages (skip tool results - they're noise)
        elif line_type == "user":
            content = line.get("message", {}).get("content", [])

            # Check if this is a tool_result (skip)
            has_tool_result = any(
                block.get("type") == "tool_result" for block in content
            )
            if has_tool_result:
                continue

            # Real user message
            text = extract_text_content(content)
            if text.strip():
                stats.messages.append({
                    "role": "user",
                    "text": truncate_middle(text),
                })

    return stats


def print_stats(stats: SessionStats, verbose: bool = False) -> None:
    """Print session statistics."""
    print(f"\n{'=' * 60}")
    print(f"SESSION: {Path(stats.filepath).name}")
    print(f"{'=' * 60}")

    print(f"\nMETRICS:")
    print(f"  Duration:      {stats.duration_s:.1f}s")
    print(f"  Turns:         {stats.turns}")
    print(f"  Cost:          ${stats.total_cost:.4f} (reported)")
    print(f"                 ${stats.calculated_cost:.4f} (calculated)")

    print(f"\nTOKENS:")
    print(f"  Non-cached:    {stats.input_tokens:>12,}")
    print(f"  Cache read:    {stats.cache_read:>12,}")
    print(f"  Cache create:  {stats.cache_creation:>12,}")
    print(f"  Output:        {stats.output_tokens:>12,}")
    print(f"  {'─' * 30}")
    print(f"  Total input:   {stats.total_input:>12,}")
    print(f"  Cache hit:     {stats.cache_hit_rate:>11.1f}%")

    print(f"\nTOOLS:")
    for tool, count in sorted(stats.tools.items(), key=lambda x: -x[1]):
        print(f"  {tool:<20} {count:>3}")

    if verbose:
        print(f"\nMESSAGE FLOW:")
        print(f"{'─' * 60}")
        for i, msg in enumerate(stats.messages):
            role = msg["role"].upper()
            print(f"\n[{i+1}] {role}:")

            if msg.get("text"):
                # Indent text
                for line in msg["text"].split("\n")[:10]:
                    print(f"    {line[:150]}")
                if msg["text"].count("\n") > 10:
                    print(f"    [...more lines...]")

            for tool in msg.get("tools", []):
                print(f"    -> {tool['name']}: {tool['input'][:200]}")


def compare_sessions(sessions: list[SessionStats]) -> None:
    """Print comparison table for multiple sessions."""
    if len(sessions) < 2:
        return

    print(f"\n{'=' * 160}")
    print("COMPARISON")
    print(f"{'=' * 160}")

    # Header
    names = [Path(s.filepath).stem[:80] for s in sessions]
    print(f"{'Metric':<20}", end="")
    for name in names:
        print(f"{name:>20}", end="")
    print()
    print("─" * (20 + 20 * len(sessions)))

    # Metrics
    metrics = [
        ("Duration (s)", lambda s: f"{s.duration_s:.1f}"),
        ("Turns", lambda s: str(s.turns)),
        ("Cost ($)", lambda s: f"{s.calculated_cost:.4f}"),
        ("Total input", lambda s: f"{s.total_input:,}"),
        ("Cache read", lambda s: f"{s.cache_read:,}"),
        ("Cache hit %", lambda s: f"{s.cache_hit_rate:.1f}%"),
        ("Output tokens", lambda s: f"{s.output_tokens:,}"),
    ]

    for name, fn in metrics:
        print(f"{name:<20}", end="")
        for s in sessions:
            print(f"{fn(s):>20}", end="")
        print()

    # Tool comparison
    all_tools = set()
    for s in sessions:
        all_tools.update(s.tools.keys())

    print(f"\n{'Tool':<20}", end="")
    for name in names:
        print(f"{name:>20}", end="")
    print()
    print("─" * (20 + 20 * len(sessions)))

    for tool in sorted(all_tools):
        print(f"{tool:<20}", end="")
        for s in sessions:
            count = s.tools.get(tool, 0)
            print(f"{count:>20}", end="")
        print()


def print_compact(sessions: list[SessionStats]) -> None:
    """Print compact one-line-per-session summary."""
    print(f"{'Session':<45} {'Time':>8} {'Turns':>6} {'Cost':>8} {'Input':>12} {'Cache%':>8}")
    print("─" * 95)
    for s in sessions:
        name = Path(s.filepath).stem[:44]  # beginning is most important (date/time)
        print(
            f"{name:<45} "
            f"{s.duration_s:>7.0f}s "
            f"{s.turns:>6} "
            f"${s.calculated_cost:>6.2f} "
            f"{s.total_input:>11,} "
            f"{s.cache_hit_rate:>7.1f}%"
        )


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    args = sys.argv[1:]
    verbose = "-v" in args or "--verbose" in args
    compact = "-c" in args or "--compact" in args
    files = [f for f in args if not f.startswith("-")]

    sessions = []
    for filepath in files:
        path = Path(filepath)
        if not path.exists():
            print(f"File not found: {filepath}", file=sys.stderr)
            continue

        try:
            stats = parse_session(path)
            sessions.append(stats)
        except Exception as e:
            print(f"Error parsing {filepath}: {e}", file=sys.stderr)

    if compact:
        print_compact(sessions)
    else:
        for stats in sessions:
            print_stats(stats, verbose=verbose)

        if len(sessions) > 1:
            compare_sessions(sessions)


if __name__ == "__main__":
    main()
