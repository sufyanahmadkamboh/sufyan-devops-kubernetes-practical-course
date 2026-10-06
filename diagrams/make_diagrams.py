"""Generate the course diagrams (SVG) in one consistent style.

    python diagrams/make_diagrams.py        writes diagrams/*.svg

Each diagram is described with a few primitives (boxes, arrows, labels), so they stay editable and match.
"""
from __future__ import annotations

from pathlib import Path

OUT = Path(__file__).resolve().parent
FONT = "Segoe UI, Helvetica, Arial, sans-serif"
MONO = "Cascadia Code, Consolas, Menlo, monospace"
INK, MUTED, LINE, BG = "#1f2937", "#5b6472", "#c9d1dc", "#ffffff"
BLUE, GREEN, ORANGE, PURPLE, RED, TEAL = "#1d63ed", "#16a34a", "#ea7a0c", "#7c3aed", "#dc2626", "#0d9488"


class Svg:
    def __init__(self, w: int, h: int, title: str):
        self.w, self.h, self.parts = w, h, []
        self.parts.append(f'<rect width="{w}" height="{h}" rx="14" fill="{BG}"/>')
        self.text(24, 38, title, size=20, weight=700)

    def text(self, x, y, s, size=14, color=INK, weight=400, anchor="start", mono=False):
        s = s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        fam = MONO if mono else FONT
        self.parts.append(f'<text x="{x}" y="{y}" font-family="{fam}" font-size="{size}" font-weight="{weight}" '
                          f'fill="{color}" text-anchor="{anchor}" xml:space="preserve">{s}</text>')

    def box(self, x, y, w, h, title, sub="", color=BLUE, fill=None, dashed=False):
        fill = fill or color + "14"
        dash = ' stroke-dasharray="7 5"' if dashed else ""
        self.parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="{fill}" stroke="{color}" '
                          f'stroke-width="2"{dash}/>')
        if title:
            self.text(x + w / 2, y + (h / 2 + 5 if not sub else h / 2 - 6), title, size=15, weight=700,
                      anchor="middle", color=color)
        if sub:
            self.text(x + w / 2, y + h / 2 + 15, sub, size=12, color=MUTED, anchor="middle")

    def frame(self, x, y, w, h, label, color=MUTED):
        """A dashed area (a host, a network, a stage) with its label at the top left."""
        self.parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12" fill="none" stroke="{color}" '
                          f'stroke-width="1.8" stroke-dasharray="7 5"/>')
        self.text(x + 12, y + 20, label, size=12, weight=700, color=color)

    def arrow(self, x1, y1, x2, y2, label="", color=MUTED, above=True, dashed=False):
        mid = f"a{len(self.parts)}"
        dash = ' stroke-dasharray="6 5"' if dashed else ""
        self.parts.append(f'<defs><marker id="{mid}" markerWidth="11" markerHeight="11" refX="9" refY="5" orient="auto" '
                          f'markerUnits="userSpaceOnUse"><path d="M0,0 L10,5 L0,10 z" fill="{color}"/></marker></defs>')
        self.parts.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="2.2"{dash} '
                          f'marker-end="url(#{mid})"/>')
        if label:
            self.text((x1 + x2) / 2, (y1 + y2) / 2 + (-9 if above else 20), label, size=13, anchor="middle",
                      color=color, mono=True)

    def save(self, name: str):
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.w} {self.h}" width="{self.w}" '
               f'height="{self.h}" role="img" aria-label="{name}">' + "".join(self.parts) + "</svg>\n")
        (OUT / f"{name}.svg").write_text(svg, encoding="utf-8", newline="\n")
        print(f"wrote diagrams/{name}.svg")




def architecture():
    d = Svg(1000, 420, "Kubernetes architecture")
    d.box(30, 160, 140, 70, "kubectl", "you", ORANGE)
    d.frame(210, 60, 330, 330, "control plane", BLUE)
    for i, (t, s) in enumerate([("API server", "the front door"), ("etcd", "the state"), ("scheduler", "where to run"),
                                ("controller manager", "reconcile")]):
        d.box(240, 95 + i * 72, 270, 58, t, s, BLUE if i == 0 else PURPLE)
    d.arrow(172, 195, 238, 124)
    d.frame(580, 60, 390, 330, "worker node (Minikube: the same node)", GREEN)
    d.box(610, 95, 160, 58, "kubelet", "runs Pods", GREEN)
    d.box(790, 95, 160, 58, "kube-proxy", "Services", GREEN)
    d.box(610, 170, 340, 50, "containerd", "", TEAL)
    for i in range(3):
        d.box(610 + i * 116, 240, 104, 60, "Pod", "", ORANGE)
    d.arrow(512, 124, 608, 124, "watch")
    d.save("architecture")


