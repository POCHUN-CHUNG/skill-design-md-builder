# Token → DESIGN.md mapping rules

What `tokens_to_frontmatter.py` does, and what it leaves for you to write in prose.
Read this when you need to explain a value, override a default, or handle a token file
whose shape differs from the usual Design Token Builder export.

## 1. Colors

Two source layouts are normalised to the same internal shape `{mode: {palettes, semantic, surface}}`:

| Layout | Palettes | Semantic | Surface roles |
|---|---|---|---|
| **mode-first** (current export) | `color.<mode>.<palette>.<shade>` (+ optional `.on`) | `color.<mode>.semantic.*` | `color.<mode>.surface.{bg, surface, surfaceRaised, text, textMuted, textInverted, border, borderStrong, btnSecondaryBg, btnInvertedBg, btnOutlinedText}` |
| **legacy** | `color.<palette>.<shade>` (shared) | `color.semantic.*` (shared) | flat `color.<mode>.{bg, surface, text, border}` |

| Source (DTCG) | DESIGN.md key | Rule |
|---|---|---|
| `<palette>.{50..950}` | `<palette>-<shade>` | Flattened from the default mode. Kept so prose and components can point at exact shades. If the alternate mode's shades differ, only the differing ones are added as `dark-<palette>-<shade>` (the preview follows the toggle). |
| `primary-2` / `primary-3` | `secondary-*` / `tertiary-*` | Renamed when no `secondary`/`tertiary` exists. Override with `--palette-map`. |
| Palette identical to an earlier one **in every mode** | dropped | Logged as alias (e.g. `accent-2` = `secondary`). Refer to the survivor. |
| default-mode `bg / surface / text / border` | `background`, `surface`, `on-surface`, `on-background`, `outline-variant` | Unprefixed. |
| alternate-mode surface tokens | `dark-background`, `dark-surface`, … | `dark-` prefix (or `light-` when `--default-mode dark`). |
| `btnSecondaryBg` | `button-secondary`, `on-button-secondary` | Token value as given; on-color = first of text/background reaching 4.5:1. Drives the `button-secondary` component (in older files without it, that component falls back to `primary-container`). |
| `surfaceRaised` | `surface-raised` | Token value as given. Used as the nested-card background (inferred: the tokens do not name the component). |
| `textMuted` | `on-surface-variant` | Token wins over the derived neutral shade. |
| `borderStrong` | `outline` | Token wins. The control-boundary color (input, outlined button, unchecked checkbox/radio). |
| `textInverted` | `on-button-inverted` | Token wins over the derived on-color. |
| `btnOutlinedText` | `button-outlined-text` | Label color of the `button-outlined` component (falls back to `primary` when absent). |
| `btnInvertedBg` | `button-inverted`, `on-button-inverted` | Same rule; drives the `button-inverted` component (inverse-polarity button: dark on light pages, light on dark). |
| other `surface.*` tokens | kebab-case role of the same name | e.g. `chartGrid` → `chart-grid`. No on-color is generated. |
| derived | `surface-container-lowest … highest` | `low…highest` mix the surface toward text (light 3/6/9/12 %, dark 4/7/10/14 %) so containers keep the surface's tint. `lowest` is the extreme end of the ramp: the page background (dark: slightly darker) normally, but the **surface itself** when it already lies beyond the background (white cards on a gray page, black cards on a dark-gray page) — this keeps the ramp monotonic. |
| derived (only without `borderStrong` / `textMuted`) | `outline`, `on-surface-variant` | Neutral shade that reaches 3:1 (outline) / 4.5:1 (secondary text). `outline` is the control-boundary color; `outline-variant` (`border`) is the decorative hairline. |
| `<palette>.on` | `on-primary` / `on-secondary` / `on-tertiary` | Explicit pairing from the tokens: the role fill is then the palette's **500** and the label color is `on` as given (no contrast-driven shade search; hover = one step darker/lighter; container 100/900 light, 800/100 dark). Contrast below 4.5:1 is reported, not fixed. `on` of other palettes (neutral, link, accent-*) is read but not turned into roles. Without `.on` the derived search below applies. |
| `primary` palette (no `.on`) | `primary`, `on-primary`, `primary-hover`, `primary-container`, `on-primary-container` | Light: first of 500→600→700→400→800 whose best on-color is ≥ 4.5:1 and which is ≥ 3:1 against background. Dark: 300→200→400→100. Hover is one shade darker (light) / lighter (dark). Container 100/900 (light), 800/100 (dark). Same for secondary/tertiary. |
| `semantic.*` | `success`, `warning`, `error`, `info` + `on-*`, `*-container`, `on-*-container` | mode-first: each mode's value is used **as given** (token wins). legacy: light as given, dark derived from a lighter shade of the source palette. Source palette is found by matching its 500 shade; containers come from that palette. A warning is logged when a semantic fill is < 4.5:1 on its surface (fine for fills/icons, not for text). Semantic colors without a matching palette shade get **derived containers**: the color tinted into the surface (14 % light / 28 % dark) with an on-color mixed toward text (≥ 4.5:1), logged as inferred. |
| `link` palette | `link` | First shade ≥ 4.5:1 against background. |
| derived | `focus-ring` | First of `primary`, `link`, `on-surface` that is ≥ 3:1 against both background and surface (a deep primary that is invisible on dark surfaces falls back to `link`). Use it for focus-visible rings and for accent strokes/text that must stay visible on dark surfaces. |
| alternate mode primaries | `inverse-primary`, `inverse-surface`, `inverse-on-surface` | M3 convention for snackbars / inverted regions. |
| `appearance.elevation.tintColor` | `shadow-tint` | Added so prose can name the shadow color and the linter's hex check passes. |
| `meta.a11yStatus` / `a11yFailCount` | `extras.meta` | Shown in the preview; a non-pass status is logged as a warning. |

