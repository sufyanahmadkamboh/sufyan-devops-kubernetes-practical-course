#!/usr/bin/env python3
"""mdrun: run the commands in the Markdown lessons, exactly as a learner would type them.

Kubernetes course: every lesson file starts and ends with a clean cluster (see cluster_reset). Set
MDRUN_NO_CLUSTER_RESET=1 to keep everything.

Every ```bash block of a lesson runs in order. Blocks run on your computer, or inside one of the lab's Ubuntu VMs
when the block is marked with `on=<vm>` (the learner opens a shell there with `multipass shell <vm>`). A block passes
when it exits with status 0, unless it is marked as an expected failure.

Annotations are HTML comments on the line(s) right before a block (invisible on GitHub):

    <!-- test: on=k8s-cp -->             run inside the VM k8s-cp, as the user "ubuntu", in its home directory
    <!-- test: skip -->                  do not run (interactive, needs a browser, or only an illustration)
    <!-- test: github -->                talks to the GitHub practice repository: runs only with MDRUN_GITHUB=1
    <!-- test: fail -->                  the block MUST fail (we break things on purpose)
    <!-- test: contains=TEXT -->         the output must contain TEXT (several: contains=a; contains=b)
    <!-- test: absent=TEXT -->           the output must NOT contain TEXT
    <!-- test: anyof=A||B -->            the output must contain A or B (e.g. "not found" or a registry rate limit)
    <!-- test: retry=N -->               retry up to N times, 2 s apart (waiting for a cluster to settle)
    <!-- test: timeout=S -->             seconds before the block is stopped (default 600)
    <!-- test: output -->                with --update: write the real output into the ```text block below
    <!-- test: output=head:N -->         ... only the first N lines (also tail:N)

Hidden test-only steps (not shown to readers), on the computer or in a VM:

    <!-- test-run: tests/vm.sh launch k8s-cp 2 4G -->
    <!-- test-run on=k8s-worker: sudo systemctl stop kubelet -->
    <!-- test-run github: gh auth setup-git -->        (hidden, only with MDRUN_GITHUB=1)

How a VM block is executed is configurable, so the same lessons run against Multipass (a learner's laptop) or LXD
(the CI machines): MDRUN_VM_EXEC is a command template with {vm}; the block's script arrives on standard input.

    multipass (default):  multipass exec {vm} -- bash -e
    CI:                   the same, through tests/shims/multipass (LXD virtual machines)

Usage:
    python tests/mdrun.py kubeadm/README.md                       run one lesson
    python tests/mdrun.py --update --record tests/out FILES...    refresh the shown outputs, save every command+output
"""
from __future__ import annotations

import argparse
import getpass
import os
import re
import shlex
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FENCE = re.compile(r"^(\s*)```(\w*)\s*$")
ANNOT = re.compile(r"^\s*<!--\s*test:\s*(.*?)\s*-->\s*$")
HIDDEN = re.compile(r"^\s*<!--\s*test-run(?:\s+on=([\w-]+))?(\s+github)?:\s*(.*?)\s*-->\s*$")
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
WINDOWS = os.name == "nt"
VM_EXEC = os.environ.get("MDRUN_VM_EXEC", "multipass exec {vm} -- bash -e")
PROBE = re.compile(r"\s*(curl|wget|kubectl|microk8s kubectl|minikube (status|kubectl|service)|sudo crictl|"
                   r"sudo systemctl status|systemctl is-active|eksctl get|aws )\b")


@dataclass
class Block:
    line: int
    code: str
    hidden: bool = False
    opts: dict = field(default_factory=dict)
    contains: list = field(default_factory=list)
    absent: list = field(default_factory=list)
    out_start: int | None = None
    out_end: int | None = None


def parse_annotation(text: str, block: Block) -> None:
    for part in [p.strip() for p in text.split(";") if p.strip()]:
        key, _, val = part.partition("=")
        key, val = key.strip(), val.strip().strip('"')
        if key == "contains":
            block.contains.append(val)
        elif key == "anyof":                      # one of several acceptable outputs: anyof=a||b
            block.contains.append(tuple(v.strip() for v in val.split("||")))
        elif key == "absent":
            block.absent.append(val)
        else:
            block.opts[key] = val or True


