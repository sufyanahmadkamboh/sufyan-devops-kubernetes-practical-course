# LinkedIn package

| File | Use |
|---|---|
| `post.md` | Post text |
| `carousel/carousel.pdf` | **Recommended:** upload as a *Document* post. LinkedIn shows it as a swipeable carousel |
| `carousel/slide-01.png` … `slide-11.png` | The same slides as images (1080×1350), for a multi-image post |
| `carousel/slides.html` | Source of the slides; re-render a slide with a headless browser (`slides.html?s=N`) |
| `carousel/qr-repo.svg`, `qr-portfolio.svg` | The QR codes used on the last slide |
| `project-image.png` | Single overview image (1200×627), from `project-image.html` |
| `project-summary.md` | Short technical summary |
| `hashtags.txt` | Hashtags |

## The slides (one picture per idea)

| # | Visual | Message |
|---|---|---|
| 1 | Four numbers: lessons, broken clusters, tested blocks, labs | What it is |
| 2 | Eight real failure outputs from the troubleshooting lab | The pain |
| 3 | The ten-step path with Break / Troubleshoot / Fix highlighted | The method |
| 4 | Deployment → ReplicaSet → Pods | Concept: desired state |
| 5 | A Service selector that matches nothing | Concept: Services and labels |
| 6 | Allowed traffic paths and `kubectl auth can-i` | Concept: NetworkPolicies and RBAC |
| 7 | Four surprises found by the tests | Lessons learned |
| 8 | The capstone and its six breaks | The capstone |
| 9 | Tiles: labs, challenges, videos, PDF | What is inside |
| 10 | A test annotation on a lesson block | Every command tested |
| 11 | QR codes to the course and the portfolio, and a question | Links |

## How to post

1. Create a post, choose **Add a document**, upload `carousel/carousel.pdf` and give it the title
   "Kubernetes, from zero to practical".
2. Paste `post.md` as the text (the hashtags are at the end).
3. Reply to comments within the first hour.
