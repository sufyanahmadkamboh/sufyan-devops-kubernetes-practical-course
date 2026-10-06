"""The video series, generated from the lessons: one video per module (01-16, 18-20), plus the 25 troubleshooting
problems and the capstone.

Every lesson becomes the same five scenes, played as a conversation between a senior DevOps engineer and a junior
colleague (two voices):

  concept    the junior asks; the senior explains, with the lesson's diagram on screen
  demo       the lab and the demonstration commands, with their real outputs (recorded when the tests ran)
  break      the junior makes the lesson's mistake on purpose (error tone); the senior reads the symptoms
  fix        the fix, with its real output (success chime)
  recap      the three points to remember

Nothing on screen is typed by hand: commands and outputs are the lesson's tested blocks, diagrams are the lesson's
own. Narration is the lesson's text, cleaned up for speech.
"""

from __future__ import annotations

import re
from pathlib import Path

from components import card, checklist, code, esc, grid, terminal

REPO = Path(__file__).resolve().parent.parent
SENIOR, JUNIOR = "senior", "junior"
VOICES = {SENIOR: "Microsoft David Desktop", JUNIOR: "Microsoft Zira Desktop"}

# --------------------------------------------------------------------------------------------- markdown parsing
FENCE = re.compile(r"^(<!-- test[^>]*-->\n)?```(bash|text)\n(.*?)\n```", re.M | re.S)


def section(text: str, name: str, level: int = 2) -> str:
    """The body of the heading `name` (at `level`), up to the next heading of the same or a higher level.
    Lines inside fenced code blocks are never headings (outputs can contain "# Cafe")."""
    out, inside, fence = [], False, False
    for ln in text.split("\n"):
        if ln.startswith("```"):
            fence = not fence
        heading = None if fence or ln.startswith("```") else re_heading(ln)
        if heading and heading[0] <= level:
            if inside:
                break
            inside = heading[0] == level and heading[1] == name
            continue
        if inside:
            out.append(ln)
    return "\n".join(out).strip()


def re_heading(ln: str):
    m = re.match(r"^(#{1,6}) (.+?)\s*$", ln)
    return (len(m.group(1)), m.group(2)) if m else None


def items(md: str) -> list[tuple[str, str]]:
    """The section as a sequence of ("prose", text) / ("bash", code) / ("output", text), in order."""
    out, pos = [], 0
    md = re.sub(r"<details>.*?</details>", "", md, flags=re.S)
    for m in FENCE.finditer(md):
        prose = re.sub(r"<!--.*?-->", "", md[pos:m.start()]).strip()
        if prose:
            out.append(("prose", prose))
        out.append(("bash" if m.group(2) == "bash" else "output", m.group(3)))
        pos = m.end()
    rest = re.sub(r"<!--.*?-->", "", md[pos:]).strip()
    if rest:
        out.append(("prose", rest))
    return out


def runs(md: str) -> list[dict]:
    """Bash blocks with the prose before them and their recorded output (if any)."""
    seq, result, prose = items(md), [], ""
    for i, (kind, text) in enumerate(seq):
        if kind == "prose":
            prose = text
        elif kind == "bash":
            out = seq[i + 1][1] if i + 1 < len(seq) and seq[i + 1][0] == "output" else ""
            after = seq[i + 2][1] if i + 2 < len(seq) and seq[i + 2][0] == "prose" and out else (
                seq[i + 1][1] if i + 1 < len(seq) and seq[i + 1][0] == "prose" else "")
            result.append({"prose": prose, "bash": text, "out": out, "after": after})
            prose = ""
    return result


def first_prose(md: str) -> str:
    for kind, text in items(md):
        if kind == "prose":
            return text
    return ""


def visual(md: str) -> str:
    for kind, text in items(md):
        if kind == "output":          # the Visual section's ```text block
            return text
    return ""


def bullets(md: str) -> list[str]:
    return [re.sub(r"^\s*[-*]\s+", "", l).strip() for l in md.splitlines() if re.match(r"^\s*[-*]\s+", l)]


