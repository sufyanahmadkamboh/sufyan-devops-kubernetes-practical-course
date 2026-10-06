"""Builds one video of the series (PART: see video/series.py), or all of them.

    python video/build.py PART [page|frames|audio|video|post|all]     one video (default: all steps)
    python video/build.py all                                        every video, then AUDIO-LICENSES.md
    python video/build.py licenses                                   AUDIO-LICENSES.md from the built videos

Steps for one video:
  page    out/partNN/page.html (all scenes; ?sc=<scene>&st=<step> shows one frame)
  frames  screenshot every scene/step with headless Edge (shot.mjs), plus the thumbnail
  audio   narrate every step with the Windows speech engine (tts.ps1): senior and junior voices
  video   encode one clip per scene (fades), join, add the narration; youtube/partNN/captions.srt, chapters.txt,
          description.md
  post    voice clean-up, original music bed ducked under the voice, sound effects, loudness -14 LUFS; writes
            out/partNN/<name>-full.mp4     picture + voice + music + sound effects
            out/partNN/<name>-silent.mp4   the identical picture stream (copied, frame for frame), no audio
          and youtube/partNN/audio-events.json (the timestamps of every sound, for AUDIO-LICENSES.md)

Requirements: Python 3 with pygments, numpy and scipy, Node.js 22+, Microsoft Edge, Windows (System.Speech), Docker.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import wave
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from pygments.formatters import HtmlFormatter  # noqa: E402

import series  # noqa: E402
from components import SVG_DEFS  # noqa: E402
from production import CSS as PRODUCTION_CSS  # noqa: E402
from production import package  # noqa: E402
from redact import check, redact  # noqa: E402

FPS = 30
LEAD, GAP, TAIL, FADE = 0.5, 0.55, 0.7, 0.3   # seconds
ANIM = [0.488, 0.784, 0.936, 0.992]            # eased build-in of newly revealed elements, one frame each
RATE = 24000                                   # narration WAV: 24 kHz, 16-bit, mono
SPEED = "0"                                    # speech engine rate, -10..10
FFMPEG_IMAGE = "linuxserver/ffmpeg@sha256:a7182d4fe498feea393622b43513cfaecb3fd073dcd3c7f38e9d74a10a4e8702"
REPO_URL = "https://github.com/sufyanahmadkamboh/sufyan-devops-kubernetes-practical-course"


class Part:
    def __init__(self, number: int):
        self.info, self.scenes = series.build(number)
        chips = [re.sub(r"^Lesson \d+ · ", "", s["chapter"]) for s in self.scenes if s["chapter"]][:6]
        package(self.scenes, self.info["title"], self.info["subtitle"], chips)
        self.number = number
        self.name = f"k8s-course-{number:02d}-" + re.sub(r"^\d+-", "", self.info["slug"])
        self.out = HERE / "out" / f"part{number:02d}"
        self.frames, self.audio = self.out / "frames", self.out / "audio"
        self.yt = HERE / "youtube" / f"part{number:02d}"


def spoken(step: dict) -> str:
    return redact(step["tts"] or step["say"])


def frame_name(sc: int, st: int) -> str:
    return f"s{sc:03d}_{st:02d}"


# ------------------------------------------------------------------------------------------------ page
CSS = """
:root{--bg:#0b1420;--panel:#13233a;--line:#284468;--ink:#f1f6fc;--muted:#a9bbd2;--blue:#3b82d6;--sky:#9cc3f0;--ok:#4cc286;--bad:#ff6b6b;--amber:#ffc94d}
*{box-sizing:border-box;margin:0;padding:0}
html,body{width:1920px;height:1080px;overflow:hidden}
body{background:radial-gradient(1300px 800px at 100% 0%,rgba(29,145,230,.20),transparent 60%),radial-gradient(1000px 700px at 0% 100%,rgba(156,195,240,.09),transparent 60%),var(--bg);
 font-family:Inter,"Segoe UI",sans-serif;color:var(--ink);position:relative}
body::before{content:"";position:absolute;inset:0;background-image:linear-gradient(rgba(156,195,240,.045) 1px,transparent 1px),linear-gradient(90deg,rgba(156,195,240,.045) 1px,transparent 1px);background-size:60px 60px}
.scene{display:none;position:absolute;inset:0}
.scene.on{display:block}
.kicker{position:absolute;left:100px;top:58px;color:#8ec9ff;font-weight:800;font-size:24px;letter-spacing:3px;text-transform:uppercase}
h1{position:absolute;left:100px;right:420px;top:96px;font-size:56px;line-height:1.08;font-weight:900;letter-spacing:-1px}
.content{position:absolute;left:100px;right:100px;top:205px;bottom:115px;display:flex;flex-direction:column;align-items:center;justify-content:center}
.st{opacity:0;transition:none}
.st.on{opacity:1}
.grid{display:grid;width:100%}
.card{display:flex;gap:22px;align-items:flex-start;background:var(--panel);border:3px solid var(--line);border-left:10px solid var(--tone);border-radius:22px;padding:24px 26px;min-height:120px}
.card.now{box-shadow:0 0 0 4px var(--tone),0 0 40px rgba(255,255,255,.12);background:#182c49}
.card-icon{font-size:46px;line-height:1}
.card-title{font-size:29px;font-weight:800;margin-bottom:8px}
.card-text{font-size:24px;color:var(--muted);line-height:1.4}
.checklist{list-style:none;width:100%;display:flex;flex-direction:column;gap:20px}
.checklist li{display:flex;gap:26px;align-items:center;background:var(--panel);border:3px solid var(--line);border-radius:20px;padding:20px 26px}
.checklist li.now{border-color:var(--ok);background:#0f2a22}
.checklist .num{flex:0 0 64px;height:64px;border-radius:50%;background:#1d91e6;display:flex;align-items:center;justify-content:center;font-size:30px;font-weight:900}
.checklist b{display:block;font-size:31px;line-height:1.3}.checklist span{font-size:23px;color:var(--muted)}
.code{background:#0a0f18;border:3px solid var(--line);border-radius:20px;overflow:hidden;width:100%}
.code-bar{display:flex;gap:10px;align-items:center;padding:14px 20px;background:#101b2c;border-bottom:2px solid var(--line)}
.code-bar i{width:14px;height:14px;border-radius:50%;background:#ff6b6b}.code-bar i:nth-child(2){background:#ffc94d}.code-bar i:nth-child(3){background:#4cc286}
.code-bar span{margin-left:14px;font:600 20px "JetBrains Mono",Consolas,monospace;color:var(--muted)}
.code pre{font:500 var(--fs) / 1.45 "JetBrains Mono",Consolas,monospace;padding:18px 0;white-space:pre;font-variant-ligatures:none;overflow:hidden;color:#dbe7f5}
.code pre > span[id]{display:block;padding:0 24px;border-left:6px solid transparent}
.term{background:#0a0f18;border:3px solid var(--line);border-radius:20px;overflow:hidden;width:100%;padding-bottom:14px}
.tl{font:500 var(--ts,24px)/1.62 "JetBrains Mono",Consolas,monospace;padding:0 24px;white-space:pre;overflow:hidden;color:#c9d6e6;font-variant-ligatures:none}
.tl.cmd{color:#9cc3f0;font-weight:700}.tl.ok{color:#4cc286}.tl.bad{color:#ff8a8a}.tl.warn{color:#ffc94d}.tl.dim{color:#7f93ad;font-style:italic}
.tl.now{background:rgba(255,201,77,.08)}
.term{padding-top:0}.term .code-bar{margin-bottom:12px;position:relative;z-index:2}
.term .tz{will-change:transform}
.bottom{position:absolute;left:100px;right:100px;bottom:40px;display:flex;align-items:center;gap:28px;font-size:22px;color:var(--muted)}
.bottom b{color:var(--ink)}
.bar{flex:1;display:flex;gap:6px}
.bar i{flex:1;height:8px;border-radius:4px;background:#22344f}
.bar i.done{background:#1d6fb8}.bar i.cur{background:var(--amber)}
.chap{color:var(--amber);font-weight:800;max-width:560px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
"""

JS = """
const q = new URLSearchParams(location.search);
const sc = +(q.get("sc") || 0), st = +(q.get("st") || 0), p = q.has("p") ? +q.get("p") : 1;
const scene = document.querySelector(`.scene[data-i="${sc}"]`);
scene.classList.add("on");
scene.querySelectorAll("[data-s]").forEach(e => {
  const s = +e.dataset.s;
  if (s <= st) e.classList.add("on");
  if (s === st) {
    e.classList.add("now");
    if (p < 1 && !e.classList.contains("speaker")) { e.style.opacity = p; e.style.transform = `translateY(${((1 - p) * 18).toFixed(1)}px)`; }
  }
});
// The terminal follows the newest lines: when the panel is fuller than the screen, it scrolls up smoothly.
const tz = scene.querySelector(".term .tz");
if (tz) {
  const box = tz.parentElement.getBoundingClientRect();
  const visible = [...tz.querySelectorAll(".tl.on")];
  if (visible.length) {
    const bottom = visible[visible.length - 1].getBoundingClientRect().bottom;
    const over = bottom - (box.bottom - 16);
    if (over > 0) tz.style.transform = `translateY(${(-over).toFixed(1)}px)`;
  }
}
window.__ready = true;
"""


def chapters(scenes: list[dict]) -> list[tuple[int, str]]:
    return [(i, s["chapter"]) for i, s in enumerate(scenes) if s["chapter"]]


def write_page(part: Part) -> Path:
    part.out.mkdir(parents=True, exist_ok=True)
    part.yt.mkdir(parents=True, exist_ok=True)
    chaps = chapters(part.scenes)
    style = HtmlFormatter(style="github-dark").get_style_defs(".code pre")
    parts = []
    for i, s in enumerate(part.scenes):
        cur = max(k for k, (start, _) in enumerate(chaps) if start <= i)
        bar = "".join(f'<i class="{"cur" if k == cur else "done" if k < cur else ""}"></i>' for k in range(len(chaps)))
        speakers = "".join(
            f'<div class="speaker st {st["who"]}" data-s="{k}">{"Senior engineer" if st["who"] == "senior" else "Junior engineer"}</div>'
            for k, st in enumerate(s["steps"]) if st.get("who"))
        parts.append(
            f'<section class="scene" data-i="{i}"><div class="kicker">{s["kicker"]}</div><h1>{s["title"]}</h1>{speakers}'
            f'<div class="content">{s["body"]}</div>'
            f'<div class="bottom"><span><b>Sufyan Ahmad</b> · DevOps Engineer</span><div class="bar">{bar}</div>'
            f'<span class="chap">{chaps[cur][1]}</span></div></section>')
    page = part.out / "page.html"
    html_out = redact(
        f'<!doctype html><html lang="en"><head><meta charset="utf-8"><title>{part.info["title"]}</title>'
        '<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=JetBrains+Mono:wght@500;600;700&display=swap" rel="stylesheet">'
        f"<style>{CSS}{PRODUCTION_CSS}{style}.code pre{{background:transparent}}</style></head><body>{SVG_DEFS}{''.join(parts)}<script>{JS}</script></body></html>")
    problems = check(re.sub(r"<[^>]+>", " ", html_out))
    if problems:
        raise SystemExit(f"redaction check failed for the page: {problems}")
    page.write_text(html_out, encoding="utf-8", newline="\n")
    return page


# ------------------------------------------------------------------------------------------------ frames
def shoot(part: Part, jobs: list[dict], profile: str) -> None:
    jf = part.out / "jobs.json"
    jf.write_text(json.dumps(jobs), encoding="utf-8")
    subprocess.run(["node", str(HERE / "shot.mjs"), str(jf), str(HERE / "out" / profile)], check=True)


def frames(part: Part) -> None:
    page = write_page(part)
    part.frames.mkdir(exist_ok=True)
    for old in part.frames.glob("*.png"):
        old.unlink()
    url = page.as_uri()
    jobs = [{"url": f"{url}?sc={i}&st={k}", "out": str(part.frames / f"{frame_name(i, k)}.png")}
            for i, s in enumerate(part.scenes) for k in range(len(s["steps"]))]
    jobs += [{"url": f"{url}?sc={i}&st={k}&p={p}", "out": str(part.frames / f"{frame_name(i, k)}_a{j}.png")}
             for i, s in enumerate(part.scenes) for k in range(len(s["steps"])) for j, p in enumerate(ANIM)]
    thumb = (HERE / "thumbnail.html").as_uri()
    title = part.info["title"].split(" · ", 1)[-1]
    jobs.append({"url": f"{thumb}?n={part.number:02d}&t={title}&s={part.info['subtitle']}",
                 "out": str(part.yt / "thumbnail.png"), "w": 1280, "h": 720})
    shoot(part, jobs, "browser-profile")


# ------------------------------------------------------------------------------------------------ audio
def silence(path: Path, seconds: float) -> None:
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(b"\0\0" * round(seconds * RATE))


def audio(part: Part) -> None:
    part.audio.mkdir(exist_ok=True)
    for old in part.audio.glob("*.wav"):
        old.unlink()
    items = []
    for i, s in enumerate(part.scenes):
        for k, st in enumerate(s["steps"]):
            out = part.audio / f"{frame_name(i, k)}.wav"
            if st["say"]:
                items.append({"text": spoken(st), "out": str(out), "voice": st["voice"]})
            else:                                               # a silent step: hold the picture
                silence(out, st.get("hold") or 2.0)
    (part.out / "tts.json").write_text(json.dumps(items, ensure_ascii=False), encoding="utf-8")
    subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(HERE / "tts.ps1"),
                    str(part.out / "tts.json"), str(RATE), SPEED], check=True)


def wav_seconds(path: Path) -> float:
    with wave.open(str(path)) as w:
        return w.getnframes() / w.getframerate()


def frames_for(seconds: float) -> int:
    return max(1, round(seconds * FPS))


def timeline(part: Part) -> list[dict]:
    plan = []
    for i, s in enumerate(part.scenes):
        steps = []
        for k, st in enumerate(s["steps"]):
            speech = wav_seconds(part.audio / f"{frame_name(i, k)}.wav")
            if st["say"]:
                n = frames_for(speech + GAP + (LEAD if k == 0 else 0) + (TAIL if k == len(s["steps"]) - 1 else 0))
            else:
                n, speech = frames_for(speech), 0.0
            steps.append({"k": k, "frames": n, "speech": speech, "say": st["say"], "sfx": st.get("sfx"),
                          "who": st.get("who")})
        plan.append({"i": i, "steps": steps, "chapter": s["chapter"], "title": s["title"]})
    return plan


def build_audio(part: Part, plan: list[dict]) -> Path:
    out = part.out / "narration.wav"
    with wave.open(str(out), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        for sc in plan:
            for st in sc["steps"]:
                total = round(st["frames"] / FPS * RATE)
                lead = round(LEAD * RATE) if st["k"] == 0 and st["say"] else 0
                with wave.open(str(part.audio / f"{frame_name(sc['i'], st['k'])}.wav")) as r:
                    assert r.getframerate() == RATE and r.getsampwidth() == 2 and r.getnchannels() == 1
                    data = r.readframes(r.getnframes())
                speech = len(data) // 2
                w.writeframes(b"\0\0" * lead + data + b"\0\0" * max(0, total - lead - speech))
    return out


# ------------------------------------------------------------------------------------------------ video
def stamp(t: float, srt: bool = False) -> str:
    h, rem = divmod(t, 3600)
    m, s = divmod(rem, 60)
    if srt:
        return f"{int(h):02d}:{int(m):02d}:{int(s):02d},{int(round((s - int(s)) * 1000)) % 1000:03d}"
    return f"{int(h)}:{int(m):02d}:{int(s):02d}" if h else f"{int(m)}:{int(s):02d}"


def caption_parts(text: str) -> list[str]:
    parts = re.split(r"(?<=[.?!:])\s+", text.strip())
    out: list[str] = []
    for p in parts:
        while len(p) > 110 and ", " in p[40:]:
            cut = p.index(", ", 40) + 1
            out.append(p[:cut])
            p = p[cut:].strip()
        out.append(p)
    return [p for p in out if p]


def captions_and_chapters(part: Part, plan: list[dict]) -> None:
    cues, chaps, t = [], [], 0.0
    for sc in plan:
        if sc["chapter"]:
            chaps.append(f"{stamp(t)} {sc['chapter']}")
        for st in sc["steps"]:
            start = t + (LEAD if st["k"] == 0 else 0)
            parts = caption_parts(st["say"])
            total_chars = sum(len(p) for p in parts) or 1
            for p in parts:
                d = st["speech"] * len(p) / total_chars
                cues.append((start, start + d, redact(p)))
                start += d
            t += st["frames"] / FPS
    srt = "\n".join(f"{n}\n{stamp(a, True)} --> {stamp(b, True)}\n{text}\n" for n, (a, b, text) in enumerate(cues, 1))
    info = part.info
    description = (
        f"{info['title']} ({info['subtitle']}): part {part.number} of the Kubernetes Practical Course, Kubernetes from "
        f"zero to practical.\n\nA senior DevOps engineer and a junior colleague go through every lesson: the "
        f"concept with its diagram, the real commands with their real outputs, a mistake made on purpose, how to read "
        f"the error, the fix, and what to remember. Every command in the course is tested in CI on a fresh Minikube cluster.\n\n"
        f"Chapters\n" + "\n".join(chaps) + f"\n\nThe course (free, every lesson with its lab): {REPO_URL}\n"
        f"Follow along: open the lesson, type the commands in the course folder, then do the lesson's exercise and "
        f"challenge, and the lab of the level.\n\n#kubernetes #k8s #devops\n")
    for name, text in (("captions", srt), ("chapters", "\n".join(chaps)), ("description", description)):
        if check(text):
            raise SystemExit(f"redaction check failed for {name}: {check(text)}")
    part.yt.mkdir(parents=True, exist_ok=True)
    (part.yt / "captions.srt").write_text(srt, encoding="utf-8", newline="\n")
    (part.yt / "chapters.txt").write_text("\n".join(chaps) + "\n", encoding="utf-8", newline="\n")
    (part.yt / "description.md").write_text(description, encoding="utf-8", newline="\n")
    (part.yt / "title.txt").write_text(f"{info['title']} | Kubernetes Practical Course\n", encoding="utf-8", newline="\n")
    print(f"part {part.number:02d}: duration {stamp(t)} · {len(cues)} captions · {len(chaps)} chapters")


def video(part: Part) -> None:
    plan = timeline(part)
    build_audio(part, plan)
    clips = part.out / "clips"
    clips.mkdir(exist_ok=True)
    script = ["set -e", "cd /work"]
    joined = []
    for sc in plan:
        lst = clips / f"scene{sc['i']:03d}.txt"
        lines = ["ffconcat version 1.0"]
        for st in sc["steps"]:
            name = frame_name(sc['i'], st['k'])
            for j in range(len(ANIM)):
                lines += [f"file '../frames/{name}_a{j}.png'", f"duration {1 / FPS:.6f}"]
            lines += [f"file '../frames/{name}.png'", f"duration {(st['frames'] - len(ANIM)) / FPS:.6f}"]
        lines.append(f"file '../frames/{frame_name(sc['i'], sc['steps'][-1]['k'])}.png'")
        lst.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
        total = sum(st["frames"] for st in sc["steps"]) / FPS
        vf = f"fps={FPS},format=yuv420p,fade=t=in:st=0:d={FADE},fade=t=out:st={total - FADE:.3f}:d={FADE}"
        script.append(f"ffmpeg -y -loglevel error -f concat -safe 0 -i clips/{lst.name} -vf '{vf}' -frames:v {sum(st['frames'] for st in sc['steps'])} "
                      f"-c:v libx264 -preset slow -crf 18 -tune stillimage -r {FPS} clips/scene{sc['i']:03d}.mp4")
        joined.append(f"file 'scene{sc['i']:03d}.mp4'")
    (clips / "all.txt").write_text("\n".join(joined) + "\n", encoding="utf-8", newline="\n")
    script.append("ffmpeg -y -loglevel error -f concat -safe 0 -i clips/all.txt -i narration.wav -map 0:v -map 1:a "
                  "-c:v copy -c:a aac -b:a 160k -ar 48000 -ac 2 -shortest -movflags +faststart video.mp4")
    (part.out / "encode.sh").write_text("\n".join(script) + "\n", encoding="utf-8", newline="\n")
    subprocess.run(["docker", "run", "--rm", "-v", f"{part.out}:/work", "--entrypoint", "bash", FFMPEG_IMAGE,
                    "/work/encode.sh"], check=True)
    captions_and_chapters(part, plan)


# ------------------------------------------------------------------------------------------------ post-production
def post(part: Part) -> None:
    import audio_assets
    plan = timeline(part)
    events, t = [], 0.0
    for n, sc in enumerate(plan):
        if n > 0:
            events.append((t, "chapter" if sc["chapter"] else "scene"))
        for st in sc["steps"]:
            if st["sfx"]:
                events.append((t + (LEAD if st["k"] == 0 and st["say"] else 0), st["sfx"]))
            t += st["frames"] / FPS
    total = t
    mix = part.out / "mix"
    mix.mkdir(exist_ok=True)
    subprocess.run(["docker", "run", "--rm", "-v", f"{part.out}:/work", "--entrypoint", "ffmpeg", FFMPEG_IMAGE, "-y",
                    "-loglevel", "error", "-i", "/work/narration.wav", "-af",
                    "highpass=f=80,equalizer=f=3200:t=q:w=1.2:g=2.5,equalizer=f=250:t=q:w=1:g=-1.5,"
                    "acompressor=threshold=-26dB:ratio=3:attack=5:release=160:makeup=4dB,"
                    "loudnorm=I=-17:TP=-2:LRA=9,aresample=48000", "-ac", "1", "/work/mix/voice.wav"], check=True)
    audio_assets.render_mix(mix / "voice.wav", mix / "mix.wav", total, events, seed=part.number)

    def ff(*args, capture=False):
        r = subprocess.run(["docker", "run", "--rm", "-v", f"{part.out}:/work", "-w", "/work", "--entrypoint", "ffmpeg",
                            FFMPEG_IMAGE, "-hide_banner", "-y", *args], check=True, capture_output=capture, text=True)
        return r.stderr if capture else ""
    measured = json.loads(re.search(r"\{[^{}]*\}", ff("-nostats", "-i", "mix/mix.wav", "-af",
                          "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-", capture=True)).group(0))
    ff("-loglevel", "error", "-i", "mix/mix.wav", "-af",
       "loudnorm=I=-14:TP=-1.5:LRA=11:linear=true:"
       f"measured_I={measured['input_i']}:measured_TP={measured['input_tp']}:measured_LRA={measured['input_lra']}:"
       f"measured_thresh={measured['input_thresh']}:offset={measured['target_offset']},aresample=48000", "mix/final.wav")
    ff("-loglevel", "error", "-i", "video.mp4", "-i", "mix/final.wav", "-map", "0:v", "-map", "1:a", "-c:v", "copy",
       "-c:a", "aac", "-b:a", "320k", "-ar", "48000", "-ac", "2", "-shortest", "-movflags", "+faststart",
       f"{part.name}-full.mp4")
    ff("-loglevel", "error", "-i", "video.mp4", "-map", "0:v", "-c:v", "copy", "-an", "-movflags", "+faststart",
       f"{part.name}-silent.mp4")
    (part.yt / "audio-events.json").write_text(json.dumps({"name": part.name, "title": part.info["title"],
                                                            "total": total, "events": events}), encoding="utf-8")
    print(f"part {part.number:02d}: {len(events)} sound effects, {stamp(total)} -> {part.name}-full.mp4 and -silent.mp4")


SOUNDS = {
    "intro": ("Intro sting (soft impact + bell arpeggio)", "title card"),
    "pop": ("Pop", "second build step of the title card"),
    "scene": ("Scene whoosh (quiet)", "cuts between scenes"),
    "chapter": ("Chapter whoosh", "cuts that start a new lesson"),
    "error": ("Error tone (two soft falling tones)", "the junior's mistake breaks something on screen"),
    "success": ("Success chime (two rising bell notes)", "a fix is verified"),
    "outro": ("Outro chord", "end card"),
}


def licenses() -> None:
    """AUDIO-LICENSES.md: every audio asset of every full video, its license, and when it plays."""
    mmss = lambda t: f"{int(t // 60)}:{int(t % 60):02d}"  # noqa: E731
    own = ("Sufyan Ahmad (this repository)", "MIT (repository license)", "[LICENSE](../LICENSE)", "none required")
    sections = []
    for f in sorted((HERE / "youtube").glob("part*/audio-events.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        total, events = d["total"], d["events"]
        rows = [("Background music bed (pads, bass, plucked arpeggio, soft drums)", *own[:1],
                 "generated by `audio_assets.music()` (synthesised in code, no samples)", *own[1:],
                 f"0:00 – {mmss(total)} (whole video, ducked under the voice)", "background music"),
                ("Narration: senior engineer voice", "text: Sufyan Ahmad; voice engine: Microsoft",
                 'Windows speech synthesis (`System.Speech`, "Microsoft David Desktop"), `tts.ps1`',
                 "Windows license terms; the narration text is original",
                 "[Microsoft Software License Terms](https://www.microsoft.com/en-us/useterms)", "none",
                 f"0:00 – {mmss(total)} (senior lines)", "voiceover"),
                ("Narration: junior engineer voice", "text: Sufyan Ahmad; voice engine: Microsoft",
                 'Windows speech synthesis (`System.Speech`, "Microsoft Zira Desktop"), `tts.ps1`',
                 "Windows license terms; the narration text is original",
                 "[Microsoft Software License Terms](https://www.microsoft.com/en-us/useterms)", "none",
                 f"0:00 – {mmss(total)} (junior lines)", "voiceover")]
        for kind, (asset, usage) in SOUNDS.items():
            times = [mmss(t) for t, k in events if k == kind]
            if times:
                shown = ", ".join(times) if len(times) <= 30 else ", ".join(times[:30]) + f", … ({len(times)} in total)"
                rows.append((asset, own[0], f'generated by `audio_assets.sfx("{kind}")`', *own[1:], shown, usage))
        table = "\n".join("| " + " | ".join(r) + " |" for r in rows)
        sections.append(f"## {d['title']} · `{d['name']}-full.mp4` ({mmss(total)})\n\n"
                        "| Asset | Creator | Source | License | License URL | Attribution | Timestamp | Usage |\n"
                        "|---|---|---|---|---|---|---|---|\n" + table + "\n")
    text = ("# Audio licenses\n\nEvery audio asset in the full versions of the video series, where it comes from, its "
            "license, and when it plays. The silent versions (`*-silent.mp4`) have no audio track at all.\n\n"
            "**No third-party music or sound-effect files are used.** The music and every sound effect are original: "
            "synthesised by [`audio_assets.py`](audio_assets.py) from sine waves, filtered noise and envelopes "
            "(numpy/scipy). Nothing is sampled, downloaded or derived from a recording. This file is written by "
            "`build.py licenses` from the actual timelines of the videos.\n\n"
            "Note on the narration: it is produced with the speech engines that ship with Windows. Review Microsoft's "
            "license terms for your Windows edition before commercial distribution; replacing the narration with "
            "recorded voices removes the question entirely and needs no change to the visuals.\n\n"
            + "\n".join(sections))
    (HERE / "AUDIO-LICENSES.md").write_text(text, encoding="utf-8", newline="\n")
    print(f"wrote AUDIO-LICENSES.md ({len(sections)} videos)")


def run(number: int, what: str = "all") -> None:
    part = Part(number)
    if what in ("page", "all"):
        print("page:", write_page(part))
    if what in ("frames", "all"):
        frames(part)
    if what in ("audio", "all"):
        audio(part)
    if what in ("video", "all"):
        video(part)
    if what in ("post", "all"):
        post(part)
    if what == "all":                                   # keep the two finished videos, free the disk
        import shutil
        for name in ("frames", "clips", "audio", "mix"):
            shutil.rmtree(part.out / name, ignore_errors=True)
        for name in ("narration.wav", "video.mp4", "jobs.json"):
            (part.out / name).unlink(missing_ok=True)


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else "all"
    if arg == "licenses":
        licenses()
    elif arg == "all":
        for p in series.module_parts():
            run(p["part"])
        licenses()
    else:
        run(int(arg), sys.argv[2] if len(sys.argv) > 2 else "all")
