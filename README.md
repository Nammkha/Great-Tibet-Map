# Chöl-kha-sum — an interactive map of the three regions of Tibet

An interactive SVG map of **Ü-Tsang**, **Kham** and **Amdo** — the three
traditional regions of Tibet (ཆོལ་ཁ་གསུམ་, *chöl-kha-sum*). One self-contained
HTML file: no build step, no framework, no dependencies beyond an optional
Google Fonts request.

Select a region on the map or in the proportional bar above it, and the side
panel gives its Tibetan name, description, dialect group, principal towns,
landscape, area as drawn, and the present-day units it covers.

## Files

| File | What it is |
|---|---|
| `tibet-three-regions-map.html` | The interactive widget. Open it directly in a browser, or embed it. |
| `tibet-three-regions-dark.svg` | Static map, dark. For `<img>`, a CMS, or print. |
| `tibet-three-regions-light.svg` | Static map, light. |
| `INTEGRATION.md` | Full integration, configuration, theming and API reference. |

The static SVGs carry Latin labels only — an SVG loaded through `<img>` can't
fetch a webfont, and most systems have no Tibetan font, so the script would
render as empty boxes. The interactive version shows both scripts.

## Quick start

Open `tibet-three-regions-map.html` in a browser. That's the whole demo.

To put it on a page, either point an iframe at it:

```html
<iframe src="/maps/tibet-three-regions-map.html"
        style="width:100%;height:1050px;border:0"
        loading="lazy"
        title="The three regions of Tibet"></iframe>
```

…or copy everything between the `COPY FROM HERE` and `COPY TO HERE` comments
in that file and paste it into your own page. The block contains the container
div, its `<style>` and its `<script>` — nothing else is needed. Every selector
is scoped to `.tibmap` and every SVG class is prefixed `tm-`, so it won't
collide with your stylesheet.

## Features

- **Three selectable regions**, each with a distinct colour *and* a distinct
  hatch angle, so they read apart without relying on colour alone.
- **Bilingual labels** — English, Tibetan, or both.
- **Current borders overlay** — toggle today's TAR and provincial boundaries on
  top of the cultural regions to compare the two.
- **Towns, world locator inset, and dark/light themes**, each toggleable.
- **Proportional bar** sized by each region's share of the total area.
- **Keyboard accessible** — regions are focusable (`Tab`, then `Enter`/`Space`),
  the panel is `aria-live="polite"`, and `prefers-reduced-motion` is respected.
- **Responsive** down to phone widths via container queries.

## Configuration

Set these on the container div; they can also be changed at runtime.

```html
<div class="tibmap" id="tibet-map"
     data-theme="auto"        <!-- dark | light | auto -->
     data-labels="both"       <!-- both | en | bo -->
     data-admin="false"       <!-- true shows current provincial borders -->
     data-cities="true"       <!-- true | false -->
     data-inset="true"        <!-- world locator box -->
     data-selected="kham">    <!-- utsang | kham | amdo | "" -->
</div>
```

Colours, fonts, max width and radius are CSS custom properties
(`--tm-utsang`, `--tm-kham`, `--tm-amdo`, `--tm-gold`, `--tm-max`, …) — see
[`INTEGRATION.md`](INTEGRATION.md) for the full list.

## JavaScript API

```js
TibetMap.select('kham');        // or 'utsang', 'amdo', '' to clear
TibetMap.get();                 // 'kham' | null
TibetMap.setTheme('light');
TibetMap.on(function (region) { /* fires on every selection change */ });
TibetMap.regions;               // the descriptive copy, editable
TibetMap.data;                  // raw paths, areas, coordinates
```

Useful if you want the map to drive other content — swapping a photo,
filtering a list of monasteries, scrolling to a section.

## Fonts

The widget `@import`s three families from Google Fonts. **Noto Serif Tibetan**
is load-bearing: without it every ཆོལ་ཁ་གསུམ string renders as empty boxes on
most systems, so self-host it if you can't call Google. **Fraunces** (display)
and **IBM Plex Sans** (UI) are cosmetic — drop the `@import` and they fall back
to Georgia and your system UI font.

## About the boundaries

The regions are built by grouping present-day prefectures, then dissolving and
projecting in an Albers equal-area conic (standard parallels 26°N / 41°N,
central meridian 92°E) — which is why the area figures are measurements of the
shapes shown rather than quoted numbers.

**Areas as drawn:** Ü-Tsang 1,077,976 km² · Kham 542,279 km² ·
Amdo 563,220 km² · combined 2,183,475 km².

These are **traditional cultural regions, not administrative units.** Their
historical limits were never surveyed, shifted over time, and are drawn
differently by different sources — especially along the Gyalrong, Kongpo and
Kokonor margins. Treat the lines as indicative; the *Current borders* toggle
overlays today's boundaries for comparison.

The source prefecture data is Chinese and draws PRC claim lines, so every
region is clipped against the actual boundaries of India, Nepal, Bhutan,
Bangladesh and Myanmar: nothing administered by those states appears inside the
highlight, and the paths themselves no longer contain that ground. The
silhouette was checked against a published Tibetan cultural-area map and agrees
over 92.9% of their combined area.

[`INTEGRATION.md`](INTEGRATION.md) documents the prefecture grouping for each
region, the northern-rim closure, and the exclusions in full.