# --------------------------------------------------------------------------------------------- text for screen and speech
def plain(md: str) -> str:
    """Markdown → readable text (captions)."""
    t = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", md)
    t = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", t)
    t = re.sub(r"\*\*([^*]+)\*\*", r"\1", t)
    t = re.sub(r"(?<!\w)\*([^*]+)\*(?!\w)", r"\1", t)
    t = t.replace("`", "")
    t = re.sub(r"^\s*[-*]\s+", "", t, flags=re.M)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def sentences(text: str, limit: int) -> str:
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z`(\"'])", text.strip())
    out = " ".join(parts[:limit]).strip()
    return out if out.endswith((".", "!", "?", ":")) else out + "."


def code_words(code_text: str) -> str:
    """Inline code read aloud: options without dashes, symbols as words."""
    t = code_text
    t = re.sub(r"HEAD~(\d+)", r"head tilde \1", t)
    t = re.sub(r"HEAD\^(\d)", r"head caret \1", t)
    t = re.sub(r"@\{(\w+)\}", r" at \1", t)
    t = re.sub(r"(?<!\w)--?([a-z])", r"\1", t)
    t = t.replace("...", " three dots ").replace("..", " two dots ")
    t = t.replace("/", " slash ").replace("~", "home ").replace("=", " equals ").replace("|", " pipe ")
    t = re.sub(r"[\"'<>{}\[\]()*]", " ", t)
    t = t.replace("-", " ").replace("_", " ").replace(":", " ")
    return re.sub(r"\s+", " ", t).strip()


SAY = [  # how the speech engine should say words it would otherwise mangle (captions keep the real spelling)
    (r"\betcd\b", "et see dee"), (r"\bkubelet\b", "kube let"), (r"\bkube-proxy\b", "kube proxy"),
    (r"\bkube-apiserver\b", "kube A P I server"), (r"\bCoreDNS\b", "core D N S"), (r"\bk8s\b", "kubernetes"),
    (r"\bConfigMaps?\b", "config map"), (r"\bReplicaSets?\b", "replica set"), (r"\bStatefulSets?\b", "stateful set"),
    (r"\bDaemonSets?\b", "daemon set"), (r"\bCronJobs?\b", "cron job"), (r"\bServiceAccounts?\b", "service account"),
    (r"\bNetworkPolic(y|ies)\b", "network policy"), (r"\bClusterIP\b", "cluster I P"), (r"\bNodePort\b", "node port"),
    (r"\bHPA\b", "H P A"), (r"\bPVCs?\b", "P V C"), (r"\bPVs?\b", "P V"), (r"\bRBAC\b", "R back"),
    (r"\bCNI\b", "C N I"), (r"\b[Mm]inikube\b", "mini kube"), (r"\bcrictl\b", "C R I control"),
    (r"\bLoadBalancer\b", "load balancer"), (r"\bemptyDir\b", "empty dir"), (r"\bStorageClass(es)?\b", "storage class"),
    (r"\.dockerignore\b", "dot docker ignore"), (r"\bdockerd\b", "docker D"), (r"\bcontainerd\b", "container D"),
    (r"\brunc\b", "run C"), (r"\bcgroups?\b", "C groups"), (r"\bbuildx\b", "build X"), (r"\bBuildx\b", "build X"),
    (r"\bBuildKit\b", "build kit"), (r"\bENTRYPOINT\b", "entry point"), (r"\bCMD\b", "C M D"),
    (r"\bWORKDIR\b", "work dir"), (r"\bHEALTHCHECK\b", "health check"), (r"\bEXPOSE\b", "expose"),
    (r"\bARG\b", "arg"), (r"\bENV\b", "env"), (r"\bOOMKilled\b", "O O M killed"), (r"\bOOM\b", "out of memory"),
    (r"\bPID\b", "P I D"), (r"\bnpm\b", "N P M"), (r"\bJDK\b", "J D K"), (r"\bJRE\b", "J R E"), (r"\bJVM\b", "J V M"),
    (r"\bPHP-FPM\b", "P H P F P M"), (r"\bPHP\b", "P H P"), (r"\bFPM\b", "F P M"), (r"\bPostgreSQL\b", "postgres Q L"),
    (r"\bdistroless\b", "distro-less"), (r"\blocalhost\b", "local host"), (r"\btmpfs\b", "temp F S"),
    (r"\bDNS\b", "D N S"), (r"\bIP\b", "I P"), (r"\bCPUs?\b", "C P U"), (r"\bCVEs?\b", "C V E"), (r"\bNAT\b", "nat"),
    (r"\bamd64\b", "A M D 64"), (r"\barm64\b", "arm 64"), (r"\bOCI\b", "O C I"), (r"\bVMs?\b", "V M"),
    (r"\bWSL\b", "W S L"), (r"\bMB\b", "megabytes"), (r"\bGB\b", "gigabytes"), (r"\bMiB\b", "mebibytes"),
    (r"\bTLS\b", "T L S"), (r"\bECR\b", "E C R"), (r"\bpgx\b", "P G X"), (r"\bgunicorn\b", "green unicorn"),
    (r"\bHEAD\b", "head"), (r"\bORIG_HEAD\b", "orig head"), (r"\bMERGE_HEAD\b", "merge head"),
    (r"\breflog\b", "ref log"), (r"\bREADME\b", "read me"), (r"\.gitignore\b", "dot git ignore"),
    (r"\bgitignore\b", "git ignore"), (r"\.gitattributes\b", "dot git attributes"), (r"\.gitmodules\b", "dot git modules"),
    (r"\.env\b", "dot env"), (r"\bGitHub\b", "git hub"), (r"\bGitLab\b", "git lab"), (r"\bgh\b", "G H"),
    (r"\bCI/CD\b", "C I C D"), (r"\bCI\b", "C I"), (r"\bCD\b", "C D"), (r"\bPRs\b", "P Rs"), (r"\bPR\b", "P R"),
    (r"\bGHCR\b", "G H C R"), (r"\bYAML\b", "yammel"), (r"\.yaml\b", " dot yammel"), (r"\.yml\b", " dot yammel"),
    (r"\bJSON\b", "jason"), (r"\.json\b", " dot jason"), (r"\.txt\b", " dot text"), (r"\.md\b", " dot M D"),
    (r"\.sh\b", " dot S H"), (r"\bSHA\b", "shah"), (r"\bSHA-256\b", "shah 256"), (r"\bSSH\b", "S S H"),
    (r"\bHTTPS\b", "H T T P S"), (r"\bHTTP\b", "H T T P"), (r"\bURLs?\b", "U R L"), (r"\bAPI\b", "A P I"),
    (r"\bCLI\b", "C L I"), (r"\bGPG\b", "G P G"), (r"\bLFS\b", "L F S"), (r"\bID\b", "I D"), (r"\bIDs\b", "I Ds"),
    (r"\bOS\b", "O S"), (r"\bOAuth\b", "oh auth"), (r"\bDevOps\b", "dev ops"), (r"\bGitOps\b", "git ops"),
    (r"\bkubectl\b", "kube control"), (r"\bkind\b", "kind"), (r"\bnginx\b", "engine x"), (r"\bHelm\b", "helm"),
    (r"\bsemver\b", "sem ver"), (r"\bvs\.?\b", "versus"), (r"\be\.g\.", "for example"), (r"\bi\.e\.", "that is"),
    (r"\bstdin\b", "standard in"), (r"\bstdout\b", "standard out"), (r"\bstderr\b", "standard error"),
    (r"\bcat-file\b", "cat file"), (r"\bfilter-repo\b", "filter repo"), (r"\bfsck\b", "F S check"),
    (r"\brerere\b", "re re re"), (r"\bzdiff3\b", "Z diff 3"), (r"\bdiff3\b", "diff 3"), (r"\bAKIA\b", "A K I A"),
    (r"\bTODO\b", "to do"), (r"\bWIP\b", "work in progress"), (r"\bOIDC\b", "O I D C"), (r"\b2FA\b", "two factor"),
    (r"\bCODEOWNERS\b", "code owners"), (r"\bmacOS\b", "mac O S"), (r"\bUbuntu\b", "oo-boon-too"),
    (r"\bv(\d+)\.(\d+)\.(\d+)\b", r"version \1 point \2 point \3"), (r"\bpatch-id\b", "patch I D"),
    (r"→", " to "), (r"≠", " not "), (r"…", "."), (r"·", ","), (r"—|–", ", "), (r"\s&\s", " and "),
]


def speech(md: str) -> str:
    t = re.sub(r"`([^`]+)`", lambda m: code_words(m.group(1)), md)
    t = plain(t)
    for pattern, repl in SAY:
        t = re.sub(pattern, repl, t)
    return re.sub(r"\s+", " ", t).strip()


def step(who: str, md: str, limit: int = 2, sfx: str | None = None, zoom: float = 1, hold: float = 0) -> dict:
    text = sentences(plain(md), limit) if md else ""
    spoken = sentences(speech(md), limit) if md else ""
    return {"say": text, "tts": spoken, "hl": None, "zoom": zoom, "sfx": sfx, "voice": VOICES[who], "who": who,
            "hold": hold}


def line(who: str, text: str, sfx: str | None = None) -> dict:
    return step(who, text, limit=9, sfx=sfx)


# --------------------------------------------------------------------------------------------- terminal content
def classify(text: str) -> str:
    low = text.lower()
    if re.search(r"\b(fatal|error|conflict|rejected|failed|fail |missing|denied|refusing|not possible|cannot|"
                 r"unhealthy|oomkilled|not found|exited \((?!0\))|toomanyrequests|unauthorized|read-only file system)\b", low):
        return "bad"
    if re.search(r"\b(successfully|ok |all checks passed|deployed|complete|healthy\)|\(healthy|started|pass )", low):
        return "ok"
    if low.startswith(("hint:", "warning:")):
        return "dim"
    return ""


def term_lines(run: dict, s: int, max_out: int = 14) -> list[tuple[int, str, str]]:
    lines = []
    for raw in run["bash"].splitlines():
        if not raw.strip():
            continue
        lines.append((s, ("  " if raw.startswith(" ") else "$ ") + raw.rstrip() if not raw.lstrip().startswith("#")
                      else raw.rstrip(), "dim" if raw.lstrip().startswith("#") else "cmd"))
    out = [l for l in run["out"].splitlines()]
    if len(out) > max_out:
        out = out[:max_out - 1] + [f"… ({len(out) - max_out + 1} more lines)"]
    lines += [(s, l, classify(l)) for l in out]
    return lines


def fits(lines: list[tuple[int, str, str]], limit: int = 21) -> list[tuple[int, str, str]]:
    """Keep the terminal readable: drop the oldest steps' lines when the panel would overflow."""
    while len(lines) > limit:
        first = lines[0][0]
        rest = [l for l in lines if l[0] != first]
        if not rest:
            return lines[-limit:]
        lines = rest
    return lines


# --------------------------------------------------------------------------------------------- scenes
QUESTIONS = ["Can you show me {t}?", "I keep hearing about {t}. What is it, really?", "How does {t} work?",
             "Why would I need {t}?", "What should I know about {t}?"]


def question(title: str, n: int) -> str:
    if re.match(r"(What|How|Why|When) ", title):
        return title.rstrip("?") + "?"
    keep = ("Kubernetes", "Pods", "Pod", "kubectl", "Minikube", "ReplicaSets", "Deployments", "Services", "ConfigMaps",
            "Secrets", "Jobs", "CronJobs", "DaemonSets", "StatefulSets", "Ingress", "NetworkPolicies", "ServiceAccounts",
            "RBAC", "Helm", "Horizontal", "DNS")
    topic = title if title.startswith(keep) else title[0].lower() + title[1:]
    return QUESTIONS[n % len(QUESTIONS)].format(t=topic)


def visual_panel(text: str, title: str = "visual") -> str:
    longest = max((len(l) for l in text.splitlines()), default=40)
    rows = len(text.splitlines())
    size = max(15, min(26, int(1680 / (longest * 0.62)), int(660 / (rows * 1.5))))
    return code(title, text, lang="text", size=size)


TERMINAL = "~/kubernetes-practical-course"


def lesson_scenes(readme: Path, n: int, module: str) -> list[dict]:
    text = readme.read_text(encoding="utf-8")
    number, title = re.match(r"# (\d+) · (.+)", text).groups()
    title = title.strip()
    kicker = f"{module} · Lesson {number}"
    scenes = []

    # 1 · concept, over the lesson's architecture diagram
    concept = first_prose(section(text, "What is it?"))
    vis = visual(section(text, "Architecture")) or visual(section(text, "How does it work?"))
    body = visual_panel(vis) if vis else grid([card(1, "💡", title, esc(plain(concept)), "blue")], cols=1)
    why = first_prose(section(text, "Why do we need it?"))
    scenes.append({"chapter": f"{number} · {title}", "kicker": kicker, "title": esc(title), "body": body,
                   "layout": "full",
                   "steps": [line(JUNIOR, question(title, n)), step(SENIOR, concept, 4)]
                   + ([step(SENIOR, why, 3)] if why else [])})

    how = first_prose(section(text, "How does it work?"))
    if how and vis:
        scenes.append({"chapter": None, "kicker": kicker, "title": "How it works", "body": body, "layout": "full",
                       "steps": [line(JUNIOR, "And how does it actually work?"), step(SENIOR, how, 4)]})

    # 2 · the hands-on lab: its first commands with their real output
    demo = [r for r in runs(section(text, "Hands-On Lab")) if r["out"] or "kubectl" in r["bash"]][:4]
    if demo:
        steps, lines = [], []
        for r in demo:
            k = len(steps)
            narr = r["prose"] or r["after"] or "Let's run it."
            if r["after"] and r["out"]:
                narr = (r["prose"] + " " + r["after"]) if r["prose"] else r["after"]
            steps.append(step(SENIOR, narr, 3))
            lines += term_lines(r, k)
        scenes.append({"chapter": None, "kicker": kicker, "title": "Let's run it", "layout": "full",
                       "body": terminal(fits(lines), f"{TERMINAL} · lesson {number}"), "steps": steps})

    # 2b · inspect: the first command that looks inside, with its output
    ins = [r for r in runs(section(text, "Inspect")) if r["out"]][:1] or runs(section(text, "Inspect"))[:1]
    if ins:
        r = ins[0]
        scenes.append({"chapter": None, "kicker": kicker, "title": "Look inside", "layout": "full",
                       "body": terminal(fits(term_lines(r, 0)), f"{TERMINAL} · inspect"),
                       "steps": [line(JUNIOR, "How do I see what Kubernetes did?"),
                                 step(SENIOR, r["prose"] or first_prose(section(text, "Inspect")) or "Ask the cluster.", 3)]})

    # 3 · break it (the junior's mistake) and troubleshoot it
    brk = runs(section(text, "Break It"))
    trouble = section(text, "Troubleshoot It")
    if brk:
        r = brk[0]
        intro = r["prose"] or first_prose(section(text, "Break It"))
        lines = term_lines(r, 0)
        steps = [step(JUNIOR, "Let me try something. " + intro, 2, sfx="error")]
        tr = [t for t in runs(trouble) if t["out"]]
        if tr:
            lines += term_lines(tr[0], 1, max_out=8)
        steps.append(step(SENIOR, first_prose(trouble) or "Read what Kubernetes tells you: events first.", 4))
        scenes.append({"chapter": None, "kicker": kicker, "title": "Break it, on purpose", "layout": "full",
                       "body": terminal(fits(lines), f"{TERMINAL} · the mistake"), "steps": steps})

    # 4 · the fix: its own section, or the last command of the troubleshooting
    fix = runs(section(text, "Fix It")) or runs(trouble)[-1:]
    if fix and brk:
        r = fix[0]
        narr = r["prose"] or first_prose(section(text, "Fix It")) or "Here is the fix."
        scenes.append({"chapter": None, "kicker": kicker, "title": "Fix it", "layout": "full",
                       "body": terminal(fits(term_lines(r, 0)), f"{TERMINAL} · the fix"),
                       "steps": [step(SENIOR, narr, 2, sfx="success")]})

    # 4b · break scenarios (the capstone): break, investigation and fix of each
    for sub in re.findall(r"^### (Break \d+ · .+)$", text, re.M):
        body_md = section(text, sub, level=3)
        rs = [r for r in runs(body_md) if r["out"]] or runs(body_md)
        if not rs:
            continue
        lines, steps = [], [step(JUNIOR, first_prose(body_md) or sub, 2, sfx="error")]
        for k, r in enumerate(rs[:2]):
            lines += term_lines(r, k, max_out=8)
            if k:
                steps.append(step(SENIOR, r["prose"] or "Follow the evidence.", 3))
        why = re.search(r"\*Root cause:\*\s*(.+?)(?:\n\n|$)", body_md, re.S)
        if why:
            steps.append(step(SENIOR, "Root cause: " + why.group(1), 3, sfx="success"))
        scenes.append({"chapter": sub.split(" · ", 1)[1][:60], "kicker": f"{kicker} · {sub.split(' · ')[0]}",
                       "title": esc(sub), "layout": "full", "body": terminal(fits(lines), f"{TERMINAL} · capstone"),
                       "steps": steps})

    # 5 · key takeaways
    rec = [b for b in bullets(section(text, "Key Takeaways")) if not b.startswith("Real-world use")][:3]
    if rec:
        items_ = [(k + 1, esc(plain(b).split(":")[0] if len(plain(b)) > 70 and ":" in plain(b) else plain(b)), "")
                  for k, b in enumerate(rec)]
        steps = [line(JUNIOR, "Got it. What do I need to remember?")] + [step(SENIOR, b, 2) for b in rec]
        scenes.append({"chapter": None, "kicker": kicker, "title": "Remember", "layout": "full",
                       "body": checklist(items_), "steps": steps})
    return scenes


# the roadmap of the README: one video per level
LEVELS = [
    (1, "Kubernetes fundamentals", ["01", "02", "03"]),
    (2, "kubectl", ["04", "05"]),
    (3, "Pods", ["06", "07"]),
    (4, "Deployments", ["08", "09"]),
    (5, "Services", ["10"]),
    (6, "Configuration", ["11", "12"]),
    (7, "Storage", ["13"]),
    (8, "Health checks", ["14"]),
    (9, "Resources and scheduling", ["15", "16"]),
    (10, "Jobs, CronJobs and DaemonSets", ["17", "18"]),
    (11, "Stateful applications", ["19"]),
    (12, "Ingress and networking", ["20", "21", "22"]),
    (13, "Security and RBAC", ["23", "24"]),
    (14, "Scaling and autoscaling", ["25", "26"]),
    (15, "Troubleshooting and Helm", ["27", "28"]),
    (16, "The capstone", ["29"]),
]


def module_parts() -> list[dict]:
    """One entry per video: number, slug, title, subtitle, files."""
    parts = []
    for n, name, lessons in LEVELS:
        files = [next((REPO / "docs").glob(f"{d}-*/README.md")) for d in lessons]
        slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
        span = f"Lesson {int(lessons[0])}" if len(lessons) == 1 else f"Lessons {int(lessons[0])}–{int(lessons[-1])}"
        parts.append({"part": n, "slug": f"{n:02d}-{slug}", "title": f"Level {n} · {name}", "subtitle": span,
                      "kind": "module", "files": files})
    problems = sorted((REPO / "labs/12-troubleshooting").glob("[0-9][0-9]-*.md"))
    parts.append({"part": 17, "slug": "17-troubleshooting-lab", "title": "Troubleshooting lab · 14 broken clusters",
                  "subtitle": f"{len(problems)} problems, from symptom to fix", "kind": "troubleshooting",
                  "files": problems})
    return parts


def troubleshooting_scenes(path: Path, n: int) -> list[dict]:
    text = path.read_text(encoding="utf-8")
    m = re.match(r"# (?:Problem )?(\d+)\s*·\s*(.+)", text)
    number, name = (m.group(1), m.group(2).strip()) if m else (f"{n + 1:02d}", path.stem)
    kicker = f"Troubleshooting lab · Problem {number}"
    first = runs(section(text, "First command to run"))
    sym = runs(section(text, "Symptoms")) or runs(section(text, "Problem"))
    inv = runs(section(text, "Investigation"))
    fix = runs(section(text, "Fix"))
    lines, steps = [], [step(JUNIOR, first_prose(section(text, "Problem")) or name, 2, sfx="error")]
    for r in (first or sym)[-1:]:
        lines += term_lines(r, 0, max_out=8)
    if inv:
        steps.append(step(SENIOR, inv[0]["prose"] or first_prose(section(text, "Investigation")), 2))
        lines += term_lines(inv[0], 1, max_out=8)
    steps.append(step(SENIOR, first_prose(section(text, "Root cause")), 2))
    scenes = [{"chapter": f"{number} · {name}"[:60], "kicker": kicker, "title": esc(name), "layout": "full",
               "body": terminal(fits(lines), f"{TERMINAL} · investigate"), "steps": steps}]
    if fix:
        lesson = first_prose(section(text, "Lesson learned"))
        scenes.append({"chapter": None, "kicker": kicker, "title": "Fix and verify", "layout": "full",
                       "body": terminal(fits(term_lines(fix[0], 0, max_out=10)), f"{TERMINAL} · fix"),
                       "steps": [step(SENIOR, fix[0]["prose"] or first_prose(section(text, "Fix")), 2, sfx="success")]
                       + ([step(SENIOR, lesson, 1)] if lesson else [])})
    return scenes


def build(part: int) -> tuple[dict, list[dict]]:
    info = next(p for p in module_parts() if p["part"] == part)
    scenes: list[dict] = []
    if info["kind"] == "module":
        for n, f in enumerate(info["files"]):
            scenes += lesson_scenes(f, n, info["title"].split(" · ")[0])
    else:
        for n, f in enumerate(info["files"]):
            scenes += troubleshooting_scenes(f, n)
    return info, scenes


if __name__ == "__main__":
    import sys
    for p in module_parts():
        if len(sys.argv) > 1 and str(p["part"]) not in sys.argv[1:]:
            continue
        info, scenes = build(p["part"])
        words = sum(len(s["say"].split()) for sc in scenes for s in sc["steps"])
        print(f"{p['part']:02d} {info['title']:<50} {len(scenes):3d} scenes {words:5d} words ≈ {words / 150:4.1f} min")
