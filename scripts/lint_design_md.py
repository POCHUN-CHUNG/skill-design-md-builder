#!/usr/bin/env python3
"""Validate a DESIGN.md against the Stitch DESIGN.md spec plus this skill's house rules.

Usage: python lint_design_md.py DESIGN.md
Exit code 1 if any ERROR, else 0. WARN lines are advisory.

Checks
  structure : frontmatter fenced by '---' lines; name + colors.primary present;
              known H2 sections in spec order; no duplicate H2; no H1 besides optional title
  tokens    : color values are #hex; typography dimensions valid; rounded/spacing values valid
  references: every {path} resolves; outside `components` it must hit a primitive value
  prose     : every #hex mentioned in the body exists in frontmatter colors
              (keeps prose and tokens from drifting apart); no leftover __FILL_IN__ / TODO
  contrast  : X / on-X pairs and component background/text pairs >= 4.5:1
"""
import re
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent))
from colorlib import HEX_RE, contrast, norm_hex  # noqa: E402

SECTION_ORDER = [
    ("overview", {"overview", "brand & style", "brand and style"}),
    ("colors", {"colors"}),
    ("typography", {"typography"}),
    ("layout", {"layout", "layout & spacing", "layout and spacing"}),
    ("elevation", {"elevation & depth", "elevation", "elevation and depth"}),
    ("shapes", {"shapes"}),
    ("components", {"components"}),
    ("dos", {"do's and don'ts", "dos and don'ts", "do's & don'ts"}),
]
DIM_RE = re.compile(r"^-?\d+(\.\d+)?(px|em|rem)$")
REF_RE = re.compile(r"\{([A-Za-z0-9_.\-]+)\}")
KNOWN_COMPONENT_PROPS = {"backgroundColor", "textColor", "typography", "rounded", "padding",
                         "size", "height", "width"}

errors, warns = [], []


def err(m):
    errors.append(m)


def warn(m):
    warns.append(m)


def split(text):
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        err("File must start with a line containing only '---'")
        return None, text
    try:
        end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    except StopIteration:
        err("Frontmatter is not closed by a line containing only '---'")
        return None, text
    return "\n".join(lines[1:end]), "\n".join(lines[end + 1:])


def lookup(fm, path):
    node = fm
    for p in path.split("."):
        if not isinstance(node, dict) or p not in node:
            return None, False
        node = node[p]
    return node, True


def check_tokens(fm):
    if not fm.get("name"):
        err("frontmatter `name` is required")
    colors = fm.get("colors") or {}
    if "primary" not in colors:
        err("colors.primary is required")
    for k, v in colors.items():
        if isinstance(v, str) and REF_RE.fullmatch(v):
            continue
        if not isinstance(v, str) or not HEX_RE.match(v):
            err(f"colors.{k} = {v!r} is not a #hex color")
    for k, t in (fm.get("typography") or {}).items():
        if not isinstance(t, dict):
            err(f"typography.{k} must be an object")
            continue
        for prop in ("fontSize", "letterSpacing"):
            if prop in t and not DIM_RE.match(str(t[prop])):
                err(f"typography.{k}.{prop} = {t[prop]!r} is not a dimension (px/em/rem)")
        lh = t.get("lineHeight")
        if lh is not None and not (isinstance(lh, (int, float)) or DIM_RE.match(str(lh))):
            err(f"typography.{k}.lineHeight = {lh!r} must be unitless number or dimension")
        if "fontWeight" in t and not str(t["fontWeight"]).isdigit():
            err(f"typography.{k}.fontWeight = {t['fontWeight']!r} must be numeric")
        if not t.get("fontFamily"):
            warn(f"typography.{k} has no fontFamily")
    for grp in ("rounded", "spacing"):
        for k, v in (fm.get(grp) or {}).items():
            if not (isinstance(v, (int, float)) or DIM_RE.match(str(v))):
                (err if grp == "rounded" else warn)(f"{grp}.{k} = {v!r} is not a valid dimension")
    for cname, props in (fm.get("components") or {}).items():
        for p in (props or {}):
            if p not in KNOWN_COMPONENT_PROPS:
                warn(f"components.{cname}.{p}: property not in common set (consumers accept with warning)")


