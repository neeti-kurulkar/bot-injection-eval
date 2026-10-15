"""Money formatting. Amounts are integer paise everywhere in the code."""


def indian_group(n: int) -> str:
    """12345678 -> '1,23,45,678' (Indian digit grouping)."""
    s = str(n)
    if len(s) <= 3:
        return s
    head, tail = s[:-3], s[-3:]
    parts = []
    while len(head) > 2:
        parts.insert(0, head[-2:])
        head = head[:-2]
    if head:
        parts.insert(0, head)
    return ",".join(parts + [tail])


def format_inr(paise: int) -> str:
    """1234050 -> '₹12,340.50'."""
    sign = "-" if paise < 0 else ""
    rupees, p = divmod(abs(paise), 100)
    return f"{sign}₹{indian_group(rupees)}.{p:02d}"