def parse(path: Path) -> tuple[list[str], list[Block]]:
    lines = path.read_text(encoding="utf-8").split("\n")
    blocks: list[Block] = []
    i = 0
    while i < len(lines):
        hidden = HIDDEN.match(lines[i])
        if hidden:
            b = Block(line=i + 1, code=hidden.group(3), hidden=True)
            if hidden.group(1):
                b.opts["on"] = hidden.group(1)
            if hidden.group(2):
                b.opts["github"] = True
            blocks.append(b)
            i += 1
            continue
        m = FENCE.match(lines[i])
        if m and m.group(2) in ("bash", "sh"):
            j = i + 1
            while j < len(lines) and not FENCE.match(lines[j]):
                j += 1
            block = Block(line=i + 1, code="\n".join(lines[i + 1:j]))
            k = i - 1
            while k >= 0 and ANNOT.match(lines[k]):
                parse_annotation(ANNOT.match(lines[k]).group(1), block)
                k -= 1
            n = j + 1
            while n < len(lines) and not lines[n].strip():
                n += 1
            if n < len(lines) and FENCE.match(lines[n]) and FENCE.match(lines[n]).group(2) == "text":
                e = n + 1
                while e < len(lines) and not FENCE.match(lines[e]):
                    e += 1
                block.out_start, block.out_end = n, e
            blocks.append(block)
            i = j + 1
            continue
        elif m:
            j = i + 1
            while j < len(lines) and not FENCE.match(lines[j]):
                j += 1
            i = j + 1
            continue
        i += 1
    return lines, blocks


def sanitize(text: str) -> str:
    # Docker 29 warns when a table goes to a pipe instead of a terminal; a learner's terminal never shows it
    text = ANSI.sub("", text.replace("\r\n", "\n"))
    text = text.replace("WARNING: This output is designed for human readability. "
                        "For machine-readable output, please use --format.\n", "")
    text = "\n".join(line.split("\r")[-1] for line in text.split("\n"))
    kube = os.environ.get("KUBECONFIG", "")
    if len(kube) > 3:
        short = kube.replace(str(Path.home()), "~")
        for form in {kube, kube.replace("\\", "\\\\"), short, short.replace("\\", "\\\\")}:
            text = text.replace(form, "~/.kube/config")
    # the sandbox home first: on Windows it lives inside the course folder (tests/out/home.XXXX)
    lab_home = os.environ.get("MDRUN_HOME", "")
    if len(lab_home) > 3:
        for form in {lab_home, lab_home.replace("\\", "/"), "/" + lab_home[0].lower() + lab_home[2:].replace("\\", "/")}:
            text = text.replace(form, "~")
    posix_home = os.environ.get("MDRUN_HOME_POSIX", "").removeprefix("posix:")
    if len(posix_home) > 3:
        text = text.replace(posix_home, "~")
    mk = os.environ.get("MINIKUBE_HOME", "")
    if len(mk) > 3:
        for form in {mk, mk.replace("\\", "/"), mk.replace("/", "\\")}:
            text = text.replace(form, "~/.minikube")
    root = str(ROOT)
    for form in {root, root.replace("\\", "/"), "/" + root[0].lower() + root[2:].replace("\\", "/")}:
        text = text.replace(form, "~/kubernetes-practical-course")
    home = str(Path.home())
    for form in {home, home.replace("\\", "/"), "/" + home[0].lower() + home[2:].replace("\\", "/")}:
        if len(home) > 3:
            text = text.replace(form, "~")
    user = getpass.getuser()
    if len(user) > 2 and user not in ("runner", "ubuntu", "root"):
        text = re.sub(rf"(?<![\w.-]){re.escape(user)}(?![\w.-])", "learner", text)
    # kubeadm bootstrap tokens are credentials: mask real ones (lab 04's documented fake token stays visible)
    text = re.sub(r"\b(?!abcdef\.0123456789abcdef)[a-z0-9]{6}\.[a-z0-9]{16}\b", "<bootstrap-token>", text)
    # never publish who ran it: IAM user names (in ARNs, eksctl context names) and e-mail addresses
    text = re.sub(r"(:user/)[\w+=,.@-]+", r"\1<iam-user>", text)
    # (addresses at the reserved example domains of RFC 2606, used as sample data, stay readable, and so does the
    # SSH user of Git hosts: git@github.com is not an e-mail address)
    text = re.sub(r"(?<![\w.+-])(?!git@)[\w.+-]+@(?!(?:[\w-]+\.)*example\.(?:com|org|net)\b)[\w-]+(?:\.[\w-]+)*\.[a-z]{2,}(?=@|\b)", "<iam-user>", text)
    # never publish an AWS account ID (12 digits), also inside ARNs and ECR host names
    # (not inside hex IDs such as container or image IDs, which are letters and digits)
    text = re.sub(r"(?<![0-9a-f])(?<!job/)(?<!runs/)\d{12}(?![0-9a-f])", "<account-id>", text)  # GitHub job IDs stay
    return text.rstrip("\n")