def pod():
    d = Svg(1000, 360, "A Pod: containers sharing network and storage")
    d.frame(200, 70, 600, 260, "Pod web (IP 10.244.0.12)", BLUE)
    d.box(240, 110, 230, 80, "app container", "listens on :8080", GREEN)
    d.box(530, 110, 230, 80, "sidecar container", "reads the app's logs", PURPLE)
    d.box(240, 220, 520, 45, "shared network: localhost between the containers", "", TEAL)
    d.box(240, 275, 520, 45, "shared volume (emptyDir): /var/log/app", "", ORANGE)
    d.text(500, 350, "one IP per Pod · containers start and stop together · Pods are replaceable", size=13,
           color=MUTED, anchor="middle")
    d.save("pod")


def deployment():
    d = Svg(1000, 360, "Deployment → ReplicaSet → Pods")
    d.box(60, 140, 200, 80, "Deployment web", "replicas: 3 · v2", BLUE)
    d.box(360, 80, 220, 70, "ReplicaSet web-v2", "3 Pods wanted", GREEN)
    d.box(360, 220, 220, 70, "ReplicaSet web-v1", "0 Pods (history)", MUTED, dashed=True)
    for i in range(3):
        d.box(690 + (i % 3) * 100, 85, 85, 60, "Pod", "v2", GREEN)
    d.arrow(262, 170, 358, 118)
    d.arrow(262, 190, 358, 250, dashed=True)
    d.arrow(582, 115, 688, 115)
    d.text(500, 330, "delete a Pod → the ReplicaSet creates one · new version → new ReplicaSet · rollback → old one",
           size=13, color=MUTED, anchor="middle")
    d.save("deployment")


def service():
    d = Svg(1000, 340, "Service: one stable name for changing Pods")
    d.box(40, 130, 170, 70, "client Pod", "http://backend", ORANGE)
    d.box(290, 120, 220, 90, "Service backend", "ClusterIP 10.96.0.20", BLUE)
    d.text(400, 235, "selector: app=backend", size=13, color=MUTED, anchor="middle", mono=True)
    for i, ip in enumerate(["10.244.0.5", "10.244.0.7", "10.244.0.9"]):
        d.box(620, 60 + i * 85, 220, 65, "Pod app=backend", ip, GREEN)
        d.arrow(512, 165, 618, 92 + i * 85)
    d.arrow(212, 165, 288, 165, "DNS")
    d.text(500, 320, "Pods come and go, the Service's name and IP stay · CoreDNS resolves the name",
           size=13, color=MUTED, anchor="middle")
    d.save("service")


def ingress():
    d = Svg(1000, 340, "Ingress: HTTP routing to Services")
    d.box(30, 130, 150, 70, "browser", "learning-app.local", ORANGE)
    d.box(240, 120, 230, 90, "Ingress controller", "ingress-nginx", PURPLE)
    d.box(560, 70, 180, 65, "frontend Service", "path /", BLUE)
    d.box(560, 195, 180, 65, "backend Service", "path /api", BLUE)
    d.box(800, 70, 160, 65, "frontend Pods", "", GREEN)
    d.box(800, 195, 160, 65, "backend Pods", "", GREEN)
    d.arrow(182, 165, 238, 165)
    d.arrow(472, 150, 558, 102)
    d.arrow(472, 180, 558, 228)
    d.arrow(742, 102, 798, 102)
    d.arrow(742, 228, 798, 228)
    d.save("ingress")


def configuration():
    d = Svg(1000, 330, "ConfigMaps and Secrets: configuration outside the image")
    d.box(40, 80, 230, 75, "ConfigMap", "LOG_LEVEL, nginx.conf", TEAL)
    d.box(40, 190, 230, 75, "Secret", "password (base64, not encrypted)", RED)
    d.box(600, 120, 330, 110, "Pod", "env: LOG_LEVEL=info · file: /run/secrets/db/password", GREEN)
    d.arrow(272, 118, 598, 160, "as environment variables")
    d.arrow(272, 228, 598, 195, "as files (volume)", above=False)
    d.save("configuration")


def storage():
    d = Svg(1000, 340, "Storage: PV ← PVC ← Pod")
    d.box(40, 130, 170, 75, "Pod db-0", "mounts the claim", GREEN)
    d.box(280, 130, 200, 75, "PVC data-db-0", "1Gi, ReadWriteOnce", BLUE)
    d.box(560, 130, 190, 75, "PV pvc-…", "the actual storage", PURPLE)
    d.box(800, 130, 170, 75, "StorageClass", "standard (provisioner)", TEAL)
    d.arrow(212, 168, 278, 168, "uses")
    d.arrow(482, 168, 558, 168, "bound")
    d.arrow(798, 168, 752, 168, "creates", above=False)
    d.text(500, 280, "the Pod can be deleted, rescheduled or updated: the data stays on the PV",
           size=13, color=MUTED, anchor="middle")
    d.save("storage")


