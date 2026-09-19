#!/usr/bin/env python3
"""Build preview.html from a finished DESIGN.md (+ extras.json + optional sample fragment).

Every visual value in the preview comes from the DESIGN.md frontmatter, so the preview can
never drift from the spec. The only hand-written part is the sample-page fragment.

Usage:
  python build_preview.py DESIGN.md --extras work/extras.json \
      [--sample work/sample.html] --out preview.html

Generated CSS API (use ONLY these in the sample fragment):
  var(--<color-key>)        every non-prefixed color key, e.g. var(--primary), var(--surface-container)
                            palette shades too: var(--primary-600). Theme toggle swaps role colors.
  var(--r-<key>)            rounded scale      var(--s-<key>)  spacing scale
  .t-<type-key>             typography styles, e.g. .t-headline-lg, .t-body-md
  .c-<component-key>        component styles, e.g. .c-button-primary, .c-card, .c-input, .c-chip
  .elev-1 … .elev-N         elevation levels rendered with the token strategy (glass/material/flat/glow)
  .backdrop                 tinted backdrop that glass surfaces need to read as glass
"""
import argparse
import html
import json
import re
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent))
from colorlib import HEX_RE, hex_to_rgb  # noqa: E402

REF_RE = re.compile(r"\{([A-Za-z0-9_.\-]+)\}")
TEMPLATE = Path(__file__).parent.parent / "assets" / "preview-template.html"


def load_frontmatter(path):
    text = Path(path).read_text(encoding="utf-8")
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.S)
    if not m:
        sys.exit("DESIGN.md has no frontmatter; run lint_design_md.py first")
    return yaml.safe_load(m.group(1))


def lookup(fm, path):
    node = fm
    for p in path.split("."):
        node = node[p]
    return node


def css_value(fm, v):
    """Turn a token reference into a CSS expression (colors stay as var() for theming)."""
    if not isinstance(v, str):
        return str(v)
    m = REF_RE.fullmatch(v)
    if not m:
        return v
    group, _, key = m.group(1).partition(".")
    if group == "colors":
        return f"var(--{key})"
    if group == "rounded":
        return f"var(--r-{key})"
    if group == "spacing":
        return f"var(--s-{key})"
    return css_value(fm, lookup(fm, m.group(1)))


def type_decls(t):
    out = []
    if t.get("fontFamily"):
        fams = ", ".join(f'"{f.strip()}"' for f in str(t["fontFamily"]).split(","))
        out.append(f"font-family: {fams}, system-ui, sans-serif")
    for k, prop in (("fontSize", "font-size"), ("fontWeight", "font-weight"),
                    ("lineHeight", "line-height"), ("letterSpacing", "letter-spacing"),
                    ("fontFeature", "font-feature-settings"), ("fontVariation", "font-variation-settings")):
        if k in t:
            out.append(f"{prop}: {t[k]}")
    return out


def rgba_var(hexv, a):
    r, g, b = hex_to_rgb(hexv)
    return f"rgba({r}, {g}, {b}, {a})"


