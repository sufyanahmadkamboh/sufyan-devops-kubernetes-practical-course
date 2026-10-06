"""Production layer: the title card, the end card and the sound cues around each video of the series.

Silent steps ("say": "") are held for "hold" seconds; build.py gives them silence instead of narration.
"""

from __future__ import annotations

import re
from pathlib import Path

from components import card, esc, grid

REPO = Path(__file__).resolve().parent.parent
REPO_URL = "github.com/sufyanahmadkamboh/sufyan-devops-kubernetes-practical-course"


def tested_blocks() -> int:
    """The ```bash blocks the CI runs: lessons, labs, challenges."""
    files = list((REPO / "docs").glob("[0-9][0-9]-*/README.md")) + list((REPO / "labs").rglob("*.md")) \
        + list((REPO / "challenges").rglob("*.md"))
    return sum(len(re.findall(r"^```bash$", p.read_text(encoding="utf-8"), re.M)) for p in files)


def _silent(hold: float, sfx: str | None = None) -> dict:
    return {"say": "", "tts": "", "hl": None, "zoom": 1, "sfx": sfx, "voice": "", "who": "", "hold": hold}


def _intro(title: str, subtitle: str, chips: list[str]) -> dict:
    chip_html = "".join(f'<span class="chip st" data-s="1">{esc(c)}</span>' for c in chips)
    module, _, name = title.partition(" · ")
    body = (
        '<div class="titlecard">'
        '<div class="tc-logo st" data-s="0">☸</div>'
        '<div class="tc-course st" data-s="0">Kubernetes Practical Course</div>'
        f'<div class="tc-name st" data-s="0">{esc(name or title)}</div>'
        f'<div class="tc-part st" data-s="1">{esc(module)} · {esc(subtitle)}</div>'
        f'<div class="tc-chips">{chip_html}</div>'
        '</div>')
    return {"chapter": None, "kicker": "Kubernetes, from zero to practical · every command real",
            "title": "&nbsp;", "body": body, "layout": "full",
            "steps": [_silent(1.9, "intro"), _silent(2.4, "pop")]}


def _outro(title: str) -> dict:
    body = grid([
        card(0, "💻", "The free course", REPO_URL, "ok"),
        card(1, "🧪", "Every command tested", f"{tested_blocks():,} code blocks run in CI on a fresh Minikube cluster", "blue"),
        card(1, "🏁", "Your turn", "type the lesson's commands, then break it on purpose and fix it", "amber"),
        card(1, "📚", "Then", "the lab of the level, the 14 troubleshooting problems, the challenges and the capstone", "blue"),
    ], cols=2)
    return {"chapter": None, "kicker": esc(title), "title": "Thanks for watching", "body": body, "layout": "full",
            "steps": [_silent(2.2, "outro"), _silent(5.0)]}


CSS = """
.titlecard{height:100%;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:14px;margin-top:-40px}
.tc-logo{font-size:140px;line-height:1;color:#1d91e6}
.tc-course{font-size:34px;font-weight:800;letter-spacing:4px;text-transform:uppercase;color:#8ec9ff}
.tc-name{font-size:92px;font-weight:900;letter-spacing:-3px;color:#f1f6fc;text-align:center;line-height:1.05}
.tc-part{font-size:40px;font-weight:800;color:#ffc94d}
.tc-chips{display:flex;flex-wrap:wrap;justify-content:center;gap:14px;margin-top:18px;max-width:1600px}
.chip{background:#13233a;border:3px solid #1d91e6;border-radius:40px;padding:8px 24px;font-size:26px;font-weight:800;color:#f1f6fc}
.speaker{display:none;position:absolute;right:100px;top:56px;padding:8px 22px;border-radius:30px;font-size:24px;font-weight:800;letter-spacing:1px}
.speaker.now{display:block}
.speaker.senior{background:#1e3a5f;border:3px solid #3b82d6;color:#cfe3fb}
.speaker.junior{background:#3a2a12;border:3px solid #f59e0b;color:#fde7c0}
"""


def package(scenes: list[dict], title: str, subtitle: str, chips: list[str]) -> None:
    """Add the title card and the end card. YouTube chapters must start at 0:00: the first chapter moves to the title."""
    intro = _intro(title, subtitle, chips)
    intro["chapter"], scenes[0]["chapter"] = scenes[0]["chapter"], None
    scenes.insert(0, intro)
    scenes.append(_outro(title))
