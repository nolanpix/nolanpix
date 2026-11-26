#!/usr/bin/env python3
"""Render the profile's typing header (typing.svg).

Same technique as readme-typing-svg: a <textPath> over a straight path whose
length grows one character at a time, so characters past the path end are simply
not drawn. Clip-path geometry animation and per-character opacity were ignored by
some engines (all lines showed at once / nothing showed), this variant is the one
proven to animate inside an <img>.

Usage:
    ./tools/gen_typing.py [-o typing.svg] [--offset MS]

`--offset MS` shifts every animation back by MS milliseconds (render a still).
"""

import argparse
import sys
from xml.sax.saxutils import escape

WIDTH = 820
HEIGHT = 48
FONT_SIZE = 18
PATH_Y = 32
FILL = "#c0398f"
CHAR_MS = 87          # same cadence as the previous service-based header
HOLD_MS = 2000        # dwell on the finished line so it can be read
ERASE_MS = 400
ADVANCE = round(FONT_SIZE * 0.6, 2)   # monospace advance at this size

LINES = [
    "Floorplan \u2192 Placement \u2192 CTS/CCopt \u2192 Route \u2192 postRoute \u2192 ECO \u2192 Signoff",
    "writing down what actually cost me days",
    "building small tools in public",
]


def plan():
    rows, cursor = [], 0
    for text in LINES:
        typing = len(text) * CHAR_MS
        rows.append((cursor, len(text), typing))
        cursor += typing + HOLD_MS + ERASE_MS
    return rows, cursor


def schedule(index, rows, cycle):
    """keyTimes and path 'd' values for one line's reveal, over the whole cycle."""
    start, chars, typing = rows[index]
    full = chars * ADVANCE
    x0 = round((WIDTH - full) / 2, 2)
    points = [(0, 0.0)]
    if start:
        points.append((start, 0.0))
    for k in range(1, chars + 1):
        points.append((start + k * CHAR_MS, k * ADVANCE))
    points.append((start + typing + HOLD_MS, full))
    steps = 8
    for j in range(1, steps + 1):
        points.append((start + typing + HOLD_MS + j * ERASE_MS / steps,
                       round(full * (steps - j) / steps, 2)))
    points = [(t, w) for t, w in points if t < cycle]
    points.append((cycle, 0.0))

    key_times, values, last = [], [], -1
    for t, w in points:
        if t <= last:
            continue
        key_times.append(round(t / cycle, 6))
        values.append(f"m{x0},{PATH_Y} h{w:g}")
        last = t
    return key_times, values


def render(offset_ms=0):
    rows, cycle = plan()
    begin = f"-{offset_ms}ms" if offset_ms else "0s"
    paths, texts = [], []
    for index, line in enumerate(LINES):
        key_times, values = schedule(index, rows, cycle)
        paths.append(
            f'    <path id="p{index}" d="m0,{PATH_Y} h0">\n'
            f'      <animate attributeName="d" dur="{cycle}ms" begin="{begin}" '
            f'repeatCount="indefinite" calcMode="discrete"\n'
            f'        keyTimes="{";".join(f"{k:g}" for k in key_times)}"\n'
            f'        values="{";".join(values)}"/>\n'
            f'    </path>'
        )
        texts.append(
            f'    <text y="{PATH_Y}">'
            f'<textPath href="#p{index}" startOffset="0">{escape(line)}</textPath></text>'
        )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" '
        f'viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-label="{escape(LINES[0])}">\n'
        '  <defs>\n' + "\n".join(paths) + "\n  </defs>\n"
        f'  <g font-family="\'JetBrains Mono\', ui-monospace, SFMono-Regular, Menlo, monospace" '
        f'font-size="{FONT_SIZE}" font-weight="500" fill="{FILL}" xml:space="preserve">\n'
        + "\n".join(texts) + "\n  </g>\n</svg>\n"
    ), cycle


def main():
    parser = argparse.ArgumentParser(description="Render the typing header SVG.")
    parser.add_argument("-o", "--out", default="typing.svg")
    parser.add_argument("--offset", type=int, default=0,
                        help="shift animations back by this many milliseconds")
    args = parser.parse_args()

    svg, cycle = render(args.offset)
    with open(args.out, "w", encoding="utf-8") as handle:
        handle.write(svg)
    print(f"wrote {args.out}: {len(svg)} bytes, cycle {cycle}ms, "
          f"chars={[len(line) for line in LINES]}, offset={args.offset}ms")
    if args.offset >= cycle:
        print("warning: offset exceeds one cycle", file=sys.stderr)


if __name__ == "__main__":
    main()