def networking():
    d = Svg(1000, 360, "NetworkPolicies: only the allowed paths")
    d.box(40, 140, 170, 70, "ingress-nginx", "", PURPLE)
    d.box(290, 140, 170, 70, "frontend", "tier=frontend", GREEN)
    d.box(540, 140, 170, 70, "backend", "tier=backend", GREEN)
    d.box(790, 140, 170, 70, "database", "tier=database", GREEN)
    d.arrow(212, 175, 288, 175, "8080")
    d.arrow(462, 175, 538, 175, "8080")
    d.arrow(712, 175, 788, 175, "5432")
    d.parts.append('<path d="M375 215 Q600 330 875 215" fill="none" stroke="#dc2626" stroke-width="2.4" stroke-dasharray="7 5"/>')
    d.text(625, 300, "✕ frontend → database: denied", size=14, color=RED, anchor="middle", weight=700)
    d.text(500, 80, "default deny, then explicit allows (enforced by Calico)", size=14, color=MUTED, anchor="middle")
    d.save("network-policies")


def rbac():
    d = Svg(1000, 320, "RBAC: who may do what")
    d.box(40, 120, 190, 80, "User developer", "or a ServiceAccount", ORANGE)
    d.box(380, 120, 230, 80, "RoleBinding", "in namespace learning-app", BLUE)
    d.box(760, 120, 200, 80, "Role app-viewer", "get, list, watch pods…", PURPLE)
    d.arrow(232, 160, 378, 160, "subject")
    d.arrow(612, 160, 758, 160, "roleRef")
    d.text(500, 270, "kubectl auth can-i delete pods --as developer  →  no", size=15, mono=True, anchor="middle")
    d.save("rbac")


def rolling_update():
    d = Svg(1000, 330, "Rolling update and rollback")
    for row, (label, old, new) in enumerate([("start", 3, 0), ("surge", 3, 1), ("replace", 2, 2), ("done", 0, 3)]):
        y = 70 + row * 60
        d.text(60, y + 28, label, size=14, color=MUTED)
        for i in range(old):
            d.box(170 + i * 90, y, 80, 44, "v1", "", MUTED)
        for i in range(new):
            d.box(470 + i * 90, y, 80, 44, "v2", "", GREEN)
    d.text(800, 140, "kubectl rollout status", size=14, mono=True, color=BLUE)
    d.text(800, 200, "kubectl rollout undo", size=14, mono=True, color=RED)
    d.save("rolling-update")


def hpa():
    d = Svg(1000, 320, "Horizontal Pod Autoscaler")
    d.box(40, 120, 190, 80, "metrics-server", "CPU per Pod", TEAL)
    d.box(320, 120, 210, 80, "HPA backend", "target 60% CPU, 2–5", BLUE)
    d.box(620, 120, 180, 80, "Deployment", "replicas: 2 → 5", GREEN)
    d.arrow(232, 160, 318, 160)
    d.arrow(532, 160, 618, 160, "scale")
    d.text(500, 260, "desired = ceil(current × currentCPU / targetCPU) · scale-down waits a stabilization window",
           size=13, color=MUTED, anchor="middle")
    d.save("hpa")


def helm():
    d = Svg(1000, 320, "Helm: one chart, many environments")
    d.box(40, 110, 200, 100, "chart learning-app", "templates/ + values.yaml", BLUE)
    d.box(330, 60, 200, 60, "values-dev.yaml", "1 replica", TEAL)
    d.box(330, 200, 200, 60, "values-test.yaml", "2 replicas", TEAL)
    d.box(640, 60, 300, 60, "release learning-app-dev", "revision 1, 2, 3 …", GREEN)
    d.box(640, 200, 300, 60, "release learning-app-test", "helm upgrade / rollback", GREEN)
    d.arrow(242, 140, 328, 90)
    d.arrow(242, 180, 328, 230)
    d.arrow(532, 90, 638, 90, "helm install")
    d.arrow(532, 230, 638, 230)
    d.save("helm")


def troubleshooting():
    d = Svg(1000, 300, "The troubleshooting path")
    steps = [("What is broken?", "the symptom", RED), ("Which object?", "Ingress, Service, Pod…", ORANGE),
             ("describe", "the events", PURPLE), ("logs", "--previous", BLUE), ("config", "ConfigMap, Secret", TEAL),
             ("fix + verify", "as the user", GREEN)]
    for i, (t, s, c) in enumerate(steps):
        d.box(15 + i * 164, 110, 146, 80, t, s, c)
        if i:
            d.arrow(15 + i * 164 - 16, 150, 15 + i * 164 - 2, 150)
    d.text(500, 245, "kubectl get events · kubectl describe · kubectl logs · kubectl exec · kubectl get endpointslices",
           size=13, color=MUTED, anchor="middle", mono=True)
    d.save("troubleshooting")


if __name__ == "__main__":
    for make in [architecture, pod, deployment, service, ingress, configuration, storage, networking, rbac,
                 rolling_update, hpa, helm, troubleshooting]:
        make()