def check_refs(fm):
    def rec(node, path):
        if isinstance(node, dict):
            for k, v in node.items():
                rec(v, path + [str(k)])
        elif isinstance(node, str):
            for ref in REF_RE.findall(node):
                val, ok = lookup(fm, ref)
                where = ".".join(path)
                if not ok:
                    err(f"Unresolved reference {{{ref}}} at {where}")
                elif isinstance(val, dict) and path[0] != "components":
                    err(f"{{{ref}}} at {where} points to a group; only `components` may reference composites")
    rec(fm, [])


def resolve_color(fm, v):
    for _ in range(5):
        m = REF_RE.fullmatch(v or "")
        if not m:
            break
        v, _ = lookup(fm, m.group(1))
    return v if isinstance(v, str) and HEX_RE.match(v) else None


def check_contrast(fm):
    colors = fm.get("colors") or {}
    for k in colors:
        if k.startswith("on-") or "-on-" in k:
            continue
        prefix, base = ("", k)
        for p in ("dark-", "light-"):
            if k.startswith(p):
                prefix, base = p, k[len(p):]
        on = f"{prefix}on-{base}"
        if on in colors:
            a, b = resolve_color(fm, colors[k]), resolve_color(fm, colors[on])
            if a and b and contrast(a, b) < 4.5:
                err(f"Contrast {k}/{on} = {contrast(a, b)}:1 < 4.5:1")
    for cname, props in (fm.get("components") or {}).items():
        bg, fg = props.get("backgroundColor"), props.get("textColor")
        if bg and fg:
            a, b = resolve_color(fm, bg), resolve_color(fm, fg)
            if a and b and contrast(a, b) < 4.5:
                err(f"components.{cname}: text/background contrast {contrast(a, b)}:1 < 4.5:1")


def check_body(fm, body):
    heads = [(m.start(), m.group(1).strip()) for m in re.finditer(r"^##\s+(.+?)\s*$", body, re.M)]
    h1 = re.findall(r"^#\s+.+$", body, re.M)
    if len(h1) > 1:
        err(f"Only one optional H1 title allowed, found {len(h1)}")
    seen, last_idx = set(), -1
    for _, title in heads:
        t = title.lower()
        if t in seen:
            err(f"Duplicate section '## {title}' (consumers reject the whole file)")
        seen.add(t)
        idx = next((i for i, (_, names) in enumerate(SECTION_ORDER) if t in names), None)
        if idx is None:
            continue  # extension section: allowed anywhere
        if idx < last_idx:
            err(f"Section '## {title}' is out of order (spec order: Overview, Colors, Typography, "
                "Layout, Elevation & Depth, Shapes, Components, Do's and Don'ts)")
        last_idx = max(last_idx, idx)
    present = {next((key for key, names in SECTION_ORDER if t.lower() in names), None) for _, t in heads}
    for key, names in SECTION_ORDER:
        if key not in present:
            warn(f"Standard section missing: {sorted(names)[0]}")

    palette = {norm_hex(v) for v in (fm.get("colors") or {}).values()
               if isinstance(v, str) and HEX_RE.match(v)}
    for h in sorted(set(re.findall(r"#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b", body))):
        try:
            if norm_hex(h) not in palette:
                err(f"Prose mentions {h} which is not a frontmatter color — prose and tokens disagree")
        except ValueError:
            pass
    blob = body + yaml.safe_dump(fm)
    for marker in ("__FILL_IN__", "TODO", "TBD"):
        if marker in blob:
            err(f"Leftover placeholder '{marker}'")
    if "lorem ipsum" in blob.lower():
        err("Leftover placeholder 'lorem ipsum'")


def main():
    path = Path(sys.argv[1])
    text = path.read_text(encoding="utf-8")
    fm_text, body = split(text)
    if fm_text is not None:
        try:
            fm = yaml.safe_load(fm_text) or {}
        except yaml.YAMLError as e:
            err(f"YAML parse error: {e}")
            fm = {}
        check_tokens(fm)
        check_refs(fm)
        check_contrast(fm)
        check_body(fm, body)
    for w in warns:
        print("WARN ", w)
    for e in errors:
        print("ERROR", e)
    print(f"\n{path.name}: {len(errors)} error(s), {len(warns)} warning(s)")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
