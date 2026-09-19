---
name: design-md-builder
description: Turn a design-tokens.json (W3C DTCG / Design Token Builder export) plus reference material (screenshots, URLs, brand guides, CSS/React code) into a Google Stitch-compliant DESIGN.md and a single-file preview.html that renders the system. Use this whenever the user wants to write, generate, convert or update a DESIGN.md, build a design system spec or style guide from tokens, turn tokens into AI-readable design guidelines, or preview what a token set looks like — including casual phrasings like "幫我寫設計規範", "把 token 轉成 DESIGN.md", "做一份設計系統文件", "Stitch design md", or when a design-tokens.json is uploaded with any design references. Not for building a full product site from an existing DESIGN.md.
---

# DESIGN.md Builder

Produces exactly two deliverables:

1. **`DESIGN.md`** — the single source of truth that other AI tools will follow when generating
   web pages, slides, images and social cards. Stitch format: YAML frontmatter (machine tokens)
   + Markdown sections (human/AI-readable rules).
2. **`preview.html`** — one self-contained page that renders every token and a realistic sample
   screen, so the user can judge the system before real design work starts.

The core principle: **numbers come from scripts, judgment comes from you.** Converting 150+ token
values by hand is where errors creep in, so the scripts do the deterministic mapping, contrast math
and validation. Your job is reading the references, deciding what the system *means*, and writing
rules precise enough that another model reproduces the look without seeing the references.

Paths below are relative to this skill's directory (`scripts/…`, `references/…`, `assets/…`).
Use a scratch dir such as `work/` for intermediate files.

## Workflow

1. **Inventory inputs.** Locate the tokens file and every reference (images, URLs, code, text).
   If there is no tokens file, stop and ask — this skill converts tokens, it does not invent a
   palette. If there are no references, proceed but tell the user that brand/style prose will be
   inferred from the tokens alone.