def shell() -> list[str]:
    if WINDOWS:
        for candidate in (r"C:\Program Files\Git\bin\bash.exe", r"C:\Program Files\Git\usr\bin\bash.exe"):
            if Path(candidate).exists():
                return [candidate]
    return ["bash"]


# MSYS_NO_PATHCONV: Git Bash would rewrite container paths (kubectl exec POD -- cat /etc/hosts) into Windows paths
ENV = {**os.environ, "NO_COLOR": "1", "TERM": "dumb", "DOCKER_CLI_HINTS": "false", "MSYS_NO_PATHCONV": "1",
       "COMPOSE_PROGRESS": "plain", "COMPOSE_ANSI": "never", "BUILDKIT_PROGRESS": "plain", "AWS_PAGER": ""}


def execute(code: str, cwd: str, timeout: int, vm: str | None) -> tuple[str, int, str]:
    """Run code with bash -e, on this computer (in cwd) or inside a VM. Returns (output, status, new cwd)."""
    if vm:
        cmd = shlex.split(VM_EXEC.format(vm=vm))
        try:
            p = subprocess.run(cmd, input=code + "\n", stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                               encoding="utf-8", errors="replace", timeout=timeout, env=ENV)
            return p.stdout, p.returncode, cwd
        except subprocess.TimeoutExpired as e:
            partial = e.stdout.decode(errors="replace") if isinstance(e.stdout, bytes) else (e.stdout or "")
            return partial + f"\n[timed out after {timeout}s]", 124, cwd
    state = tempfile.NamedTemporaryFile(delete=False, suffix=".cwd")
    state.close()
    # the trap records the final directory even when the block fails (a "fail" block keeps the learner's cd)
    save = shlex.quote(f"pwd > {shlex.quote(Path(state.name).as_posix())}")
    script = "\n".join(["set -e", f"trap {save} EXIT", f"cd {shlex.quote(cwd)}", code, ""])
    try:
        p = subprocess.run(shell() + ["-c", script], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                           encoding="utf-8", errors="replace", timeout=timeout, env=ENV)
        out, rc = p.stdout, p.returncode
    except subprocess.TimeoutExpired as e:
        partial = e.stdout.decode(errors="replace") if isinstance(e.stdout, bytes) else (e.stdout or "")
        out, rc = partial + f"\n[timed out after {timeout}s]", 124
    new_cwd = Path(state.name).read_text(encoding="utf-8").strip() or cwd
    os.unlink(state.name)
    if WINDOWS and re.match(r"^/[a-z]/", new_cwd):
        new_cwd = new_cwd[1].upper() + ":" + new_cwd[2:]
    return out, rc, new_cwd


