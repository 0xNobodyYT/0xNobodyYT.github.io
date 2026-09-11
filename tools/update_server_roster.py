#!/usr/bin/env python3
"""Update the calendar's server roster from the public community Google Sheet."""

from __future__ import annotations

import argparse
import csv
import io
import json
import re
import sys
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path


DEFAULT_SOURCE = (
    "https://docs.google.com/spreadsheets/d/"
    "1uZqmE-71qg2JbEEeBKQXppDToqo4UwQ1zdMFs75UyrU/"
    "gviz/tq?tqx=out:csv&gid=730102442"
)
DEFAULT_OUTPUT = Path("sxs-primo-calculator/server-data.js")
ASSIGNMENT_RE = re.compile(r"window\.SXS_SERVER_ROWS\s*=\s*(\[.*\])\s*;", re.DOTALL)
HEADER = (
    "// Server names/opening dates sourced from the linked community roster.\n"
    "// Columns: name, previous derived date (migration only), public opening / Calendar Day 1, Nexus, number.\n"
)


def read_existing(path: Path) -> list[list[object]]:
    if not path.exists():
        return []
    match = ASSIGNMENT_RE.search(path.read_text(encoding="utf-8"))
    if not match:
        raise ValueError(f"Could not find SXS_SERVER_ROWS in {path}")
    rows = json.loads(match.group(1))
    if not isinstance(rows, list):
        raise ValueError("Existing server roster is not an array")
    return rows


def download_csv(url: str) -> str:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "0xNobody-SxS-Server-Updater/1.0"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        if response.status != 200:
            raise RuntimeError(f"Roster download returned HTTP {response.status}")
        return response.read().decode("utf-8-sig")


def iso_date(value: str) -> str:
    value = value.strip()
    if not value:
        return ""
    for fmt in ("%m/%d/%Y %I:%M %p", "%m/%d/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            pass
    raise ValueError(f"Unrecognized server start date: {value!r}")


def display_name(value: str) -> str:
    return " ".join(value.strip().split()).title()


def parse_source(text: str) -> list[list[object]]:
    reader = csv.DictReader(io.StringIO(text))
    required = {"NEXUS", "SERVER #", "SERVER NAME", "START DATE"}
    fields = {field.strip() for field in (reader.fieldnames or []) if field}
    missing = required - fields
    if missing:
        raise ValueError(f"Roster source is missing columns: {', '.join(sorted(missing))}")

    rows: list[list[object]] = []
    seen: set[tuple[str, int]] = set()
    for raw in reader:
        nexus = (raw.get("NEXUS") or "").strip()
        number_text = (raw.get("SERVER #") or "").strip()
        name_text = (raw.get("SERVER NAME") or "").strip()
        if not (nexus and number_text and name_text):
            continue
        if not re.fullmatch(r"70\d{3}", nexus):
            raise ValueError(f"Unexpected Nexus value: {nexus!r}")
        try:
            number = int(float(number_text))
        except ValueError as exc:
            raise ValueError(f"Unexpected server number: {number_text!r}") from exc
        if not 1 <= number <= 16:
            raise ValueError(f"Server number outside 1-16: {nexus} #{number}")
        key = (nexus, number)
        if key in seen:
            raise ValueError(f"Duplicate server in source: {nexus} #{number}")
        seen.add(key)

        opened = iso_date(raw.get("START DATE") or "")
        previous = (
            (datetime.strptime(opened, "%Y-%m-%d").date() - timedelta(days=1)).isoformat()
            if opened
            else ""
        )
        rows.append([display_name(name_text), previous, opened, nexus, number])

    if len(rows) < 600:
        raise ValueError(f"Roster source returned only {len(rows)} valid rows; refusing to update")
    return rows


def merge_rows(
    existing: list[list[object]], source: list[list[object]]
) -> tuple[list[list[object]], int, int]:
    old_by_id = {(str(row[3]), int(row[4])): row for row in existing}
    merged = dict(old_by_id)
    added = 0
    updated = 0

    for incoming in source:
        key = (str(incoming[3]), int(incoming[4]))
        old = old_by_id.get(key)
        if old:
            # Existing entries may contain dates that were verified in-game after
            # the community sheet was published. Keep them authoritative, but fill
            # an opening date once a previously waitlisted server actually opens.
            source_previous, source_opened = incoming[1], incoming[2]
            incoming = list(old)
            if not old[2] and source_opened:
                incoming[1], incoming[2] = source_previous, source_opened
            if incoming != old:
                updated += 1
        else:
            added += 1
        merged[key] = incoming

    rows = sorted(merged.values(), key=lambda row: (int(row[3]), int(row[4])))
    return rows, added, updated


def render(rows: list[list[object]]) -> str:
    payload = json.dumps(rows, ensure_ascii=False, separators=(",", ":"))
    return f"{HEADER}window.SXS_SERVER_ROWS={payload};\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-url", default=DEFAULT_SOURCE)
    parser.add_argument("--input-csv", type=Path, help="Use a local CSV instead of downloading")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--existing", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()

    existing = read_existing(args.existing or args.output)
    source_text = (
        args.input_csv.read_text(encoding="utf-8-sig")
        if args.input_csv
        else download_csv(args.source_url)
    )
    source = parse_source(source_text)
    rows, added, updated = merge_rows(existing, source)
    result = render(rows)
    previous = args.output.read_text(encoding="utf-8") if args.output.exists() else ""
    if result != previous:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(result, encoding="utf-8", newline="\n")
        print(f"Updated {args.output}: {len(rows)} servers ({added} added, {updated} changed).")
    else:
        print(f"No roster changes: {len(rows)} servers.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Server roster update failed: {exc}", file=sys.stderr)
        raise
