"""Statistics: every proportion is reported with count, denominator, rate, and a 95% Wilson CI."""

from __future__ import annotations

import math

Z95 = 1.959963984540054


def wilson(k: int, n: int, z: float = Z95) -> tuple[float, float]:
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def proportion(k: int, n: int) -> dict:
    lo, hi = wilson(k, n)
    return {"count": k, "n": n, "rate": (k / n) if n else None, "ci95": [round(lo, 4), round(hi, 4)]}


def fmt(p: dict) -> str:
    if not p["n"]:
        return "0/0"
    return f"{p['count']}/{p['n']} = {100 * p['rate']:.1f}% (95% CI {100 * p['ci95'][0]:.1f}-{100 * p['ci95'][1]:.1f})"
