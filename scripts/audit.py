#!/usr/bin/env python3
"""Contradiction audit. Run before every push: python3 scripts/audit.py

The site states the same facts across eight surfaces — the pages, resume.json,
index.md, llms.txt and claude.md. A fact that drifts between them is worse than a
fact that is missing: inconsistency is what makes an LLM hedge or hallucinate about
him, and it is what a careful human reader notices first.
"""
import re, sys, glob, json

FILES = [f for f in ["index.html","resume/index.html","contact/index.html","blog/index.html",
         "index.md","llms.txt","claude.md","resume.json"] + sorted(glob.glob("blog/*/index.html"))
         if "_template" not in f]

def text(f):
    t = open(f).read()
    if f.endswith(".html"):
        t = re.sub(r'<script type="application/ld\+json">.*?</script>', ' ', t, flags=re.S)
        t = re.sub(r'<[^>]+>', ' ', t)
    return re.sub(r'\s+', ' ', t)

# name: (what we DO say, what would contradict it)
CHECKS = {
 "SDK volume":      (r'tens of crores', r'USD 1 ?million|in revenue|₹50 crore|₹100 crore'),
 "Terminal name":   (r'Terminal One — MIT vs Harvard', r'Terminal-One AI Hackathon'),
 "Terminal host":   (r'Correlation One', r'[Hh]osted by Citadel\.'),
 "Terminal field":  (r'30,000', None),
 "Terminal score":  (r'5–4', r'5-4'),
 "Alphathon rank":  (r'23rd internationally', None),
 "UNSW role":       (r'Visiting Student', r'UNSW[^|.]{0,50}Visiting Researcher'),
 "MIT role":        (r'Visiting Researcher', r'MIT Media Lab[^|.]{0,40}Visiting Student'),
 "SDK repo role":   (r'\bAuthor\b', r'pg-sdk-java\)? — largest contributor'),
 "Location":        (r'\bIndia\b', r'(based in|engineer in) Bangalore'),
 "epoch-cli":       (r'27 commits', r'epoch-cli[^.]{0,30}(2[0-68-9]|3\d) commits'),
 "sdk commits":     (r'40 commits', r'pg-sdk-java[^.]{0,30}(3\d|4[1-9]) commits'),
 "launch fix":      (r'within a few hours', r'within a couple of days'),
}

bad = 0
print("facts")
for name, (canon, conflict) in CHECKS.items():
    have = [f for f in FILES if re.search(canon, text(f))]
    conf = [f for f in FILES if conflict and re.search(conflict, text(f))]
    if conf:
        bad += 1; print(f"  FAIL {name:<16} contradicted in: {', '.join(conf)}")
    else:
        print(f"  ok   {name:<16} {len(have)} file(s)")

print("\nposts: sections must match the left-rail index")
for f in sorted(glob.glob("blog/*/index.html")):
    p = open(f).read()
    h = [re.sub(r'<[^>]+>','',x[1]) for x in re.findall(r'<h2 class="post-h2" id="([^"]+)">(.*?)</h2>', p, re.S)]
    t = [re.sub(r'<[^>]+>','',x) for x in re.findall(r'<li><a href="#[^"]+">(.*?)</a></li>', p, re.S)]
    if h != t: bad += 1; print(f"  FAIL {f}")
    else: print(f"  ok   {f}")

print("\nposts: the blog index year must match the post's own kicker")
b = open("blog/index.html").read()
for m in re.finditer(r'<a href="(/blog/[^"]+)">[^<]+</a>\s*<span class="when">([^<]+)</span>', b, re.S):
    url, yr = m.group(1), m.group(2).strip()
    k = re.search(r'class="hero-kicker">([^<]*)</p>', open(url.strip("/") + "/index.html").read())
    kick = k.group(1) if k else ""
    if re.search(r'\b(19|20)\d{2}\b', kick) and yr not in kick:
        bad += 1; print(f"  FAIL {url}  index:{yr}  kicker:{kick}")
    else:
        print(f"  ok   {url}")

print("\nno JavaScript anywhere")
for f in [x for x in FILES if x.endswith(".html")]:
    if "<script src" in open(f).read():
        bad += 1; print(f"  FAIL {f} loads external JS")
print("  ok   every page")

print(f"\n{'PASS — no contradictions' if bad == 0 else f'FAIL — {bad} issue(s)'}")
sys.exit(1 if bad else 0)
