#!/usr/bin/env python3
"""Render the profile's typing header (typing.svg).

Typewriter effect with per-character speed, a long hold on the finished line and
a quick wipe before the next line starts. Self-hosted so the timing is exact.

Usage:
    ./tools/gen_typing.py [-o typing.svg] [--offset MS]

`--offset MS` shifts every animation back by MS milliseconds, which is handy to
render a still of a given moment while checking the timing.
"""

import argparse
import sys

WIDTH = 820
HEIGHT = 48
FONT_SIZE = 18
BASELINE = 31
FILL = "#c0398f"
CHAR_MS = 87          # matches the previous service-based cadence
HOLD_MS = 2000        # extra dwell so the whole line can be read
ERASE_MS = 400
ERASE_STEPS = 8
ADVANCE = round(FONT_SIZE * 0.6, 2)   # monospace advance at this size

LINES = [
    "Floorplan \u2192 Placement \u2192 CTS/CCopt \u2192 Route \u2192 postRoute \u2192 ECO \u2192 Signoff",
    "writing down what actually cost me days",
    "building small tools in public",
]


def line_windows():
    """Return [(start_ms, chars, width_px), ...] plus total cycle length."""
    windows, cursor = [], 0
    for text in LINES:
        chars = len(text)
        line_type = chars * CHAR_MS
        windows.append((cursor, chars, line_type))
        cursor += line_type + HOLD_MS + ERASE_MS
    return windows, cursor


def schedule(index, cycle):
    """keyTimes/values for one line's clip width over the whole cycle."""
    windows, _ = line_windows()
    start, chars, line_type = windows[index]
    points = []  # (time_ms, width_px)

    points.append((0, 0))
    if start > 0:
        points.append((start, 0))
    for k in range(1, chars + 1):
        points.append((start + k * CHAR_MS, round(k * ADVANCE, 2)))
    full = round(chars * ADVANCE, 2)
    points.append((start + line_type + HOLD_MS, full))
    for j in range(1, ERASE_STEPS + 1):
        step_ms = start + line_type + HOLD_MS + round(j * ERASE_MS / ERASE_STEPS)
        points.append((step_ms, round(full * (ERASE_STEPS - j) / ERASE_STEPS, 2)))

    points = [(t, w) for t, w in points if t < cycle]
    points.append((cycle, 0))

    # keep times strictly increasing (discrete mode needs monotonic keyTimes)
    dedup, last = [], -1
    for t, w in points:
        if t > last:
            dedup.append((t, w))
            last = t
    key_times = [round(t / cycle, 6) for t, _ in dedup]
    values = [f"{w:g}" for _, w in dedup]
    return key_times, values


def render(offset_ms=0):
    windows, cycle = line_windows()
    begin = f"-{offset_ms}ms" if offset_ms else "0s"
    clips, texts = [], []
    for index, text in enumerate(LINES):
        chars = len(text)
        start = windows[index][0]
        line_width = round(chars * ADVANCE, 2)
        x0 = round((WIDTH - line_width) / 2, 2)
        key_times, values = schedule(index, cycle)
        clips.append(
            f'    <clipPath id="c{index}" clipPathUnits="userSpaceOnUse">\n'
            f'      <rect x="{x0 - 1}" y="6" width="0" height="{HEIGHT - 12}">\n'
            f'        <animate attributeName="width" dur="{cycle}ms" begin="{begin}" '
            f'repeatCount="indefinite" calcMode="discrete"\n'
            f'          keyTimes="{";".join(f"{k:g}" for k in key_times)}"\n'
            f'          values="{";".join(values)}"/>\n'
            f'      </rect>\n'
            f'    </clipPath>'
        )
        texts.append(
            f'    <text x="{x0}" y="{BASELINE}" clip-path="url(#c{index})" '
            f'textLength="{line_width}" lengthAdjust="spacingAndGlyphs">{text}</text>'
        )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" '
        f'viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-label="{LINES[0]}">\n'
        '  <defs>\n' + "\n".join(clips) + "\n  </defs>\n"
        f'  <g font-family="\'JetBrains Mono\', ui-monospace, SFMono-Regular, Menlo, monospace" '
        f'font-size="{FONT_SIZE}" font-weight="500" fill="{FILL}">\n'
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
          f"chars={[len(l) for l in LINES]}")
    if args.offset >= cycle:
        print("warning: offset is longer than one cycle", file=sys.stderr)


if __name__ == "__main__":
    main()
