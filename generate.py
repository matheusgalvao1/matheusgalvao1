"""Build assets/profile.svg and README.md from data.json + photo.jpg.

    uv run --with pillow python generate.py

The photo is downsampled to a character grid; each cell becomes an ASCII glyph
(denser = brighter) filled with that pixel's real color, so the portrait reads
as a colored terminal render on a dark neofetch-style card.
"""

import hashlib
import json
from html import escape
from pathlib import Path

from PIL import Image, ImageOps

ROOT = Path(__file__).parent
data = json.loads((ROOT / "data.json").read_text())
T, P, ID = data["theme"], data["portrait"], data["identity"]

W, H = 1200, 700
PORTRAIT = dict(x=42, y=96, w=364, h=400)
KEY_X, DOTS_X, VALUE_X = 488, 700, 786
STAT_W, STAT_H, STAT_XS = 148, 56, (488, 650, 812, 974)


def clamp8(v):
    return max(0, min(255, round(v)))


def portrait_cells():
    cols = P["cols"]
    rows = max(1, round(cols * PORTRAIT["h"] / PORTRAIT["w"] * P["charAspect"]))
    img = Image.open(ROOT / "photo.jpg").convert("RGB")
    img = ImageOps.fit(img, (PORTRAIT["w"], PORTRAIT["h"]))  # center-crop to the panel aspect
    img = img.resize((cols, rows), Image.LANCZOS)

    cell_w, cell_h = PORTRAIT["w"] / cols, PORTRAIT["h"] / rows
    ramp = P["ramp"]
    out = []
    for ry in range(rows):
        for rx in range(cols):
            r, g, b = img.getpixel((rx, ry))
            l = 0.299 * r + 0.587 * g + 0.114 * b
            mx, mn = max(r, g, b), min(r, g, b)
            s = 0 if mx == 0 else (mx - mn) / mx
            # Drop a near-white studio background so the subject floats on the card.
            if l > P["bgLumaCut"] and s < P["bgSatCut"]:
                continue
            t = min(1, max(0, (l / 255 - 0.5) * P["contrast"] + 0.5))
            d = P["densityFloor"] + (1 - P["densityFloor"]) * t
            ch = ramp[round(d * (len(ramp) - 1))]
            lift = lambda c: clamp8(P["shadowLift"] + (l + (c - l) * P["satBoost"]) * P["gain"])
            fill = "#%02x%02x%02x" % (lift(r), lift(g), lift(b))
            x = PORTRAIT["x"] + rx * cell_w + cell_w / 2
            y = PORTRAIT["y"] + ry * cell_h + cell_h * 0.82
            out.append(f'<text x="{x:.1f}" y="{y:.1f}" fill="{fill}">{escape(ch)}</text>')
    return "".join(out), round(cell_h * 1.02, 1)


