# Token → DESIGN.md mapping rules

What `tokens_to_frontmatter.py` does, and what it leaves for you to write in prose.
Read this when you need to explain a value, override a default, or handle a token file
whose shape differs from the usual Design Token Builder export.

## 1. Colors

| Source (DTCG) | DESIGN.md key | Rule |
|---|---|---|
| `color.<palette>.{50..950}` | `<palette>-<shade>` | Flattened. Kept so prose and components can point at exact shades. |
| `color.primary-2` / `primary-3` | `secondary-*` / `tertiary-*` | Renamed when no `secondary`/`tertiary` exists. Override with `--palette-map`. |
| Palette identical to an earlier one | dropped | Logged as alias (e.g. `accent-2` = `secondary`). Refer to the survivor. |
| `color.light.bg/surface/text/border` | `background`, `surface`, `on-surface`, `on-background`, `outline-variant` | Default mode, unprefixed. |
| `color.dark.*` | `dark-background`, `dark-surface`, … | Alternate mode gets the `dark-` prefix (or `light-` when `--default-mode dark`). |
| derived | `surface-container-lowest … highest` | Mix of surface toward text (light 3/6/9/12 %, dark 4/7/10/14 %) so containers keep the surface's tint instead of switching to a gray ramp. |
| derived | `outline`, `on-surface-variant` | Neutral shade that reaches 3:1 (outline) / 4.5:1 (secondary text). |
| `primary` palette | `primary`, `on-primary`, `primary-hover`, `primary-container`, `on-primary-container` | Light: first of 500→600→700→400→800 whose best on-color is ≥ 4.5:1 and which is ≥ 3:1 against background. Dark: 300→200→400→100. Hover is one shade darker (light) / lighter (dark). Container 100/900 (light), 800/100 (dark). Same for secondary/tertiary. |
| `color.semantic.*` | `success`, `warning`, `error`, `info` + `on-*`, `*-container`, `on-*-container` | Source palette is found by matching its 500 shade; containers come from that palette. |
| `link` palette | `link` | First shade ≥ 4.5:1 against background. |
| alternate mode primaries | `inverse-primary`, `inverse-surface`, `inverse-on-surface` | M3 convention for snackbars / inverted regions. |
| `appearance.elevation.tintColor` | `shadow-tint` | Added so prose can name the shadow color and the linter's hex check passes. |

Role colors are emitted as literal hex with a YAML comment naming their source shade — Stitch's
own files use literal hex, and the comment keeps traceability.

## 2. Typography

- `{fontFamily.heading}` style references are repaired to the real path (e.g. `typography.families.heading`) and logged.
- Font family arrays become a comma-separated stack: `Noto Sans, Noto Sans TC`. The first family is
  the Latin face, later ones are fallbacks (CJK). Explain this in the Typography prose.
- `{value, unit}` → `44px`, `-0.025em`. Unitless line-height stays a number (spec recommendation).
- Checks: sizes strictly decreasing inside `headline-*`, `body-*`, `label-*`; same size used by different
  roles is flagged as a hierarchy collision. Report — don't silently change the user's scale.

## 3. Rounded

The spec has no per-component radius slot, so radii live in `rounded`. How components relate to it
depends on what the token file contains:

- **No radius scale at all** → distinct component radii are sorted into `sm, md, lg, xl, 2xl`;
  `none: 0px` and `full: 9999px` are added; `xs` = half the smallest radius when that radius is
  ≥ 12px. Components reference `{rounded.*}`. `extras.shape.radiusKey` records which key each
  component uses — cite it in Shapes (e.g. "Buttons use `rounded.lg` (25px)").
- **Explicit scale present** (`rounded`, `radius`, `dimension.radius`, or `appearance.radius`) and
  it is NOT `appearance.radius` co-existing with per-component radii → the scale is used as-is and
  components still reference `{rounded.*}` for any key whose value matches.
