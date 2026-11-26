#!/usr/bin/env python3
"""Render the profile milestones card (milestones.svg).

Pulls a few numbers from the GitHub REST API for one user and writes a small
dark card in the same visual language as banner.svg.

Usage:
    GITHUB_TOKEN=... ./tools/gen_milestones.py [-u USER] [-o milestones.svg]

The token is only read from the environment and never written to disk.
Standard library only, single file, no companion files required.
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

API = "https://api.github.com"


def api_get(path, token):
    req = urllib.request.Request(API + path)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "nolanpix-milestones")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"GET {path} -> HTTP {exc.code} {exc.reason}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"GET {path} -> {exc.reason}") from exc


def optional(path, token, default=None):
    try:
        return api_get(path, token)
    except RuntimeError as exc:
        print(f"warning: {exc} (skipped)", file=sys.stderr)
        return default


def collect(user, token):
    profile = api_get(f"/users/{user}", token)
    commits = optional(f"/search/commits?q=author:{user}&per_page=1", token, {})
    repos = optional(f"/users/{user}/repos?per_page=100&sort=pushed", token, [])
    pages = optional(
        f"/repos/{user}/{user}.github.io/contents/assets/pages.json", token, {}
    )
    note_count = 0
    if isinstance(pages, dict) and pages.get("content"):
        import base64

        try:
            listing = json.loads(base64.b64decode(pages["content"]))
            note_count = sum(1 for key in listing if str(key).startswith("/notes/"))
        except (ValueError, KeyError):
            print("warning: pages.json unreadable (skipped notes)", file=sys.stderr)
    since = (profile.get("created_at") or "")[:7]
    if since:
        months = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()
        since = f"{months[int(since[5:7]) - 1]} {since[:4]}"
    return {
        "commits": (commits or {}).get("total_count", 0),
        "repos": profile.get("public_repos", 0),
        "stars": sum(int(r.get("stargazers_count", 0)) for r in (repos or [])),
        "notes": note_count,
        "since": since or "—",
    }


TILES = [
    ("commits", "COMMITS"),
    ("repos", "PUBLIC REPOS"),
    ("notes", "NOTES"),
    ("since", "BUILDING SINCE"),
]


def render(data):
    width, height = 880, 128
    tiles = []
    for index, (key, label) in enumerate(TILES):
        x = 28 + index * 212
        value = str(data.get(key, 0))
        size = 30 if len(value) <= 4 else 20
        tiles.append(
            f'    <text x="{x}" y="82" font-size="{size}" font-weight="700" '
            f'fill="#f0f6fc">{value}</text>\n'
            f'    <text x="{x}" y="104" font-size="11" letter-spacing="1.6" '
            f'fill="#8b949e">{label}</text>'
        )
    dividers = "\n".join(
        f'    <line x1="{198 + i * 212}" y1="52" x2="{198 + i * 212}" y2="108" '
        f'stroke="#21262d" stroke-width="1"/>'
        for i in range(3)
    )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="Milestones">
  <defs>
    <linearGradient id="accent" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="#ff5a3c"/>
      <stop offset="1" stop-color="#c0398f"/>
    </linearGradient>
  </defs>
  <rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="12" fill="#0d1117" stroke="#21262d"/>
  <g font-family="-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif">
    <rect x="28" y="26" width="34" height="3" rx="1.5" fill="url(#accent)"/>
    <text x="72" y="31" font-size="11" letter-spacing="2.4" fill="#8b949e" font-family="'JetBrains Mono',ui-monospace,SFMono-Regular,Menlo,monospace">MILESTONES</text>
{chr(10).join(tiles)}
{dividers}
  </g>
</svg>
"""


def main():
    parser = argparse.ArgumentParser(description="Render the profile milestones card.")
    parser.add_argument("-u", "--user", default=os.environ.get("GITHUB_USER", "nolanpix"))
    parser.add_argument("-o", "--out", default="milestones.svg")
    args = parser.parse_args()

    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        print("warning: no GITHUB_TOKEN, running unauthenticated (rate limits)", file=sys.stderr)

    data = collect(args.user, token)
    with open(args.out, "w", encoding="utf-8") as handle:
        handle.write(render(data))
    print(f"wrote {args.out}: " + " ".join(f"{k}={v}" for k, v in data.items()))


if __name__ == "__main__":
    main()
