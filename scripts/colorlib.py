"""Shared color helpers: hex parsing, WCAG 2.x relative luminance and contrast."""
import re

HEX_RE = re.compile(r"^#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})$")


def norm_hex(value: str) -> str:
    """Return lowercase 6-digit hex (#rrggbb). Raise ValueError if invalid."""
    if not isinstance(value, str) or not HEX_RE.match(value.strip()):
        raise ValueError(f"invalid hex color: {value!r}")
    h = value.strip().lower()[1:]
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return "#" + h


def hex_to_rgb(value: str):
    h = norm_hex(value)[1:]
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def luminance(value: str) -> float:
    def channel(c):
        c = c / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (channel(c) for c in hex_to_rgb(value))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a: str, b: str) -> float:
    la, lb = luminance(a), luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return round((hi + 0.05) / (lo + 0.05), 2)


def best_on_color(bg: str, candidates) -> str:
    """Pick the candidate with the highest contrast against bg."""
    return max(candidates, key=lambda c: contrast(bg, c))


def rgba(value: str, alpha: float) -> str:
    r, g, b = hex_to_rgb(value)
    return f"rgba({r}, {g}, {b}, {alpha})"


def hsl(value: str):
    import colorsys
    r, g, b = (c / 255 for c in hex_to_rgb(value))
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    return h * 360, s, l


def looks_similar(a: str, b: str, hue_tol=25, light_tol=0.1) -> bool:
    """True when two tinted colors are close enough in hue and lightness to be confused."""
    ha, sa, la = hsl(a)
    hb, sb, lb = hsl(b)
    if sa < 0.08 or sb < 0.08:
        return False
    dh = min(abs(ha - hb), 360 - abs(ha - hb))
    return dh <= hue_tol and abs(la - lb) <= light_tol