def run_block(block: Block, cwd: str, record_to: Path | None) -> tuple[bool, str, str, str]:
    timeout = int(block.opts.get("timeout", 600))
    tries = int(block.opts.get("retry", 1))
    expect_fail = "fail" in block.opts
    vm = block.opts.get("on")
    if vm and "+" in vm:                     # the same block on several VMs, one after the other
        outs, ok_all, whys = [], True, []
        for one in vm.split("+"):
            sub = Block(line=block.line, code=block.code, hidden=block.hidden, opts={**block.opts, "on": one},
                        contains=block.contains, absent=block.absent)
            ok, why, out, cwd = run_block(sub, cwd, None)
            outs.append(f"[{one}]\n{out}")
            ok_all &= ok
            if not ok:
                whys.append(f"{one}: {why}")
        out = "\n".join(outs)
        if record_to is not None and not block.hidden:
            record_to.write_text(f"# on {vm}\n{block.code}\n---\n{out}\n# exit {0 if ok_all else 1}\n",
                                 encoding="utf-8", newline="\n")
        return ok_all, "; ".join(whys), out, cwd
    code, setup_out = block.code, ""
    if tries > 1:
        # retry only the checking part (from the first probe line on); never re-run what came before it
        lines = block.code.split("\n")
        at = next((i for i, line in enumerate(lines) if PROBE.match(line)), 0)
        setup = "\n".join(lines[:at])
        if at > 0 and not re.search(r"^\s*[A-Za-z_]\w*=", setup, re.M):
            setup_out, rc, cwd = execute(setup, cwd, timeout, vm)
            if rc != 0 and not expect_fail:
                out = sanitize(setup_out)
                return False, f"exit status {rc} (before the retried part)\n{out[-3000:]}", out, cwd
            code = "\n".join(lines[at:])
    problems: list[str] = []
    out, rc, new_cwd = "", 0, cwd
    for attempt in range(tries):
        raw, rc, new_cwd = execute(code, cwd, timeout, vm)
        out = sanitize(setup_out + raw)
        problems = []
        if expect_fail and rc == 0:
            problems.append("expected this block to fail, but it succeeded")
        if not expect_fail and rc != 0:
            problems.append(f"exit status {rc}")
        problems += [f"output does not contain {t!r}" for t in block.contains
                     if (not any(x in out for x in t) if isinstance(t, tuple) else t not in out)]
        problems += [f"output contains {t!r}" for t in block.absent if t in out]
        if not problems or attempt == tries - 1:
            break
        time.sleep(2)
    if record_to is not None and not block.hidden:
        where = f"# on {vm}\n" if vm else ""
        record_to.write_text(f"{where}{block.code}\n---\n{out}\n# exit {rc}\n", encoding="utf-8", newline="\n")
    why = "; ".join(problems) + ("\n" + out[-3000:] if problems else "")
    return not problems, why, out, new_cwd


def shown_output(out: str, spec) -> list[str]:
    lines = out.split("\n") if out else []
    if isinstance(spec, str) and ":" in spec:
        kind, n = spec.split(":", 1)
        n = int(n)
        if kind == "head" and len(lines) > n:
            lines = lines[:n] + ["..."]
        elif kind == "tail" and len(lines) > n:
            lines = ["..."] + lines[-n:]
    return lines


SYSTEM_NAMESPACES = {"default", "kube-system", "kube-public", "kube-node-lease", "ingress-nginx"}
DEFAULT_KEEP = {("service", "kubernetes"), ("configmap", "kube-root-ca.crt"), ("serviceaccount", "default")}
NAMESPACED = ["deployment", "replicaset", "statefulset", "daemonset", "cronjob", "job", "pod", "service", "configmap",
              "secret", "persistentvolumeclaim", "ingress", "networkpolicy", "role", "rolebinding", "serviceaccount",
              "horizontalpodautoscaler", "poddisruptionbudget", "resourcequota", "limitrange"]
CLUSTER_LABELLED = ["clusterrole", "clusterrolebinding", "storageclass", "persistentvolume", "priorityclass"]


def kubectl(*args: str, timeout: int = 180) -> str:
    try:
        return subprocess.run(["kubectl", *args], capture_output=True, text=True, timeout=timeout, env=ENV).stdout
    except (OSError, subprocess.TimeoutExpired):
        return ""