def build_css(fm, ex):
    colors = fm.get("colors", {})
    alt = ex.get("altMode")
    alt_prefix = f"{alt}-" if alt else None
    palettes = tuple(ex.get("paletteNames", []))
    base, alt_map = {}, {}
    for k, v in colors.items():
        val = css_value(fm, v) if REF_RE.fullmatch(str(v)) else v
        if alt_prefix and k.startswith(alt_prefix):
            alt_map[k[len(alt_prefix):]] = val
        base[k] = val
    lines = [":root {", f"  color-scheme: {ex.get('defaultMode', 'light')};"]
    lines += [f"  --{k}: {v};" for k, v in base.items()]
    lines += [f"  --r-{k}: {v};" for k, v in (fm.get("rounded") or {}).items()]
    lines += [f"  --s-{k}: {v};" for k, v in (fm.get("spacing") or {}).items()]
    lines.append("}")
    if alt_map:
        lines.append(f':root[data-theme="{alt}"] {{')
        lines.append(f"  color-scheme: {alt};")
        lines += [f"  --{k}: {v};" for k, v in alt_map.items()
                  if not any(k.startswith(p + "-") and k[len(p) + 1:].isdigit() for p in palettes)]
        lines.append("}")

    for k, t in (fm.get("typography") or {}).items():
        lines.append(f".t-{k} {{ {'; '.join(type_decls(t))}; }}")

    comps = fm.get("components") or {}
    prop_map = {"backgroundColor": "background-color", "textColor": "color", "rounded": "border-radius",
                "padding": "padding", "height": "height", "width": "width"}
    for name, props in comps.items():
        sel = f".c-{name}"
        for suffix, pseudo in (("-hover", ":hover"), ("-active", ":active"), ("-focus", ":focus-visible"),
                               ("-disabled", ":disabled")):
            if name.endswith(suffix) and name[: -len(suffix)] in comps:
                sel = f".c-{name[:-len(suffix)]}{pseudo}"
        decl = []
        for p, v in (props or {}).items():
            if p == "typography":
                decl += type_decls(lookup(fm, REF_RE.fullmatch(v).group(1)))
            elif p == "size":
                decl += [f"width: {v}", f"height: {v}"]
            elif p in prop_map:
                decl.append(f"{prop_map[p]}: {css_value(fm, v)}")
        lines.append(f"{sel} {{ {'; '.join(decl)}; }}")

    el = ex.get("elevation", {})
    strategy = el.get("strategy", "material")
    bw = ex.get("shape", {}).get("borderWidth", "1px")
    levels = list(el.get("levels", {}).items())
    lines.append(f":root {{ --elev-border: {el.get('borderLight', 'transparent')}; --border-width: {bw}; }}")
    if alt_map:
        lines.append(f':root[data-theme="dark"] {{ --elev-border: {el.get("borderDark", "transparent")}; }}')
    for i, (name, lv) in enumerate(levels, 1):
        light_sh, dark_sh = lv["light"], lv["dark"]
        if strategy == "flat":
            steps = ["surface-container-low", "surface-container", "surface-container-high",
                     "surface-container-highest", "surface-container-highest"]
            decl = [f"background-color: var(--{steps[min(i - 1, 4)]})",
                    f"border: {bw} solid var(--outline-variant)", "box-shadow: none"]
        elif strategy == "glow":
            g = lv.get("glow") or {"blur": f"{4 * i + 4}px", "haloMix": 30, "borderMix": 40}
            decl = [f"box-shadow: 0 0 {g['blur']} color-mix(in srgb, var(--primary) {g['haloMix']}%, transparent)",
                    f"border: {bw} solid color-mix(in srgb, var(--primary) {g['borderMix']}%, transparent)",
                    "background-color: var(--surface)"]
        else:
            decl = [f"box-shadow: {light_sh}"]
            if strategy == "glass":
                a = round(el.get("glassSurfaceAlpha", 0.7) * 100)
                decl += [f"background-color: color-mix(in srgb, var(--surface) {a}%, transparent)",
                         f"-webkit-backdrop-filter: blur({el.get('backdropBlur', '12px')})",
                         f"backdrop-filter: blur({el.get('backdropBlur', '12px')})"]
            if el.get("requiresBorder") or strategy == "glass":
                decl.append(f"border: {bw} solid var(--elev-border)")
        lines.append(f".elev-{i} {{ {'; '.join(decl)}; }}")
        if strategy in ("material", "glass") and alt_map:
            lines.append(f':root[data-theme="dark"] .elev-{i} {{ box-shadow: {dark_sh}; }}')
    if strategy == "glass":
        lines.append(".backdrop { background:"
                     " radial-gradient(40% 50% at 15% 20%, color-mix(in srgb, var(--primary) 55%, transparent), transparent 70%),"
                     " radial-gradient(35% 45% at 85% 30%, color-mix(in srgb, var(--secondary, var(--primary)) 45%, transparent), transparent 70%),"
                     " radial-gradient(45% 50% at 60% 90%, color-mix(in srgb, var(--tertiary, var(--primary)) 50%, transparent), transparent 70%),"
                     " var(--background); }")
    else:
        lines.append(".backdrop { background: var(--background); }")
    return "\n".join(lines)


def fonts_link(ex):
    fams = [f for f in ex.get("fontFamilies", []) if f]
    if not fams:
        return ""
    weights = ";".join(str(w) for w in sorted(set(ex.get("fontWeights", [400])) | {400, 500, 600, 700}))
    q = "&".join(f"family={f.strip().replace(' ', '+')}:wght@{weights}" for f in fams)
    return ('<link rel="preconnect" href="https://fonts.googleapis.com">\n'
            '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
            f'<link rel="stylesheet" href="https://fonts.googleapis.com/css2?{q}&display=swap">')


def check_sample(sample, fm):
    palette = {v.lower() for v in (fm.get("colors") or {}).values() if isinstance(v, str) and HEX_RE.match(v)}
    bad = sorted({h for h in re.findall(r"#[0-9a-fA-F]{6}\b", sample) if h.lower() not in palette})
    if bad:
        print("WARN sample fragment hard-codes colors outside the palette:", ", ".join(bad))
    if re.search(r"\b(rgb|hsl)a?\(", sample):
        print("WARN sample fragment uses rgb()/hsl(); prefer var(--token) or color-mix with tokens")
    return sample


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("design_md")
    ap.add_argument("--extras", required=True)
    ap.add_argument("--sample", default=None)
    ap.add_argument("--out", default="preview.html")
    a = ap.parse_args()
    fm = load_frontmatter(a.design_md)
    ex = json.loads(Path(a.extras).read_text(encoding="utf-8"))
    sample = Path(a.sample).read_text(encoding="utf-8") if a.sample else \
        '<p class="t-body-md">No sample page supplied.</p>'
    check_sample(sample, fm)
    data = {"name": fm.get("name"), "description": fm.get("description", ""), "colors": fm.get("colors", {}),
            "typography": fm.get("typography", {}), "rounded": fm.get("rounded", {}),
            "spacing": fm.get("spacing", {}), "components": fm.get("components", {}), "extras": ex}
    out = TEMPLATE.read_text(encoding="utf-8")
    out = out.replace("__TITLE__", html.escape(str(fm.get("name", "Design System"))))
    out = out.replace("<!--__FONTS__-->", fonts_link(ex))
    out = out.replace("/*__CSS__*/", build_css(fm, ex))
    out = out.replace("/*__DATA__*/", "window.DS = " + json.dumps(data, ensure_ascii=False).replace("</", "<\\/") + ";")
    out = out.replace("<!--__SAMPLE__-->", sample)
    Path(a.out).write_text(out, encoding="utf-8")
    print(f"wrote {a.out} ({len(out) // 1024} KB)")


if __name__ == "__main__":
    main()
