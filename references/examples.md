# Stitch example library — style archetypes

Ten official Stitch DESIGN.md samples, condensed. Use them to (a) calibrate vocabulary when
describing a style and (b) sanity-check that font / radius / elevation choices hang together.
Do **not** copy their prose quality: the originals are thin (one-line sections) and several quote
hex values in prose that differ from their own frontmatter (e.g. Modern Tech says `#6366f1` in
prose but `primary: '#4648d4'`). Your output must be richer and internally consistent.

| # | Name | Mode | Headline / Body / Label | Base radius | Elevation | Vibe keywords |
|---|---|---|---|---|---|---|
| 01 | Modern Tech | light | Plus Jakarta Sans (all) | 0.5rem | tonal + soft diffused shadow | precise, accessible, balanced; indigo + violet |
| 02 | Bauhaus | light | Space Grotesk / Inter / Space Grotesk | 0.25rem | outlines + tonal, no heavy shadow | neutral-modern, high precision; black + red + cobalt accents |
| 03 | Obsidian | dark | Geist (all) | 0.5rem | tonal layering, border contrast | developer, futuristic; violet + mint on charcoal |
| 04 | Expressive | light | DM Sans (all) | 1rem, pill buttons | tonal + low outlines, minimal shadow | vibrant, friendly, creative; magenta + purple + cyan |
| 05 | Tonal Spot Nature | light | Literata / Nunito Sans | 0.5rem | tonal + earthy-tinted ambient shadow | calm, organic, wellness/editorial; forest green + sand |
| 06 | IBM Plex Corporate | light | IBM Plex Sans (all, 9 levels) | 0.25rem | tonal + ghost borders | enterprise, dense data, reliable; IBM blue + green |
| 07 | Fidelity | light | EB Garamond / Manrope | 0.5rem | tonal + warm diffused shadow | editorial, warm, crafted; terracotta + crimson |
| 08 | Vibrant Dark | dark | Inter (all, 9 levels) | 0.5rem | tonal + low outlines | immersive, energetic; sky blue + lavender on navy |
| 09 | Vibrant Neon Dark | dark | Sora / Inter / Space Grotesk | 0.25rem | tonal + ambient glow | bold, high-energy; hot pink + cyan + yellow |
| 10 | Fidelity Modern Serif | light | Noto Serif / Inter / Public Sans | 0.25rem | tonal, restrained contrast | corporate-editorial authority; royal blue + gold |

## Patterns worth reusing

- **Pairing logic**: serif headline + humanist/geometric sans body = editorial authority (05, 07, 10).
  Single geometric sans across all levels = product/tool UI (01, 03, 06, 08).
  Grotesk headlines/labels + neutral body = technical or constructivist edge (02, 09).
- **Radius ↔ tone**: 0.25rem → corporate/technical; 0.5rem → neutral product; ≥1rem / pill → friendly, consumer, playful.
- **Dark systems** lean on tonal layering + borders; shadows barely read on dark surfaces. Glow is the dark-mode equivalent of a shadow.
- **Type scale depth**: 3 levels (headline-lg/body-md/label-md) is the Stitch minimum; product UIs benefit from the full 9–10 levels (06, 08).

## Reading reference material → style decisions

| Signal in reference | Likely decision |
|---|---|
| Dense tables, dashboards, admin | tighter spacing (gutter 16px), smaller body (14–16px), flat or material elevation |
| Hero photography, marketing | looser spacing (gutter 24–32px, section padding 64–96px), larger display type |
| Frosted panels over imagery/gradients | glass elevation, tinted backdrop required |
| Code editors, terminals, dev tools | dark default, mono accents only for code, glow or flat |
| Long-form reading | 60–75 ch measure, line-height ≥ 1.6, serif or humanist body |
| CJK-heavy content | CJK fallback family, line-height ≥ 1.6 for body, avoid letter-spacing < 0 on CJK text |
