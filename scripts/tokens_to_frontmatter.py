#!/usr/bin/env python3
"""Convert a W3C-DTCG style design-tokens.json into DESIGN.md building blocks.

Outputs (in --out-dir):
  frontmatter.yaml  YAML block (without --- fences) ready to paste into DESIGN.md
  extras.json       Values that have no frontmatter slot (elevation, borders, fonts,
                    role provenance) - consumed by build_preview.py and used for prose
  report.md         Human-readable log: fixed references, aliases, derived roles,
                    inferred values and warnings. Summarise this for the user.

Usage:
  python tokens_to_frontmatter.py design-tokens.json --out-dir work/ \
      [--name "Brand Name"] [--default-mode light|dark] [--spacing-base 4] \
      [--palette-map '{"primary-2": "secondary"}']
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from colorlib import best_on_color, contrast, looks_similar, norm_hex, rgba  # noqa: E402

REF_RE = re.compile(r"^\{([^{}]+)\}$")
SHADE_KEYS = ["50", "100", "200", "300", "400", "500", "600", "700", "800", "900", "950"]


class Log:
    def __init__(self):
        self.fixed_refs, self.aliases, self.roles = [], [], []
        self.inferred, self.warnings, self.errors = [], [], []


LOG = Log()


# --------------------------------------------------------------------------- utils
def is_token(node):
    return isinstance(node, dict) and "$value" in node


def children(node):
    return {k: v for k, v in node.items() if not k.startswith("$")} if isinstance(node, dict) else {}


def walk(node, path=(), inherited_type=None):
    """Yield (path, token_node, type) for every token in the tree."""
    if not isinstance(node, dict):
        return
    t = node.get("$type", inherited_type)
    if is_token(node):
        yield path, node, t
        return
    for k, v in children(node).items():
        yield from walk(v, path + (k,), t)


def get_path(root, parts):
    node = root
    for p in parts:
        if not isinstance(node, dict) or p not in node:
            return None
        node = node[p]
    return node


def group_types(root):
    """Map path-tuple -> $type for every group, used for fuzzy reference repair."""
    out = {}

    def rec(node, path):
        if not isinstance(node, dict):
            return
        if "$type" in node:
            out[path] = node["$type"]
        for k, v in children(node).items():
            rec(v, path + (k,))
    rec(root, ())
    return out


def resolve_ref(root, ref, context):
    """Resolve '{a.b.c}' to its raw $value. Repairs broken paths when unambiguous."""
    m = REF_RE.match(ref.strip()) if isinstance(ref, str) else None
    if not m:
        return ref
    parts = tuple(m.group(1).split("."))
    node = get_path(root, parts)
    if node is not None:
        return node["$value"] if is_token(node) else node
    # repair: candidates whose last segment matches and whose ancestor group is
    # typed/named like the first segment (e.g. {fontFamily.heading} -> typography.families.heading)
    gtypes = group_types(root)
    head, tail = parts[0].lower(), parts[-1]
    cands = []
    for p, _tok, _t in walk(root):
        if p[-1] != tail:
            continue
        anc = [p[:i] for i in range(1, len(p))]
        if any(gtypes.get(a, "").lower() == head or a[-1].lower()[:4] == head[:4] for a in anc):
            cands.append(p)
    if len(cands) == 1:
        fixed = "{" + ".".join(cands[0]) + "}"
        LOG.fixed_refs.append(f"`{ref}` in `{context}` → `{fixed}`")
        return get_path(root, cands[0])["$value"]
    LOG.errors.append(f"Unresolvable reference `{ref}` in `{context}` (candidates: {cands or 'none'})")
    return None


def dim(v):
    """DTCG dimension -> '12px' / '-0.02em'. Accepts {value, unit}, numbers, strings."""
    if isinstance(v, dict) and "value" in v:
        num = v["value"]
        num = int(num) if float(num).is_integer() else round(float(num), 4)
        return f"{num}{v.get('unit', 'px')}"
    if isinstance(v, (int, float)):
        return f"{int(v) if float(v).is_integer() else v}px"
    return str(v)


def dim_px(v):
    if isinstance(v, dict) and v.get("unit", "px") == "px":
        return float(v["value"])
    if isinstance(v, (int, float)):
        return float(v)
    m = re.match(r"^(-?[\d.]+)px$", str(v))
    return float(m.group(1)) if m else None


def mix(a, b, t):
    """Mix hex a toward hex b by fraction t (0..1)."""
    from colorlib import hex_to_rgb
    ra, rb = hex_to_rgb(a), hex_to_rgb(b)
    return "#" + "".join(f"{round(x + (y - x) * t):02x}" for x, y in zip(ra, rb))


# --------------------------------------------------------------------------- colors
def collect_colors(root, palette_map):
    cnode = root.get("color") or root.get("colors") or {}
    palettes, modes, semantic, singles = {}, {}, {}, {}
    for key, node in children(cnode).items():
        kids = children(node)
        if is_token(node):
            singles[key] = norm_hex(resolve_ref(root, node["$value"], f"color.{key}"))
        elif kids and all(k in SHADE_KEYS for k in kids):
            palettes[key] = {k: norm_hex(resolve_ref(root, v["$value"], f"color.{key}.{k}"))
                             for k, v in kids.items() if is_token(v)}
        elif key in ("light", "dark"):
            modes[key] = {k: norm_hex(resolve_ref(root, v["$value"], f"color.{key}.{k}"))
                          for k, v in kids.items() if is_token(v)}
        elif key == "semantic":
            semantic = {k: norm_hex(resolve_ref(root, v["$value"], f"color.semantic.{k}"))
                        for k, v in kids.items() if is_token(v)}
        else:
            for p, tok, _ in walk(node, (key,)):
                singles["-".join(p)] = norm_hex(resolve_ref(root, tok["$value"], "color." + ".".join(p)))

    # default renames: primary-2 -> secondary, primary-3 -> tertiary
    rename = {}
    if "secondary" not in palettes and "primary-2" in palettes:
        rename["primary-2"] = "secondary"
    if "tertiary" not in palettes and "primary-3" in palettes:
        rename["primary-3"] = "tertiary"
    rename.update(palette_map or {})
    renamed = {}
    for k, v in palettes.items():
        nk = rename.get(k, k)
        if nk != k:
            LOG.aliases.append(f"Palette `{k}` renamed to `{nk}` (semantic role naming)")
        renamed[nk] = v

    # dedupe identical palettes (keep first in document order)
    unique, seen = {}, {}
    for k, v in renamed.items():
        sig = tuple(v.get(s) for s in SHADE_KEYS)
        if sig in seen:
            LOG.aliases.append(f"Palette `{k}` is identical to `{seen[sig]}` → dropped, use `{seen[sig]}-*`")
            continue
        seen[sig] = k
        unique[k] = v

    # semantic colors: find source palette
    sem_src = {}
    for name, hexv in semantic.items():
        src = next((p for p, v in unique.items() if v.get("500") == hexv), None)
        sem_src[name] = src
        if src:
            LOG.aliases.append(f"Semantic `{name}` ({hexv}) = `{src}-500`")
    if "info" in sem_src and sem_src["info"] == "primary":
        LOG.warnings.append("`info` equals `primary-500`: informational messages will look like brand/primary actions. "
                            "Consider mapping info to the `link` palette if distinct.")
    return unique, modes, semantic, sem_src, singles


def pick_shade(pal, bg, order, need_bg=None, on_cands=None, min_on=4.5):
    """Return (shade_key, hex, on_hex) for first shade meeting contrast rules."""
    for s in order:
        if s not in pal:
            continue
        c = pal[s]
        on = best_on_color(c, on_cands) if on_cands else None
        if on_cands and contrast(c, on) < min_on:
            continue
        if need_bg and contrast(c, bg) < need_bg:
            continue
        return s, c, on
    s = order[0] if order[0] in pal else next(iter(pal))
    c = pal[s]
    return s, c, best_on_color(c, on_cands) if on_cands else None


def build_roles(mode, palettes, modes, semantic, sem_src, singles):
    m = modes.get(mode, {})
    light = mode == "light"
    bg = m.get("bg") or ("#ffffff" if light else "#0b0b0b")
    text = m.get("text") or ("#0f0f0f" if light else "#f5f5f5")
    surface = m.get("surface") or bg
    border = m.get("border")
    neutral = palettes.get("neutral", {})
    roles, src = {}, {}

    def put(name, value, source):
        roles[name] = value
        src[name] = source

    put("background", bg, f"color.{mode}.bg")
    put("on-background", text, f"color.{mode}.text")
    put("surface", surface, f"color.{mode}.surface")
    put("on-surface", text, f"color.{mode}.text")
    steps = (0.03, 0.06, 0.09, 0.12) if light else (0.04, 0.07, 0.10, 0.14)
    put("surface-container-lowest", bg if light else mix(bg, "#000000", 0.25), "derived")
    put("surface-container-low", mix(surface, text, steps[0]), f"mix(surface, text, {steps[0]})")
    put("surface-container", mix(surface, text, steps[1]), f"mix(surface, text, {steps[1]})")
    put("surface-container-high", mix(surface, text, steps[2]), f"mix(surface, text, {steps[2]})")
    put("surface-container-highest", mix(surface, text, steps[3]), f"mix(surface, text, {steps[3]})")
    if border:
        put("outline-variant", border, f"color.{mode}.border")
    if neutral:
        order = ["500", "600", "700"] if light else ["500", "400", "300"]
        s, c, _ = pick_shade(neutral, bg, order, need_bg=3.0)
        put("outline", c, f"neutral-{s} (≥3:1 vs background)")
        order = ["600", "700", "800"] if light else ["400", "300", "200"]
        s, c, _ = pick_shade(neutral, surface, order, need_bg=4.5)
        put("on-surface-variant", c, f"neutral-{s} (≥4.5:1 vs surface)")

    on_cands = ["#ffffff", text, bg] if light else [bg, "#ffffff", text]
    fill_order = ["500", "600", "700", "400", "800"] if light else ["300", "200", "400", "100"]
    for role in ("primary", "secondary", "tertiary"):
        pal = palettes.get(role)
        if not pal:
            continue
        s, c, on = pick_shade(pal, bg, fill_order, need_bg=3.0,
                              on_cands=on_cands + [pal.get("950", text), pal.get("50", bg)])
        put(role, c, f"{role}-{s}")
        put(f"on-{role}", on, f"best contrast vs {role} ({contrast(c, on)}:1)")
        i = SHADE_KEYS.index(s) + (1 if light else -1)
        if 0 <= i < len(SHADE_KEYS) and SHADE_KEYS[i] in pal:
            put(f"{role}-hover", pal[SHADE_KEYS[i]], f"{role}-{SHADE_KEYS[i]} (one step {'darker' if light else 'lighter'})")
        cont = pal.get("100" if light else "800")
        oncont = pal.get("900" if light else "100")
        if cont and oncont:
            put(f"{role}-container", cont, f"{role}-{'100' if light else '800'}")
            put(f"on-{role}-container", oncont, f"{role}-{'900' if light else '100'}")

    # semantic
    for name, hexv in semantic.items():
        pal = palettes.get(sem_src.get(name) or "", {})
        if light or not pal:
            c = hexv
            srcname = f"color.semantic.{name}"
        else:
            s, c, _ = pick_shade(pal, bg, ["300", "200", "400"], need_bg=4.5)
            srcname = f"{sem_src[name]}-{s}"
        on = best_on_color(c, ["#ffffff", text, bg, pal.get("950", "#000000")])
        put(name, c, srcname)
        put(f"on-{name}", on, f"best contrast ({contrast(c, on)}:1)")
        if pal:
            ck, ok = ("100", "900") if light else ("900", "100")
            put(f"{name}-container", pal[ck], f"{sem_src[name]}-{ck}")
            put(f"on-{name}-container", pal[ok], f"{sem_src[name]}-{ok}")

    link = palettes.get("link")
    if link:
        order = ["500", "600", "700"] if light else ["300", "200", "400"]
        s, c, _ = pick_shade(link, bg, order, need_bg=4.5)
        put("link", c, f"link-{s} (≥4.5:1 vs background)")
    return roles, src


# --------------------------------------------------------------------------- typography
def collect_typography(root):
    tnode = root.get("typography") or {}
    out, families = {}, set()
    for key, node in children(tnode).items():
        if not is_token(node) or not isinstance(node["$value"], dict):
            continue
        v = node["$value"]
        fam = resolve_ref(root, v.get("fontFamily"), f"typography.{key}.fontFamily")
        fam_list = fam if isinstance(fam, list) else [fam] if fam else []
        families.update(f for f in fam_list if f)
        entry = {"fontFamily": ", ".join(fam_list)} if fam_list else {}
        if "fontSize" in v:
            entry["fontSize"] = dim(v["fontSize"])
        if "fontWeight" in v:
            entry["fontWeight"] = int(v["fontWeight"])
        if "lineHeight" in v:
            lh = v["lineHeight"]
            entry["lineHeight"] = dim(lh) if isinstance(lh, dict) else lh
        if "letterSpacing" in v:
            entry["letterSpacing"] = dim(v["letterSpacing"])
        for extra in ("fontFeature", "fontVariation"):
            if extra in v:
                entry[extra] = v[extra]
        out[key] = entry

    # hierarchy checks
    def px(k):
        return dim_px(out[k].get("fontSize", "0px")) or 0
    for group in ("headline", "body", "label"):
        keys = [k for k in ["display", "xl", "lg", "md", "sm", "xs"]
                for k in [f"{group}-{k}"] if k in out]
        if group == "headline" and "headline-display" in out:
            keys = ["headline-display"] + [k for k in keys if k != "headline-display"]
        sizes = [px(k) for k in keys]
        if sizes != sorted(sizes, reverse=True) or len(set(sizes)) != len(sizes):
            LOG.warnings.append(f"`{group}-*` sizes not strictly decreasing: "
                                + ", ".join(f"{k}={px(k):g}px" for k in keys))
    by_size = {}
    for k in out:
        by_size.setdefault(px(k), []).append(k)
    for size, ks in by_size.items():
        cats = {k.split("-")[0] for k in ks}
        # body/label sharing a size is normal (weight separates them); headline sharing is not
        if "headline" in cats and len(cats) > 1:
            LOG.warnings.append(f"Hierarchy collision: {', '.join(ks)} all use {size:g}px — "
                                "different roles at the same size weaken visual hierarchy.")
    return out, sorted(families)


# --------------------------------------------------------------------------- shape / spacing
def collect_shape_and_spacing(root, spacing_base):
    app = root.get("appearance", {})
    comp = children(app.get("component", {}))
    shape = app.get("shape", {})
    strategy = (shape.get("cornerStrategy") or {}).get("$value", "rounded-consistent")

    comp_radius = {}
    for name, node in comp.items():
        r = node.get("radius")
        if is_token(r):
            comp_radius[name] = dim_px(r["$value"])

    # Hybrid radius system: appearance.radius (or rounded/radius/...) is an independent global
    # scale, unrelated to per-component hard-coded radii. When both exist, `rounded.*` comes
    # straight from the global scale and component radii stay literal px (no {rounded.*} ref) —
    # the two are allowed to disagree by design.
    rounded, hybrid = {}, False
    for cand in (("appearance", "radius"), ("rounded",), ("radius",), ("dimension", "radius"), ("border", "radius")):
        node = get_path(root, cand)
        if isinstance(node, dict) and any(is_token(v) for v in children(node).values()):
            for p, tok, _ in walk(node):
                rounded["-".join(p)] = dim(tok["$value"])
            if rounded:
                hybrid = cand == ("appearance", "radius") and bool(comp_radius)
                break
    if not rounded:
        distinct = sorted({v for v in comp_radius.values() if v is not None})
        names = ["sm", "md", "lg", "xl", "2xl"]
        rounded["none"] = "0px"
        if distinct and distinct[0] >= 12:
            xs = int(round(distinct[0] / 2 / 2) * 2)
            rounded["xs"] = f"{xs}px"
            LOG.inferred.append(f"`rounded.xs` = {xs}px (half of smallest component radius; for tags/tooltips)")
        for i, v in enumerate(distinct[:len(names)]):
            rounded[names[i]] = f"{v:g}px"
        rounded["full"] = "9999px"
        LOG.inferred.append("`rounded` scale built from component radii "
                            + ", ".join(f"{k}={v}" for k, v in rounded.items())
                            + f" (cornerStrategy: {strategy})")
    elif hybrid:
        LOG.aliases.append("Hybrid radius system detected: `rounded.*` = `appearance.radius.*` "
                           "(" + ", ".join(f"{k}={v}" for k, v in rounded.items()) + "). "
                           "Component radii are independent hard-coded px values by design and are "
                           "NOT mapped to this scale — do not force them into {rounded.*} references.")

    # Only build the rounded->component lookup when the two systems are meant to align.
    radius_key = {}
    if not hybrid:
        for name, v in comp_radius.items():
            k = next((rk for rk, rv in rounded.items() if dim_px(rv) == v), None)
            radius_key[name] = k

    # spacing
    spacing = {}
    for cand in (("spacing",), ("space",), ("dimension", "spacing")):
        node = get_path(root, cand)
        if isinstance(node, dict):
            for p, tok, _ in walk(node):
                spacing["-".join(p)] = dim(tok["$value"])
            if spacing:
                break
    if not spacing:
        b = spacing_base
        spacing = {"xs": f"{b}px", "sm": f"{b*2}px", "md": f"{b*4}px", "lg": f"{b*6}px",
                   "xl": f"{b*8}px", "2xl": f"{b*12}px", "3xl": f"{b*16}px",
                   "gutter": f"{b*6}px", "margin": f"{b*8}px"}
        LOG.inferred.append(f"`spacing` scale not in tokens → {b}px-base scale generated: "
                            + ", ".join(f"{k}={v}" for k, v in spacing.items())
                            + ". Adjust gutter/margin/density to the reference material.")

    comp_padding = {n: dim_px(node["padding"]["$value"]) for n, node in comp.items()
                    if is_token(node.get("padding"))}
    comp_elev = {}
    for n, node in comp.items():
        e = node.get("elevation")
        if is_token(e) and isinstance(e["$value"], str):
            comp_elev[n] = e["$value"].strip("{}").split(".")[-1]
    for n, p in comp_padding.items():
        if p is not None and p % spacing_base:
            LOG.warnings.append(f"`{n}.padding` = {p:g}px is off the {spacing_base}px grid.")
    # concentric radius: inner radius should be outer radius - padding
    if "card" in comp_radius and "subcard" in comp_radius and "card" in comp_padding:
        ideal = max(0.0, comp_radius["card"] - comp_padding["card"])
        if ideal > 0 and abs(ideal - comp_radius["subcard"]) > 2:
            LOG.warnings.append(
                f"Nested radius mismatch: card radius {comp_radius['card']:g}px − padding "
                f"{comp_padding['card']:g}px = {ideal:g}px ideal inner radius, but subcard uses "
                f"{comp_radius['subcard']:g}px. Corners will not look concentric.")
    if comp_padding.get("subcard", 0) > comp_padding.get("card", 1e9):
        LOG.warnings.append("`subcard.padding` is larger than `card.padding` — nested container is roomier than its parent.")
    cr = comp_radius.get("checkboxRadio")
    if cr is not None and cr >= 9:
        LOG.warnings.append(f"`checkboxRadio.radius` = {cr:g}px ≥ half of an 18–20px control → checkboxes render as "
                            "circles and become indistinguishable from radios. Consider 4–6px for checkbox, full for radio.")
    return rounded, spacing, comp, comp_radius, comp_padding, radius_key, strategy, shape, comp_elev, hybrid


# --------------------------------------------------------------------------- elevation
def collect_elevation(root, roles_light):
    el = root.get("appearance", {}).get("elevation", {})

    def val(k, d=None):
        n = el.get(k)
        return n.get("$value", d) if isinstance(n, dict) else d
    strategy = val("strategy", "material")
    tint = norm_hex(val("tintColor", "#000000"))
    border_op = val("borderOpacity", 0.08)
    blur = dim(val("backdropBlur", {"value": 0, "unit": "px"}))
    levels = {}
    for i, (name, tok) in enumerate(children(el.get("levels", {})).items(), 1):
        v = tok["$value"]
        parts = [dim(v.get(k, 0)) for k in ("offsetX", "offsetY", "blur", "spread")]
        op = v.get("opacity", 0.1)
        levels[name] = {
            "light": f"{' '.join(parts)} {rgba(tint, op)}",
            "dark": f"{' '.join(parts)} {rgba('#000000', min(round(op * 2.5, 2), 0.6))}",
            "opacity": op,
            # glow strategy: halo + border in primary; strength follows level opacity
            "glow": {"blur": f"{4 * i + 4}px", "haloMix": round(op * 300),
                     "borderMix": min(90, round(op * 400)),
                     "css": f"0 0 {4 * i + 4}px color-mix(in srgb, <primary> {round(op * 300)}%, transparent)"},
        }
    intensity = val("intensity", 0.5)
    extras = {
        "strategy": strategy,
        "intensity": intensity,
        "tintColor": tint,
        "requiresBorder": val("requiresBorder", False),
        "borderOpacity": border_op,
        "borderLight": rgba(tint, border_op),
        "borderDark": rgba("#ffffff", border_op),
        "supportsBackdropBlur": val("supportsBackdropBlur", False),
        "backdropBlur": blur,
        "levels": levels,
    }
    if strategy == "glass":
        alpha = round(max(0.5, min(0.9, 1 - intensity)), 2)
        extras["glassSurfaceAlpha"] = alpha
        LOG.inferred.append(f"Glass surface opacity = {alpha} (derived as 1 − intensity {intensity}, clamped 0.5–0.9).")
        if contrast(tint, roles_light["background"]) > 1 and border_op < 0.1:
            LOG.warnings.append(f"Glass border at {border_op} opacity is nearly invisible on light backgrounds; "
                                "glass cards rely on a colorful backdrop to read as glass.")
    return extras


# --------------------------------------------------------------------------- components
def build_components(roles, typo, rounded, radius_key, comp_padding, spacing, palettes, corner="rounded-mixed",
                     hybrid_comp_radius=None):
    def r(name, fallback):
        # Hybrid mode: component radii are literal px, independent of the rounded.* scale.
        if hybrid_comp_radius is not None and hybrid_comp_radius.get(name) is not None:
            return f"{hybrid_comp_radius[name]:g}px"
        k = radius_key.get(name) or fallback
        return "{rounded.%s}" % k
    label = "label-lg" if "label-lg" in typo else "label-md"
    body = "body-md" if "body-md" in typo else next(iter(typo), None)
    sp = lambda a, b: f"{spacing.get(a, '12px')} {spacing.get(b, '24px')}"  # noqa: E731
    comps = {}
    hover = "primary-hover" if "primary-hover" in roles else None
    comps["button-primary"] = {"backgroundColor": "{colors.primary}", "textColor": "{colors.on-primary}",
                               "typography": "{typography.%s}" % label, "rounded": r("button", "md"),
                               "padding": sp("sm", "lg")}
    if hover:
        comps["button-primary-hover"] = {"backgroundColor": "{colors.%s}" % hover}
    if "primary-container" in roles:
        comps["button-secondary"] = {"backgroundColor": "{colors.primary-container}",
                                     "textColor": "{colors.on-primary-container}",
                                     "typography": "{typography.%s}" % label, "rounded": r("button", "md"),
                                     "padding": sp("sm", "lg")}
    comps["input"] = {"backgroundColor": "{colors.surface-container-lowest}", "textColor": "{colors.on-surface}",
                      "typography": "{typography.%s}" % body, "rounded": r("input", "md"),
                      "padding": sp("sm", "md")}
    comps["card"] = {"backgroundColor": "{colors.surface}", "textColor": "{colors.on-surface}",
                     "rounded": r("card", "lg"),
                     "padding": f"{comp_padding['card']:g}px" if comp_padding.get("card") else spacing.get("lg")}
    if "subcard" in radius_key or "subcard" in comp_padding:
        comps["card-nested"] = {"backgroundColor": "{colors.surface-container}", "textColor": "{colors.on-surface}",
                                "rounded": r("subcard", "md"),
                                "padding": f"{comp_padding['subcard']:g}px" if comp_padding.get("subcard") else spacing.get("md")}
    comps["checkbox"] = {"backgroundColor": "{colors.primary}", "textColor": "{colors.on-primary}",
                         "rounded": r("checkboxRadio", "sm"), "size": "20px"}
    comps["radio"] = {"backgroundColor": "{colors.primary}", "rounded": "{rounded.full}", "size": "20px"}
    if "secondary-container" in roles:
        comps["chip"] = {"backgroundColor": "{colors.secondary-container}",
                         "textColor": "{colors.on-secondary-container}",
                         "typography": "{typography.%s}" % ("label-md" if "label-md" in typo else label),
                         "rounded": "{rounded.full}" if corner != "sharp" else
                         "{rounded.%s}" % next((k for k, v in rounded.items() if (dim_px(v) or 0) > 0), "none"),
                         "padding": sp("xs", "sm")}  # chip has no user-set radius -> stays on the global scale
    if "link" in roles:
        comps["link"] = {"textColor": "{colors.link}", "typography": "{typography.%s}" % body}
    LOG.inferred.append("Component paddings / sizes not present in tokens were taken from the spacing scale "
                        "(button, input, chip padding; checkbox/radio size 20px).")
    return comps


# --------------------------------------------------------------------------- yaml emit
def q(v):
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    return "'" + str(v).replace("'", "''") + "'"


def emit_yaml(name, colors, color_src, typo, rounded, spacing, comps):
    out = ["version: alpha", f"name: {q(name)}",
           "description: '__FILL_IN__ one-sentence summary of the visual identity'", "colors:"]
    for k, v in colors.items():
        c = color_src.get(k)
        out.append(f"  {k}: {q(v)}" + (f"  # {c}" if c else ""))
    out.append("typography:")
    for k, e in typo.items():
        out.append(f"  {k}:")
        for pk, pv in e.items():
            out.append(f"    {pk}: {q(pv)}")
    out.append("rounded:")
    out += [f"  {k}: {q(v)}" for k, v in rounded.items()]
    out.append("spacing:")
    out += [f"  {k}: {q(v)}" for k, v in spacing.items()]
    out.append("components:")
    for k, e in comps.items():
        out.append(f"  {k}:")
        out += [f"    {pk}: {q(pv)}" for pk, pv in e.items()]
    return "\n".join(out) + "\n"


def write_report(path, contrast_rows):
    L = ["# Token conversion report", ""]
    sections = [("Errors (must fix)", LOG.errors), ("Repaired references", LOG.fixed_refs),
                ("Renames, aliases & duplicates", LOG.aliases),
                ("Inferred values (not in tokens — confirm with user or reference material)", LOG.inferred),
                ("Warnings (design issues in the source tokens — report, do not silently change)", LOG.warnings)]
    for title, items in sections:
        L.append(f"## {title}")
        L += [f"- {i}" for i in items] or ["- none"]
        L.append("")
    L += ["## Derived role contrast", "", "| pair | ratio | AA text (4.5) |", "|---|---|---|"]
    L += [f"| {a} / {b} | {r}:1 | {'pass' if r >= 4.5 else 'FAIL'} |" for a, b, r in contrast_rows]
    Path(path).write_text("\n".join(L) + "\n", encoding="utf-8")


# --------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tokens")
    ap.add_argument("--out-dir", default="work")
    ap.add_argument("--name", default=None)
    ap.add_argument("--default-mode", choices=["light", "dark"], default="light")
    ap.add_argument("--spacing-base", type=int, default=4)
    ap.add_argument("--palette-map", default="{}", help='JSON, e.g. {"primary-2":"secondary"}')
    a = ap.parse_args()

    root = json.loads(Path(a.tokens).read_text(encoding="utf-8"))
    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    palettes, modes, semantic, sem_src, singles = collect_colors(root, json.loads(a.palette_map))
    main_mode, alt_mode = a.default_mode, ("dark" if a.default_mode == "light" else "light")
    roles, rsrc = build_roles(main_mode, palettes, modes, semantic, sem_src, singles)
    alt, asrc = build_roles(alt_mode, palettes, modes, semantic, sem_src, singles) if alt_mode in modes else ({}, {})
    for k in ("primary", "secondary", "tertiary"):
        if k in alt:
            roles[f"inverse-{k}"] = alt[k]
            rsrc[f"inverse-{k}"] = f"{alt_mode} {k}"
    roles["inverse-surface"] = alt.get("surface", roles["on-surface"])
    roles["inverse-on-surface"] = alt.get("on-surface", roles["surface"])
    rsrc["inverse-surface"] = rsrc["inverse-on-surface"] = f"{alt_mode} mode"

    colors, csrc = {}, {}
    for k, v in roles.items():
        colors[k], csrc[k] = v, rsrc.get(k)
    for k, v in alt.items():
        colors[f"{alt_mode}-{k}"], csrc[f"{alt_mode}-{k}"] = v, asrc.get(k)
    for k, v in singles.items():
        colors.setdefault(k, v)
    for p, shades in palettes.items():
        for s in SHADE_KEYS:
            if s in shades:
                colors[f"{p}-{s}"] = shades[s]

    typo, families = collect_typography(root)
    rounded, spacing, comp, comp_radius, comp_padding, radius_key, corner, shape, comp_elev, hybrid = \
        collect_shape_and_spacing(root, a.spacing_base)
    elevation = collect_elevation(root, roles if main_mode == "light" else alt or roles)
    colors["shadow-tint"] = elevation["tintColor"]
    csrc["shadow-tint"] = "appearance.elevation.tintColor"
    comps = build_components(roles, typo, rounded, radius_key, comp_padding, spacing, palettes, corner,
                             comp_radius if hybrid else None)

    name = a.name or root.get("meta", {}).get("name") or "Untitled Design System"
    (out / "frontmatter.yaml").write_text(emit_yaml(name, colors, csrc, typo, rounded, spacing, comps),
                                          encoding="utf-8")

    # decorative containers that could be mistaken for status colors
    for prefix, rs in (("", roles), (f"{alt_mode}-", alt)):
        for deco in ("primary-container", "secondary-container", "tertiary-container"):
            for status in ("error-container", "warning-container", "success-container"):
                if deco in rs and status in rs and looks_similar(rs[deco], rs[status]):
                    LOG.warnings.append(
                        f"`{prefix}{deco}` ({rs[deco]}) looks like `{prefix}{status}` ({rs[status]}): chips/tonal "
                        f"elements using it may be read as {status.split('-')[0]} states. Consider a neutral "
                        "surface-container for those components.")
    pairs = [(x, f"on-{x}") for x in roles if f"on-{x}" in roles]
    pairs += [(f"{alt_mode}-{x}", f"{alt_mode}-on-{x}") for x in alt if f"on-{x}" in alt]
    pairs += [("background", "on-surface-variant")] if "on-surface-variant" in roles else []
    rows = [(x, y, contrast(colors[x], colors[y])) for x, y in pairs if x in colors and y in colors]
    for x, y, rt in rows:
        if rt < 4.5:
            LOG.warnings.append(f"Contrast {x}/{y} = {rt}:1 is below WCAG AA 4.5:1 for text.")

    border = shape.get("borderStrategy", {}).get("$value") if isinstance(shape.get("borderStrategy"), dict) else None
    bwidth = dim(shape["borderWidth"]["$value"]) if isinstance(shape.get("borderWidth"), dict) else "1px"
    extras = {
        "defaultMode": main_mode,
        "altMode": alt_mode if alt else None,
        "fontFamilies": families,
        "fontWeights": sorted({e.get("fontWeight", 400) for e in typo.values()}),
        "elevation": elevation,
        "shape": {"cornerStrategy": corner, "borderStrategy": border, "borderWidth": bwidth,
                  "componentRadius": comp_radius, "componentPadding": comp_padding, "radiusKey": radius_key,
                  "componentElevation": comp_elev},
        "colorSource": csrc,
        "paletteNames": list(palettes.keys()),
        "semanticSource": sem_src,
    }
    (out / "extras.json").write_text(json.dumps(extras, ensure_ascii=False, indent=2), encoding="utf-8")
    write_report(out / "report.md", rows)
    print(f"frontmatter: {len(colors)} colors, {len(typo)} type styles, {len(rounded)} radii, "
          f"{len(spacing)} spacing, {len(comps)} components")
    print(f"errors={len(LOG.errors)} warnings={len(LOG.warnings)} inferred={len(LOG.inferred)} "
          f"fixed_refs={len(LOG.fixed_refs)} → see {out/'report.md'}")
    sys.exit(1 if LOG.errors else 0)


if __name__ == "__main__":
    main()