def build_svg():
    cells, font_size = portrait_cells()
    right, y = [], 136
    for sec in data["sections"]:
        if sec["title"]:
            right.append(f'<text x="{KEY_X}" y="{y}" class="section">{escape(sec["title"])}</text>')
            y += 42
        for row in sec["rows"]:
            cls = "accent" if row.get("accent") else "value"
            right.append(
                f'<text x="{KEY_X}" y="{y}" class="key">{escape(row["key"])}</text>'
                f'<text x="{DOTS_X}" y="{y}" class="dots">········</text>'
                f'<text x="{VALUE_X}" y="{y}" class="{cls}">{escape(row["value"])}</text>'
            )
            y += 40
        y += 8

    right.append(f'<text x="{KEY_X}" y="{y}" class="section">{escape(data["statsLabel"])}</text>')
    box_y = y + 16
    for x, s in zip(STAT_XS, data["stats"]):
        right.append(
            f'<rect x="{x}" y="{box_y}" width="{STAT_W}" height="{STAT_H}" rx="12" class="box"/>'
            f'<text x="{x + 14}" y="{box_y + 20}" class="statLabel">{escape(s["label"])}</text>'
            f'<text x="{x + 14}" y="{box_y + 44}" class="statValue">{escape(s["value"])}</text>'
        )

    px, py, pw, ph = PORTRAIT["x"], PORTRAIT["y"], PORTRAIT["w"], PORTRAIT["h"]
    nl = "\n  "
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-labelledby="title">
  <title id="title">{escape(ID["name"])} — terminal profile</title>
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="{T["bg"][0]}"/><stop offset="0.52" stop-color="{T["bg"][1]}"/><stop offset="1" stop-color="{T["bg"][2]}"/>
    </linearGradient>
    <radialGradient id="glowA" cx="0.16" cy="0.60" r="0.55">
      <stop offset="0" stop-color="{T["glowA"]}" stop-opacity="0.16"/><stop offset="1" stop-color="{T["glowA"]}" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="glowB" cx="0.93" cy="0.02" r="0.62">
      <stop offset="0" stop-color="{T["glowB"]}" stop-opacity="0.14"/><stop offset="1" stop-color="{T["glowB"]}" stop-opacity="0"/>
    </radialGradient>
    <clipPath id="portraitClip"><rect x="{px}" y="{py}" width="{pw}" height="{ph}" rx="20"/></clipPath>
    <style>
      text {{ font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace; }}
      .eyebrow   {{ font-size: 12px; fill: {T["eyebrow"]}; letter-spacing: 2px; font-weight: 700; }}
      .hero      {{ font-size: 24px; fill: {T["hero"]}; font-weight: 700; letter-spacing: -0.5px; }}
      .tagHero   {{ font-size: 19px; fill: {T["accent"]}; font-weight: 700; letter-spacing: -0.3px; }}
      .key       {{ font-size: 14px; fill: {T["key"]}; font-weight: 700; }}
      .dots      {{ font-size: 14px; fill: {T["dots"]}; letter-spacing: 1.5px; }}
      .value     {{ font-size: 14px; fill: {T["value"]}; }}
      .accent    {{ font-size: 14px; fill: {T["accent"]}; }}
      .section   {{ font-size: 12px; fill: {T["section"]}; letter-spacing: 1.6px; font-weight: 700; }}
      .box       {{ fill: {T["box"]}; stroke: {T["boxStroke"]}; stroke-opacity: 0.85; }}
      .statLabel {{ font-size: 10px; fill: {T["eyebrow"]}; letter-spacing: 1.2px; font-weight: 700; }}
      .statValue {{ font-size: 22px; fill: {T["hero"]}; font-weight: 700; }}
      .px        {{ font-size: {font_size}px; }}
      .oline     {{ font-size: 13px; fill: {T["value"]}; }}
    </style>
  </defs>

  <rect width="{W}" height="{H}" rx="24" fill="url(#bg)"/>
  <rect width="{W}" height="{H}" rx="24" fill="url(#glowA)"/>
  <rect width="{W}" height="{H}" rx="24" fill="url(#glowB)"/>
  <rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="24" fill="none" stroke="{T["boxStroke"]}" stroke-opacity="0.6"/>
  <line x1="447" y1="48" x2="447" y2="{H - 44}" stroke="{T["divider"]}" stroke-opacity="0.7"/>

  <text x="54" y="60" class="eyebrow">{escape(ID["eyebrowLeft"])}</text>
  <rect x="{px}" y="{py}" width="{pw}" height="{ph}" rx="20" fill="{T["panel"]}"/>
  <g clip-path="url(#portraitClip)" class="px">{cells}</g>
  <rect x="{px}" y="{py}" width="{pw}" height="{ph}" rx="20" fill="none" stroke="{T["boxStroke"]}" stroke-opacity="0.8"/>
  <text x="54" y="530" class="tagHero">{escape(ID["tagline1"])}</text>
  <text x="54" y="556" class="tagHero">{escape(ID["tagline2"])}</text>
  <text x="54" y="600" class="section">{escape(ID["footLabel"])}</text>
  <text x="54" y="628" class="oline">{escape(ID["foot1"])}</text>
  <text x="54" y="650" class="oline">{escape(ID["foot2"])}</text>

  <text x="{KEY_X}" y="60" class="eyebrow">{escape(ID["eyebrowRight"])}</text>
  <text x="{KEY_X}" y="92" class="hero">{escape(ID["roleHero"])}</text>
  {nl.join(right)}
</svg>
"""


def build_readme(version):
    links = " ·\n".join(f'  <a href="{l["href"]}">{l["label"]}</a>' for l in data["links"])
    user = data["githubUser"]
    selected = "\n".join(
        f'- [`{s["repo"]}`](https://github.com/{user}/{s["repo"]}) — {s["desc"]}' for s in data["selected"]
    )
    # ?v=<hash> busts GitHub's camo image cache whenever the SVG changes.
    return f"""<div align="center">
  <img src="./assets/profile.svg?v={version}" width="100%" alt="{ID["name"]} — terminal profile" />
</div>

<div align="center">
{links}
</div>

<br />

### Selected projects

{selected}

<sub>{data["footerNote"]}</sub>
"""


svg = build_svg()
(ROOT / "assets").mkdir(exist_ok=True)
(ROOT / "assets" / "profile.svg").write_text(svg)
(ROOT / "README.md").write_text(build_readme(hashlib.sha1(svg.encode()).hexdigest()[:8]))
print(f"✓ assets/profile.svg ({len(svg) // 1024} KB)\n✓ README.md")
