#!/usr/bin/env python3
"""
Refresh the live stats on the site.

Two sources:
  1. Claude Code token usage  — via `ccusage`, reading ~/.claude transcripts.
  2. Apple Health (steps, calories) — via a JSON file written by the
     "Health Auto Export" iPhone app. Point HEALTH_JSON at it (env var
     AO_HEALTH_JSON overrides).

Writes data/stats.json, then rewrites the block between the STATS markers in
index.html. The numbers are baked into the HTML on purpose: the site ships zero
JavaScript, so anything rendered client-side would be invisible to the AI
crawlers that never execute JS.

Usage:  python3 scripts/update-stats.py [--push]
"""

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "index.html"
DATA = ROOT / "data" / "stats.json"

# Health Auto Export writes here by default when you pick iCloud Drive.
HEALTH_JSON = Path(
    os.environ.get(
        "AO_HEALTH_JSON",
        Path.home()
        / "Library/Mobile Documents/com~apple~CloudDocs/HealthAutoExport/HealthAutoExport.json",
    )
)


def human(n):
    """2_710_536_475 -> '2.71B'"""
    n = float(n)
    for limit, suffix in ((1e9, "B"), (1e6, "M"), (1e3, "K")):
        if n >= limit:
            return f"{n / limit:.2f}".rstrip("0").rstrip(".") + suffix
    return f"{int(n):,}"


def tokens():
    """Total Claude Code usage across every project on this machine."""
    try:
        raw = subprocess.run(
            ["npx", "-y", "ccusage@latest", "--json"],
            capture_output=True,
            text=True,
            timeout=180,
            check=True,
        ).stdout
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as e:
        print(f"  ! ccusage failed ({e}); leaving token stats untouched", file=sys.stderr)
        return None

    d = json.loads(raw)
    t = d.get("totals", {})
    daily = d.get("daily", [])
    total = t.get("totalTokens") or sum(
        t.get(k, 0)
        for k in ("inputTokens", "outputTokens", "cacheCreationTokens", "cacheReadTokens")
    )
    return {
        "total_tokens": total,
        "output_tokens": t.get("outputTokens", 0),
        "input_tokens": t.get("inputTokens", 0),
        "cost_usd": round(t.get("totalCost", 0), 2),
        "days": len(daily),
        "first_day": daily[0]["period"] if daily else None,
        "last_day": daily[-1]["period"] if daily else None,
        # last 14 days, for the bar chart
        "recent": [
            {"date": x["period"], "tokens": x.get("totalTokens", 0)} for x in daily[-14:]
        ],
    }


def health():
    """Steps and active calories from the Health Auto Export JSON."""
    if not HEALTH_JSON.exists():
        print(f"  · no health export at {HEALTH_JSON} — skipping health", file=sys.stderr)
        return None

    d = json.loads(HEALTH_JSON.read_text())
    metrics = d.get("data", {}).get("metrics", [])
    by_name = {m.get("name"): m for m in metrics}

    def series(*names):
        for n in names:
            m = by_name.get(n)
            if m and m.get("data"):
                return m["data"]
        return []

    steps = series("step_count", "steps")
    energy = series("active_energy", "active_energy_burned")

    def latest(rows):
        return float(rows[-1].get("qty", 0)) if rows else 0

    def total(rows):
        return sum(float(r.get("qty", 0)) for r in rows)

    if not steps and not energy:
        return None

    return {
        "steps_today": int(latest(steps)),
        "steps_total": int(total(steps)),
        "calories_today": int(latest(energy)),
        "calories_total": int(total(energy)),
        "days": len(steps) or len(energy),
        "last_day": (steps or energy)[-1].get("date", "")[:10],
    }


def bars(recent):
    """A 14-day bar chart in pure CSS — no JS, no external chart library."""
    if not recent:
        return ""
    peak = max((r["tokens"] for r in recent), default=1) or 1
    out = []
    for r in recent:
        pct = max(4, round(r["tokens"] / peak * 100))
        label = f'{r["date"]}: {human(r["tokens"])} tokens'
        out.append(f'<span class="bar" style="height:{pct}%" title="{label}"></span>')
    return "\n          ".join(out)


def render(stats):
    tk, h = stats.get("tokens"), stats.get("health")
    parts = []

    if tk:
        parts.append(f"""      <div class="card">
        <h3 class="card-t">LLM coding</h3>
        <p class="stat">{human(tk['total_tokens'])}<span class="unit">tokens</span></p>
        <div class="chart" aria-hidden="true">
          {bars(tk['recent'])}
        </div>
        <dl class="mini">
          <dt>Output</dt><dd>{human(tk['output_tokens'])}</dd>
          <dt>Spend</dt><dd>${tk['cost_usd']:,.0f}</dd>
          <dt>Days</dt><dd>{tk['days']}</dd>
        </dl>
      </div>""")

    if h:
        parts.append(f"""      <div class="card">
        <h3 class="card-t">Health</h3>
        <p class="stat">{h['steps_today']:,}<span class="unit">steps today</span></p>
        <dl class="mini">
          <dt>Burnt</dt><dd>{h['calories_today']:,} kcal</dd>
          <dt>Total</dt><dd>{human(h['steps_total'])} steps</dd>
          <dt>Days</dt><dd>{h['days']}</dd>
        </dl>
      </div>""")

    updated = datetime.now(timezone.utc).strftime("%d %b %Y")
    parts.append(f'      <p class="rail-note">Updated {updated} · '
                 f'<a href="/data/stats.json">stats.json</a></p>')
    return "\n".join(parts)


def main():
    DATA.parent.mkdir(exist_ok=True)
    prev = json.loads(DATA.read_text()) if DATA.exists() else {}

    stats = {
        "tokens": tokens() or prev.get("tokens"),
        "health": health() or prev.get("health"),
        "updated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    DATA.write_text(json.dumps(stats, indent=2) + "\n")
    print(f"  wrote {DATA.relative_to(ROOT)}")

    html = INDEX.read_text()
    block = re.compile(
        r"(<!-- STATS:START -->\n).*?(\s*<!-- STATS:END -->)", re.S
    )
    if not block.search(html):
        sys.exit("! STATS markers not found in index.html")
    INDEX.write_text(block.sub(lambda m: m.group(1) + render(stats) + m.group(2), html))
    print(f"  rewrote stats block in {INDEX.relative_to(ROOT)}")

    if "--push" in sys.argv:
        subprocess.run(["git", "add", "-A"], cwd=ROOT, check=True)
        r = subprocess.run(
            ["git", "commit", "-q", "-m", "chore: refresh live stats"], cwd=ROOT
        )
        if r.returncode == 0:
            subprocess.run(["git", "push", "-q", "origin", "main"], cwd=ROOT, check=True)
            print("  pushed")
        else:
            print("  nothing to commit")


if __name__ == "__main__":
    main()
