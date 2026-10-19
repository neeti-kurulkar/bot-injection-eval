"""Builds the README charts (docs/img/*.svg) from the published results in docs/results/. No extra libraries.

Run: uv run python scripts/make_readme_charts.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "dashboard"))
import results_data as D  # noqa: E402

OUT = REPO / "docs" / "img"
INK, MUTED, RULE, BG = "#1B2A41", "#5A6578", "#DED9CE", "#FBF9F4"
A_COL, B_COL = "#D9622B", "#2A5C99"
FONT = "font-family='IBM Plex Sans, Segoe UI, Helvetica, Arial, sans-serif'"


def svg(width: int, height: int, body: list[str], title: str) -> str:
    return (f"<svg xmlns='http://www.w3.org/2000/svg' width='{width}' height='{height}' viewBox='0 0 {width} {height}' "
            f"role='img' aria-label='{title}' {FONT}>\n<title>{title}</title>\n"
            f"<rect width='100%' height='100%' rx='12' fill='{BG}' stroke='{RULE}'/>\n" + "\n".join(body) + "\n</svg>\n")


def text(x, y, s, size=14, fill=INK, weight=400, anchor="start") -> str:
    s = s.replace("&", "&amp;").replace("<", "&lt;")
    return f"<text x='{x}' y='{y}' font-size='{size}' fill='{fill}' font-weight='{weight}' text-anchor='{anchor}'>{s}</text>"


def heldout_by_model() -> str:
    rows = D.model_any_rows("heldout")
    w, left, scale = 760, 150, 16.0  # px per percentage point
    body = [text(24, 36, "Held-out attacks that worked, by model", 18, weight=600),
            text(24, 58, "228 attacks per bar · lower is better · thin line = 95% range", 13, MUTED),
            f"<rect x='{w - 250}' y='24' width='14' height='14' fill='{A_COL}'/>", text(w - 230, 36, "A · no defense", 13),
            f"<rect x='{w - 130}' y='24' width='14' height='14' fill='{B_COL}'/>", text(w - 110, 36, "B · defense on", 13)]
    y = 90
    for model in ("Qwen3 4B", "Sarvam 105B", "GPT-5.6 Luna"):
        body.append(text(24, y + 26, model, 15, weight=600))
        for cond, col in (("A · no defense", A_COL), ("B · defense on", B_COL)):
            r = next(x for x in rows if x["model"] == model and x["condition"] == cond)
            bw = r["rate"] * scale
            body += [f"<rect x='{left}' y='{y}' width='{bw:.1f}' height='18' rx='3' fill='{col}'/>",
                     f"<line x1='{left + r['ci_low'] * scale:.1f}' x2='{left + r['ci_high'] * scale:.1f}' "
                     f"y1='{y + 9}' y2='{y + 9}' stroke='{INK}' stroke-opacity='.45' stroke-width='1.5'/>",
                     text(left + max(bw, r["ci_high"] * scale) + 8, y + 14, f"{r['rate']:.1f}%", 13, weight=600)]
            y += 24
        y += 22
    grid = []
    for t in (0, 10, 20, 30):
        x = left + t * scale
        grid += [f"<line x1='{x}' x2='{x}' y1='82' y2='{y - 14}' stroke='{RULE}'/>", text(x, y, f"{t}%", 12, MUTED, anchor="middle")]
    body = body[:6] + grid + body[6:]  # gridlines behind the bars
    return svg(w, y + 18, body, "Held-out attack success by model, with and without the defense")


def goals_table() -> str:
    w, h = 760, 300
    goals = [g for g in D.GOALS]
    models = ("qwen3-4b", "sarvam-105b", "gpt-5.6-luna")
    body = [text(24, 36, "What got through on held-out attacks: A → B", 18, weight=600),
            text(24, 58, "attacks that worked, out of 48 (G3: 36) · green = zero with the defense on", 13, MUTED)]
    col_x = [24, 330, 470, 610]
    for x, label in zip(col_x[1:], ("Qwen3 4B", "Sarvam 105B", "GPT-5.6 Luna")):
        body.append(text(x, 92, label, 14, weight=600))
    y = 104
    for i, g in enumerate(goals):
        if i % 2 == 0:
            body.append(f"<rect x='16' y='{y}' width='{w - 32}' height='34' rx='4' fill='#EFEBE3'/>")
        body.append(text(col_x[0] + 8, y + 22, D.GOAL_LABEL[g], 14))
        for x, slug in zip(col_x[1:], models):
            a = D.model_summary(slug, "A-heldout")["per_goal"][g]["strict_all"]["count"]
            b = D.model_summary(slug, "B-heldout")["per_goal"][g]["strict_all"]["count"]
            fill = "#2E7D4F" if b == 0 else (A_COL if b >= a else INK)
            body.append(f"<text x='{x}' y='{y + 22}' font-size='15' fill='{INK}'>{a} → "
                        f"<tspan fill='{fill}' font-weight='700'>{b}</tspan></text>")
        y += 34
    body.append(text(24, y + 26, "Planted wrong policy (G1) is the one failure the defense doesn't stop: it fell on the hosted models, not on Qwen.", 13, MUTED))
    return svg(w, y + 44, body, "Held-out attacks that worked per goal and model, A to B")


def language_heatmap() -> str:
    rows = D.language_rows("ANY", "B", ("dev", "heldout"))
    w = 760
    langs = [D.LANG_LABEL[x] for x in D.LANGS]
    body = [text(24, 36, "With the defense on, by language", 18, weight=600),
            text(24, 58, "% of attacks that worked · dev + held-out pooled, 152 per cell · darker = worse", 13, MUTED)]
    x0, cw, y0, ch = 170, 140, 96, 44
    for j, lang in enumerate(langs):
        body.append(text(x0 + j * cw + cw / 2, y0 - 10, lang, 13, weight=600, anchor="middle"))
    hi = max(r["rate"] for r in rows)
    for i, model in enumerate(("Qwen3 4B", "Sarvam 105B", "GPT-5.6 Luna")):
        y = y0 + i * ch
        body.append(text(24, y + 27, model, 14, weight=600))
        for j, lang in enumerate(langs):
            r = next(x for x in rows if x["model"] == model and x["language"] == lang)
            t = r["rate"] / hi
            fill = f"rgb({int(251 - t * (251 - 217))},{int(243 - t * (243 - 98))},{int(235 - t * (235 - 43))})"
            body += [f"<rect x='{x0 + j * cw + 3}' y='{y + 3}' width='{cw - 6}' height='{ch - 6}' rx='5' fill='{fill}'/>",
                     text(x0 + j * cw + cw / 2, y + 28, f"{r['rate']:.1f}%", 15, "#FBF9F4" if t > .6 else INK, 600, "middle")]
    y = y0 + 3 * ch
    body.append(text(24, y + 26, "Devanagari Hindi is the worst language for every model, mostly because planted policy written in it is repeated more.", 13, MUTED))
    return svg(w, y + 44, body, "Attack success by language and model with the defense on")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, fn in (("heldout-by-model", heldout_by_model), ("goals-heldout", goals_table), ("language-b", language_heatmap)):
        (OUT / f"{name}.svg").write_text(fn(), encoding="utf-8", newline="\n")
        print(f"wrote docs/img/{name}.svg")


if __name__ == "__main__":
    main()
