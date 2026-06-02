#!/usr/bin/env python3
"""Generate lab-status.json from the phase markdown files.

For each docs/build-out/phase-*.md and docs/stretch/phase-*.md it reads:
  - id     from the filename  (phase-07-... -> 7)
  - title  from the H1        ('# Phase 7: Join a client (WS01)' -> 'Join a client (WS01)')
  - status from the first '**Status:**' line

Writes site/lab-status.json so it ships with the MkDocs output.
Run AFTER `mkdocs build` (needs site/ to exist).
"""
import json
import re
from datetime import datetime, timezone
from pathlib import Path

DOCS = Path("docs")
SITE = Path("site")
GUIDE_BASE_URL = "https://chweaver.github.io/ad-lab-guide/"

# Order matters: check longer phrases before single words.
STATUS_RULES = [
    ("not started", "planned"),
    ("in progress", "next"),
    ("done", "done"),
    ("next", "next"),
    ("stretch", "stretch"),
]


def normalize_status(raw: str) -> str:
    text = raw.strip().lower().split(".")[0].strip()  # 'stretch. beyond...' -> 'stretch'
    for key, value in STATUS_RULES:
        if text.startswith(key):
            return value
    return "planned"


def parse_phase(md_path: Path, track: str):
    text = md_path.read_text(encoding="utf-8")
    id_match = re.search(r"phase-(\d+)", md_path.stem)
    if not id_match:
        return None
    phase_id = int(id_match.group(1))
    h1_match = re.search(r"^#\s+Phase\s+\d+[:\-]\s*(.+)$", text, re.MULTILINE)
    title = h1_match.group(1).strip() if h1_match else md_path.stem
    status_match = re.search(r"\*\*Status:\*\*\s*(.+)", text)
    status = normalize_status(status_match.group(1)) if status_match else "planned"
    return {
        "id": phase_id,
        "title": title,
        "status": status,
        "track": track,
        "path": f"{track}/{md_path.stem}/",  # MkDocs use_directory_urls (default true)
    }


def main() -> None:
    phases = []
    for track in ("build-out", "stretch"):
        for md in sorted((DOCS / track).glob("phase-*.md")):
            phase = parse_phase(md, track)
            if phase:
                phases.append(phase)
    phases.sort(key=lambda p: p["id"])
    build_out = [p for p in phases if p["track"] == "build-out"]
    summary = {
        "total": len(phases),
        "buildOutTotal": len(build_out),
        "buildOutDone": sum(1 for p in build_out if p["status"] == "done"),
        "done": sum(1 for p in phases if p["status"] == "done"),
        "next": sum(1 for p in phases if p["status"] == "next"),
        "planned": sum(1 for p in phases if p["status"] == "planned"),
        "stretch": sum(1 for p in phases if p["status"] == "stretch"),
    }
    payload = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "guideBaseUrl": GUIDE_BASE_URL,
        "summary": summary,
        "phases": phases,
    }
    SITE.mkdir(exist_ok=True)
    out = SITE / "lab-status.json"
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {out} with {len(phases)} phases.")


if __name__ == "__main__":
    main()