2. **Convert tokens.**
   ```bash
   python scripts/tokens_to_frontmatter.py design-tokens.json --out-dir work --name "<System Name>"
   ```
   Options: `--default-mode dark` when references are dark-first; `--spacing-base 8` for 8pt
   systems; `--palette-map '{"accent-1":"secondary"}'` to override role assignment.
   Read `work/report.md` fully. It lists repaired references, dropped duplicate palettes,
   **inferred values** and **warnings** about the source tokens. Read
   `references/mapping-rules.md` if any mapping needs explaining or overriding.

   Some token files use a **hybrid radius system**: a global `rounded` scale exists alongside
   independent hard-coded per-component radii that don't match the scale's steps. The converter
   detects this automatically (report.md logs it under aliases, not warnings) and keeps both:
   `rounded.*` comes from the global scale, components with their own radius get a literal px
   value instead of a `{rounded.*}` reference. This is not a bug to fix — see
   `references/mapping-rules.md` §3 before "correcting" a component radius that looks like it
   doesn't match the scale.

   If the user tells you a value the script flags (an inferred value, a warning, a "looks
   confusable" note) is a deliberate design decision rather than a defect, take that at face
   value for this project and move on — don't re-litigate it. Still write the deliberate value
   into DESIGN.md as a stated rule (not silently, and not as a caveat) so a future reader
   understands it was a choice: e.g. "checkboxes use a 15px radius for a soft-round rather than
   fully round or square look" rather than omitting the reasoning. This applies per-project; it
   doesn't change what the script reports for the next token file.

3. **Analyze references.** Extract what tokens cannot express:
   - brand personality, audience, emotional target (3–5 precise adjectives, not "modern and clean")
   - layout density, grid, section rhythm, content width → confirm or adjust the inferred spacing
   - imagery (photo vs illustration, treatment), iconography (stroke/fill, weight, corner style)
   - motion cues, if any
   - which archetype it resembles — `references/examples.md` has a table of Stitch archetypes and
     a "signal → decision" table.
   When a reference contradicts a token value, the token wins (the user built it deliberately);
   mention the conflict in your report instead of changing the token.

4. **Assemble DESIGN.md** — frontmatter from `work/frontmatter.yaml` (fill `description`, adjust
   inferred spacing if references justify it), then write the body per the section guide below.
   The generated `components` block is a sensible default, not the user's decision: if report.md
   flags a component color as confusable (e.g. chips that look like error states) or the
   references show a different treatment, change that component's references.

5. **Lint until clean.**
   ```bash
   python scripts/lint_design_md.py DESIGN.md
   ```
   Fix every ERROR (structure, broken references, prose hex not in frontmatter, contrast below
   4.5:1, leftover placeholders). Read WARNs and fix those that are real.

6. **Write the sample fragment and build the preview.**
   ```bash
   python scripts/build_preview.py DESIGN.md --extras work/extras.json --sample work/sample.html --out preview.html
   ```
   See "Sample page" below. Fix any WARN about hard-coded colors, then open or screenshot the
   result if the environment allows and check it looks right in both themes.

7. **Deliver** both files (in claude.ai: copy to `/mnt/user-data/outputs/` and present them).
   Then give the user a short report **in their language**: what was inferred, token-level issues
   worth fixing at the source (from `report.md` warnings), and any reference/token conflicts.
   Keep it to what they need to act on.

## Writing the DESIGN.md body

Write the body in **English** (the language Stitch and most generation models parse best). Where
the system uses CJK fonts, include CJK-specific rules in English.

Use this section order. Standard sections must stay in this order; extension sections go between
Components and Do's and Don'ts. One optional `#` title at the top.

```
# <System Name>
## Brand & Style
## Colors
## Typography
## Layout & Spacing
## Elevation & Depth
## Shapes
## Components
## Media Adaptation        ← extension (always include; see below)
## Iconography / ## Imagery / ## Motion   ← extensions, only when references support them
## Do's and Don'ts
```

Rules that apply to every section:

- **Every number must be a token or cite one.** Write "`primary` (#5b7b88)" or "`rounded.lg`
  (25px)", never a free-floating value. Any hex in prose must exist in frontmatter — the linter
  enforces this because prose/token drift is the most common failure in Stitch's own examples.
- **Rules, not adjectives.** "Primary fills are reserved for the single main action per view" is
  usable; "the palette feels calm" is not. Each section should let a model decide correctly in a
  situation the references never showed.
- **Explain the why** briefly when a rule is non-obvious, so the consumer can generalize.

Section guide:

- **Brand & Style** — who it's for, the emotional target, the archetype, and 2–3 signature traits
  that make it recognizable (e.g. "translucent glass panels over muted tinted backdrops"). Mention
  the default color mode.
- **Colors** — role-by-role usage: primary / secondary / tertiary, surfaces and containers
  (which container for which layer), outline vs outline-variant, semantic colors, link. State the
  proportion (e.g. neutrals ~80–90% of area, primary for actions and key data only). Describe the
  alternate mode and the `dark-*` keys. Note that palettes (`primary-50…950`) exist for charts
  and illustration tints.
- **Typography** — font stack incl. CJK fallback and why; the role of each level
  (display = hero only, headline-* = section hierarchy, body-*, label-* for UI chrome); weights;
  line length (60–75 ch Latin, ~30–40 CJK characters); CJK rules: no negative letter-spacing on
  CJK text, body line-height ≥ 1.6. Report any hierarchy collision from report.md as a rule
  (e.g. "never use body-lg directly under headline-sm; they share 23px").
- **Layout & Spacing** — grid (columns, gutter, margin, max content width), spacing scale usage
  (which steps for component internals vs between sections), density, breakpoints.
- **Elevation & Depth** — the strategy and exact values: each level's shadow CSS, blur, surface
  opacity, border — all from `extras.json`. Say which level each component uses and the dark-mode
  treatment. For glass: needs a tinted backdrop, never glass-on-glass beyond one level.
- **Shapes** — cornerStrategy in plain words; which rounded key each component uses; concentric
  radius rule for nested containers; when `full` is allowed.
- **Components** — for each component: anatomy, token references, and states (default, hover,
  focus-visible ring, active, disabled at 38% opacity, error). Include components the references
  show that the script did not generate (nav bar, table, tabs, modal…), built from existing tokens.
- **Media Adaptation** — the user uses this file for slides, images and social cards too, and
  those consumers otherwise fall back to generic styling. Give concrete translations:
  slides (16:9, which type levels scale up and by how much, one idea per slide, background
  surfaces), social/graphic cards (safe margins, color proportion, max two type levels), image
  generation (a reusable prompt fragment describing palette by color *names*, lighting, texture,
  mood — plus what to avoid), charts (series order from palette shades, gridline color).
- **Do's and Don'ts** — 6–10 of each, concrete and checkable, covering color proportion, type,
  elevation, shape, accessibility and anything flagged in report.md. Pair them where possible.

## Sample page (`work/sample.html`)

A fragment (no `<html>/<head>/<body>`) inserted at the top of the preview, inside a container with
the `.backdrop` class. It is what the user looks at first, so it should feel like a real screen
of *their* product:

- Pick the page type from the references (landing hero, dashboard, article, app screen). Use real
  domain copy — never lorem ipsum. Follow the frontend-design skill's guidance if available.
- Style **only** with the generated API — `var(--<color>)`, `var(--r-<k>)`, `var(--s-<k>)`,
  `.t-<type>`, `.c-<component>`, `.elev-<n>`. A local `<style>` block is fine for layout
  (grid/flex/gaps) but every color, radius and space value inside it must be a `var()`. No
  hard-coded hex/rgb; the builder warns on them because they break theme switching and fidelity.
- Anything that must follow the theme toggle (backgrounds, illustration fills, text) uses **role**
  colors (`--surface`, `--primary-container`, `--tertiary`…) or `color-mix()` of role colors.
  Palette shades (`--primary-100`) are fixed across modes, so a hero built from them stays light
  in dark mode. Use shades only for things that should look identical in both modes.
- Show the signature traits: the elevation strategy on real cards, the primary action, at least
  one input or control, and type hierarchy from display down to label.
- Responsive to ~360px; prefix local classes with `sp-` to avoid clashing with preview chrome.

## Things to avoid

- Silently "fixing" the user's tokens (renaming their scale, changing a radius). Report issues;
  change tokens only when asked.
- Writing prose from the Stitch examples' template — they are deliberately thin.
- Adding frontmatter keys outside `version, name, description, colors, typography, rounded,
  spacing, components`; put elevation and other non-slot details in prose.
- Hand-editing preview.html. Change DESIGN.md or the sample fragment and rebuild, so the preview
  can never disagree with the spec.

## Files

- `scripts/tokens_to_frontmatter.py` — DTCG tokens → `frontmatter.yaml`, `extras.json`, `report.md`
- `scripts/lint_design_md.py` — spec + house-rule validation (exit 1 on errors)
- `scripts/build_preview.py` — DESIGN.md + extras + sample fragment → `preview.html`
- `scripts/colorlib.py` — contrast helpers (shared)
- `assets/preview-template.html` — preview shell (swatches, type, spacing, elevation, components, theme toggle)
- `references/spec.md` — Stitch DESIGN.md specification (consult for schema questions)
- `references/mapping-rules.md` — exactly how each token maps, and how to override
- `references/examples.md` — Stitch style archetypes and reference-signal → decision table
