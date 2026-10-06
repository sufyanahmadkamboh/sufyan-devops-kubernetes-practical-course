#!/usr/bin/env python3
"""Every relative link in every Markdown file must point to a file or folder that exists."""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LINK = re.compile(r"\]\(([^)\s]+)\)")
bad = 0
for md in sorted(ROOT.rglob("*.md")):
    if any(part in {".git", "node_modules", "out"} for part in md.parts):
        continue
    text = re.sub(r"```.*?```", "", md.read_text(encoding="utf-8"), flags=re.S)   # ignore code blocks
    for target in LINK.findall(text):
        if re.match(r"^(https?:|mailto:|#)", target):
            continue
        path = target.split("#")[0]
        if path and not (md.parent / path).exists():
            print(f"{md.relative_to(ROOT)}: broken link -> {target}")
            bad += 1
print(f"{bad} broken link(s)")
sys.exit(1 if bad else 0)