- **Hybrid system**: `appearance.radius` is a *global* scale (e.g. `sm/md/lg/xl/full`) that exists
  *alongside* independent hard-coded `component.<name>.radius` values, and the two sets of numbers
  don't line up (e.g. global `lg=18px` but `card.radius=30px`). This is a legitimate, deliberate
  pattern some token tools use: the global scale is offered for containers, popovers, charts and
  future/unknown components, while named components keep designer-tuned literal values. In this
  case:
  - `rounded.*` = `appearance.radius.*` verbatim.
  - Components with their own token radius (button, card, input, …) get that value as a **literal
    px string** (`rounded: '25px'`), never `{rounded.*}` — forcing a fictitious match would silently
    change the designer's number.
  - Components with no token radius at all (e.g. `chip`, `radio` if untouched) still fall back to
    `{rounded.*}` from the global scale, since nothing was deliberately set for them.
  - The converter logs this as an alias/note, not a warning — it is not a defect, just a fact to
    write into the Shapes section so the AI consumer understands both numbers are intentional
    ("containers use the `rounded` scale; buttons and cards use their own fixed radii by design").
  - Do not "fix" this by picking one system over the other, and do not silently map hard-coded
    radii onto the nearest scale step — only do so if the user tells you the file's radii are
    supposed to align (a bug), not when they confirm the split is deliberate.

`cornerStrategy` meaning (write it into Shapes):

| value | prose to write |
|---|---|
| `rounded-consistent` | One corner logic scaled proportionally across all sizes. |
| `rounded-mixed` | Large containers rounder, small controls squarer — radius encodes hierarchy. |
| `sharp` | Right angles; technical / engineering tone. Only `full` for pills/avatars. |

Nested containers: inner radius should equal outer radius − padding (concentric corners). The
script flags violations.

## 4. Spacing

If the tokens have no spacing group, a `--spacing-base` (default 4px) scale is generated:
`xs 1×, sm 2×, md 4×, lg 6×, xl 8×, 2xl 12×, 3xl 16×, gutter 6×, margin 8×`. This is an
**inferred** value: adjust gutter/margin/density to the reference material (dense dashboards →
tighter; editorial/marketing → looser) and say so in Layout & Spacing.

## 5. Elevation (no frontmatter slot → prose + preview)

`extras.elevation` holds strategy, per-level CSS shadow strings for light and dark, border colors,
backdrop blur and (for glass) the derived surface opacity. Write the exact CSS values into
`## Elevation & Depth` — AI consumers cannot see extras.json.

| strategy | prose must state | preview renders |
|---|---|---|
| `material` | Compact, higher-opacity shadows; surfaces opaque. | `box-shadow` only (+ border if `requiresBorder`). |
| `glass` | Translucent surface (opacity), `backdrop-filter: blur(Npx)`, 1px border at borderOpacity, large soft shadows tinted with `shadow-tint`; needs a colorful/tinted backdrop behind it; never stack glass on glass more than one level. | color-mix translucent surface + blur + border + shadow, `.backdrop` gradient. |
| `flat` | No shadows; depth = surface-container tonal steps + hairline outline. | Tonal backgrounds + border. |
| `glow` | Luminous borders/halos in primary; for dark tech UIs; glow intensity rises with level. | Primary-tinted outer glow + border. |

Dark-mode shadows use black at 2.5× the light opacity (capped 0.6) because tinted shadows vanish
on dark backgrounds.

## 6. Components

Generated set: `button-primary`, `button-primary-hover`, `button-secondary` (tonal),
`input`, `card`, `card-nested`, `checkbox`, `radio`, `chip`, `link`.
Radii come from `appearance.component.*.radius`, card padding from tokens, everything else from the
spacing scale (logged as inferred). Stick to the common property set — `backgroundColor`,
`textColor`, `typography`, `rounded`, `padding`, `size`, `height`, `width` — unknown properties are
accepted but warned. Describe borders, focus rings and disabled states in prose.

State variants use a suffix the preview understands: `-hover`, `-active`, `-focus`, `-disabled`.

## 7. Adding tokens by hand

You may add keys the script cannot know about (brand-specific surfaces, chart colors, a display
type style). Keep them primitive (hex / dimension), keep names kebab-case, and re-run the linter.