def cluster_reset() -> None:
    """Every lesson starts and ends with a clean cluster: the course's namespaces deleted, the default namespace back to
    its built-in objects, cluster-wide objects labelled course=k8s-lab removed. Lessons clean up after themselves; this
    is the safety net. MDRUN_NO_CLUSTER_RESET=1 skips it."""
    if os.environ.get("MDRUN_NO_CLUSTER_RESET") == "1" or not kubectl("version", "--request-timeout=5s"):
        return
    for name in kubectl("get", "namespaces", "-o", "name").split():
        ns = name.removeprefix("namespace/")
        if ns not in SYSTEM_NAMESPACES:
            kubectl("delete", "namespace", ns, "--wait=true", "--timeout=120s")
    for kind in NAMESPACED:
        for obj in kubectl("get", kind, "-n", "default", "-o", "name").split():
            if (kind, obj.split("/", 1)[1]) not in DEFAULT_KEEP:
                kubectl("delete", obj, "-n", "default", "--wait=false", "--grace-period=1")
    kubectl("delete", ",".join(CLUSTER_LABELLED), "-l", "course=k8s-lab", "--wait=false")
    for name in kubectl("get", "nodes", "-o", "name").split():          # taints and labels a lesson may have left
        kubectl("label", name, "lab-", "disktype-", "--overwrite")
        kubectl("taint", name, "lab-", "dedicated-")


def run_file(path: Path, update: bool, record: Path | None) -> tuple[int, int]:
    lines, blocks = parse(path)
    cluster_reset()
    # run.sh points MDRUN_CWD at a copy of the course without .git: a lesson whose lab setup failed then runs its
    # commands in that copy, never in the course repository itself
    cwd = os.environ.get("MDRUN_CWD", "").removeprefix("posix:") or str(ROOT).replace("\\", "/")
    rel = path.resolve().relative_to(ROOT).as_posix()
    print(f"\n=== {rel}", flush=True)
    passed = failed = 0
    edits = []
    rec_dir = None
    if record:
        rec_dir = record / rel.replace("/", "__").removesuffix(".md")
        rec_dir.mkdir(parents=True, exist_ok=True)
    shown = 0
    gh_ok = os.environ.get("MDRUN_GITHUB") == "1"
    for b in blocks:
        only_gh = os.environ.get("MDRUN_ONLY") == "github" and "github" not in b.opts
        if "skip" in b.opts or ("github" in b.opts and not gh_ok) or only_gh:
            print(f"  skip  line {b.line}{' (github)' if 'github' in b.opts else ''}", flush=True)
            continue
        rec_file = None
        if rec_dir and not b.hidden:
            shown += 1
            rec_file = rec_dir / f"{shown:02d}-line{b.line}.txt"
        started = time.time()
        ok, why, out, cwd = run_block(b, cwd, rec_file)
        label = ("hidden" if b.hidden else "block") + (f" on {b.opts['on']}" if b.opts.get("on") else "")
        took = f"{time.time() - started:5.1f}s"
        if ok:
            passed += 1
            print(f"  ok    line {b.line} {label} ({took})", flush=True)
        else:
            failed += 1
            print(f"  FAIL  line {b.line} {label} ({took}): {why}", flush=True)
        if update and "output" in b.opts and b.out_start is not None and ok:
            edits.append((b.out_start + 1, b.out_end, shown_output(out, b.opts["output"])))
    if update and edits:
        for start, end, new in sorted(edits, reverse=True):
            lines[start:end] = new
        path.write_text("\n".join(lines), encoding="utf-8", newline="\n")
        print(f"  updated {len(edits)} output block(s)", flush=True)
    cluster_reset()
    return passed, failed


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="+")
    ap.add_argument("--update", action="store_true", help="refresh ```text output blocks marked with output")
    ap.add_argument("--record", type=Path, help="save every command and its output into this folder")
    ap.add_argument("--stop-on-failure", action="store_true", help="stop at the first failing file")
    args = ap.parse_args()
    total_ok = total_fail = 0
    for f in args.files:
        ok, bad = run_file(Path(f), args.update, args.record)
        total_ok += ok
        total_fail += bad
        if bad and args.stop_on_failure:
            break
    print(f"\n{total_ok} passed, {total_fail} failed")
    return 1 if total_fail else 0


if __name__ == "__main__":
    sys.exit(main())