Role colors are emitted as literal hex with a YAML comment naming their source shade — Stitch's
own files use literal hex, and the comment keeps traceability.

**Accepted deviations.** `--accept` (converter) and `--extras` (linter) let a user-declared, deliberate deviation stand: `contrast:<role>/<on-role>` (both modes at once) and `border-conflict` (`requiresBorder` with `borderStrategy: none`). They are listed in the report under "Accepted by the user" and must be written into DESIGN.md as rules.

## 2. Typography

- `{fontFamily.heading}` style references are repaired to the real path (e.g. `typography.families.heading`) and logged.
- Font family arrays become a comma-separated stack: `Noto Sans, Noto Sans TC`. The first family is
  the Latin face, later ones are fallbacks (CJK). Explain this in the Typography prose.
- `{value, unit}` → `44px`, `-0.025em`. Unitless line-height stays a number (spec recommendation).
- Checks: sizes strictly decreasing inside `headline-*`, `body-*`, `label-*`; same size used by different
  roles is flagged as a hierarchy collision. Report — don't silently change the user's scale.

Sizes below 12px trigger a readability warning.

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
backdrop blur and (for glass) the derived surface opacity. Elevation is parametric: when
`appearance.elevation.levels` is absent, `strategy` / `intensity` / `tintColor` are enough — a 5-step
ramp is generated (offsetY 1/4/10/16/24px, opacity 0.08→0.20 scaled by `intensity / 0.35`) and logged
as inferred. `appearance.component.<name>.elevation` (e.g. `card` → `level-1`) is recorded in
`extras.shape.componentElevation`.

**Border strategy.** `borderStrategy: none` (or `borderWidth: 0`) removes the *decorative* borders — card edge, nested card, glass edge, dividers (`--border-width` / `--subcard-border-width` = 0 in the preview). Controls keep a 1px `outline` (`borderStrong`) edge (`--control-border-width`) because inputs, outlined buttons and unchecked checkbox/radio are invisible otherwise; this is logged as inferred. When `elevation.requiresBorder` is true for glass, a conflict warning is raised and the shape setting wins. Write the exact CSS values into
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

Generated set: `button-primary`, `button-primary-hover`, `button-secondary`, `button-inverted`
(only with `btnInvertedBg`), `input`, `card`, `card-nested`, `checkbox`, `radio`, `slider-track` +
`slider-thumb` (only with `component.slider.radius`; track 8px / thumb 24px are inferred), `chip`, `link`.
Radii come from `appearance.component.*.radius`, card padding from tokens, everything else from the
spacing scale (logged as inferred). Selection controls: a checked `checkbox` is a **solid `primary` fill with no check
glyph** (so it has no `textColor`); a selected `radio` keeps a `primary` ring with an inner dot, which is what
separates the two when `checkboxRadio.radius` makes both near-circular. Borders: `appearance.shape.borderWidth` (all surfaces) and
`subcardBorderWidth` (nested card) have no frontmatter slot — write them into prose; the preview
exposes them as `--border-width` / `--subcard-border-width`. Stick to the common property set — `backgroundColor`,
`textColor`, `typography`, `rounded`, `padding`, `size`, `height`, `width` — unknown properties are
accepted but warned. Describe borders, focus rings and disabled states in prose.

State variants use a suffix the preview understands: `-hover`, `-active`, `-focus`, `-disabled`.

## 7. Adding tokens by hand

You may add keys the script cannot know about (brand-specific surfaces, chart colors, a display
type style). Keep them primitive (hex / dimension), keep names kebab-case, and re-run the linter.
