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


def newcombe_paired(a: int, b: int, c: int, d: int, z: float = Z95) -> dict:
    """Difference p1 - p2 for paired binary outcomes, with Newcombe's (1998) method-10 95% interval.
    a = success under both, b = success under X only, c = success under Y only, d = neither.
    p1 = (a+b)/n is X's rate, p2 = (a+c)/n is Y's rate."""
    n = a + b + c + d
    if n == 0:
        return {"diff": None, "ci95": [None, None], "n": 0, "discordant": [b, c]}
    p1, p2 = (a + b) / n, (a + c) / n
    l1, u1 = wilson(a + b, n, z)
    l2, u2 = wilson(a + c, n, z)
    denom = math.sqrt((a + b) * (c + d) * (a + c) * (b + d))
    if denom == 0:
        phi = 0.0
    else:
        num = a * d - b * c
        num = max(num - n / 2, 0) if num > 0 else num  # continuity correction as in Newcombe (1998)
        phi = num / denom
    delta = math.sqrt(max((p1 - l1) ** 2 - 2 * phi * (p1 - l1) * (u2 - p2) + (u2 - p2) ** 2, 0))
    eps = math.sqrt(max((u1 - p1) ** 2 - 2 * phi * (u1 - p1) * (p2 - l2) + (p2 - l2) ** 2, 0))
    diff = p1 - p2
    return {"diff": round(diff, 4), "ci95": [round(max(-1.0, diff - delta), 4), round(min(1.0, diff + eps), 4)],
            "n": n, "discordant": [b, c]}
