# Chöl-kha-sum map — integration guide

Three files, no build step, no dependencies beyond an optional webfont request.

| File | What it is |
|---|---|
| `tibet-three-regions-map.html` | The interactive widget. Open directly or embed. |
| `tibet-three-regions-dark.svg` | Static map, dark. Use in `<img>`, a CMS, or print. |
| `tibet-three-regions-light.svg` | Static map, light. |

The static SVGs carry Latin labels only. An SVG loaded through `<img>` can't
fetch a webfont, and most systems have no Tibetan font, so the script would
render as empty boxes. The interactive version shows both.

---

## Option 1 — iframe (fastest)

Drop the HTML file anywhere on your server and point an iframe at it.

```html
<iframe src="/maps/tibet-three-regions-map.html"
        style="width:100%;height:1050px;border:0"
        loading="lazy"
        title="The three regions of Tibet"></iframe>
```

Fully isolated from your site's CSS. The only cost is that you have to guess a
height. To make it self-sizing, add this to your page:

```html
<script>
window.addEventListener('message', function (e) {
  if (e.data && e.data.tibmapHeight) {
    document.querySelector('iframe[src*="tibet-three-regions"]')
            .style.height = e.data.tibmapHeight + 'px';
  }
});
</script>
```

…and this just before `</body>` inside the map file:

```html
<script>
new ResizeObserver(function () {
  parent.postMessage({ tibmapHeight: document.body.scrollHeight }, '*');
}).observe(document.body);
</script>
```

## Option 2 — inline (better, if you control the page)

Open `tibet-three-regions-map.html` and copy everything between

```
<!-- ══════════ COPY FROM HERE ══════════ -->
...
<!-- ══════════ COPY TO HERE ══════════ -->
```

Paste it into your page. That block contains the container div, the `<style>`,
and the `<script>` — nothing else is needed. Every selector is scoped to
`.tibmap` and every SVG class is prefixed `tm-`, so it will not collide with
your stylesheet. The widget fills its parent's width up to `--tm-max` (1180px).

## Option 3 — static image

```html
<picture>
  <source srcset="/maps/tibet-three-regions-dark.svg"
          media="(prefers-color-scheme: dark)">
  <img src="/maps/tibet-three-regions-light.svg"
       alt="The three traditional regions of Tibet: Ü-Tsang, Kham and Amdo"
       style="width:100%;height:auto">
</picture>
```

---

## Configuration

Set these on the container div. They can also be changed at runtime.

```html
<div class="tibmap" id="tibet-map"
     data-theme="auto"        <!-- dark | light | auto -->
     data-labels="both"       <!-- both | en | bo -->
     data-admin="false"       <!-- true shows current provincial borders -->
     data-cities="true"       <!-- true | false -->
     data-inset="true"        <!-- world locator box, bottom-left of the map -->
     data-rivers="false"      <!-- true draws the rivers, lakes and their names -->
     data-ranges="false"      <!-- true draws the range crests, peaks and names -->
     data-selected="kham">    <!-- utsang | kham | amdo | "" -->
</div>
```

`data-theme="auto"` follows the visitor's `prefers-color-scheme`.

## Restyling

Override the custom properties anywhere after the widget's `<style>`:

```css
#tibet-map {
  --tm-utsang: #8E2F3C;
  --tm-kham:   #26596F;
  --tm-amdo:   #35745A;
  --tm-gold:   #C9A227;
  --tm-max:    980px;         /* max width */
  --tm-radius: 10px;
  --tm-display: 'Your Display Face', Georgia, serif;
  --tm-ui:      'Your UI Face', system-ui, sans-serif;
}
```

Full list: `--tm-utsang --tm-kham --tm-amdo --tm-gold --tm-bg --tm-land
--tm-land-2 --tm-hair --tm-ink --tm-ink-dim --tm-rule --tm-panel --tm-display
--tm-ui --tm-bo --tm-radius --tm-max`.

## JavaScript API

```js
TibetMap.select('kham');        // or 'utsang', 'amdo', '' to clear
TibetMap.get();                 // 'kham' | null
TibetMap.setTheme('light');
TibetMap.on(function (region) { // fires on every selection change
  console.log('selected:', region);
});
TibetMap.regions;               // the descriptive copy, editable
TibetMap.data;                  // raw paths, areas, coordinates
```

Useful if you want the map to drive other content — swapping a photo,
filtering a list of monasteries, scrolling to a section.

## Fonts

The widget `@import`s three families from Google Fonts:

- **Noto Serif Tibetan** — load-bearing. Most systems have no Tibetan font,
  and without it every ཆོལ་ཁ་གསུམ string renders as empty boxes. Self-host
  this one if you can't call Google.
- **Fraunces** (display) and **IBM Plex Sans** (UI) — cosmetic. Delete the
  `@import` line and they fall back to Georgia and your system UI font.

To self-host, remove the `@import` and point `--tm-bo` at your own `@font-face`.

## Accessibility

Regions are keyboard-focusable (`Tab`, then `Enter`/`Space`). The panel is
`aria-live="polite"`. Each region also carries a distinct hatch angle, so the
three read apart without relying on colour. `prefers-reduced-motion` is
respected.

---

## Where the boundaries come from

Built by grouping present-day prefectures, then dissolving and projecting in an
Albers equal-area conic (standard parallels 26°N / 41°N, central meridian 92°E),
which is why the area figures in the panel are measurements of the shapes shown
rather than quoted numbers.

- **Ü-Tsang** — Lhasa, Shigatse, Nyingtri, Lhoka, Nagchu, Ngari, plus the
  Tanggula/Changthang exclave administered from Golmud.
- **Kham** — Chamdo, Garzê, Yushu, Dêqên, Muli, and the Gyalrong counties of
  Ngawa (Barkham, Chuchen, Tsanlha, Li, Trochu, Mowun, Wenchuan).
- **Amdo** — Xining, Haidong, Haibei, Malho, Tsolho, Golog, Tsonub, Kanlho, and
  northern Ngawa (Ngawa, Dzoge, Marthang, Dzamthang, Zungchu, Zitsa Degu).

**Internationally recognised boundaries only.** Every region is clipped against
the boundaries of India, Nepal, Bhutan, Bangladesh and Myanmar, so nothing
administered by those states appears inside the highlight. The southern edge
follows the Himalayan frontier and the western edge stops short of Ladakh and
Jammu & Kashmir. This is done in the build step, not in CSS — the paths
themselves no longer contain that ground.

In the west the line is checked against Natural Earth 10m, which draws
boundaries as they are administered on the ground. That check moved the
Demchok salient — about 4,600 km² east of Ladakh that the source data placed
inside Ü-Tsang — back onto the Indian side, and the Ü-Tsang figure below
reflects the smaller shape.

The same rule applies to the **Current borders** overlay. Its dashed lines are
clipped to the same footprint, so no dashed boundary runs through territory
administered by India, Nepal, Bhutan, Bangladesh or Myanmar; where a provincial
line meets one of those states it is carried along the internationally
recognised boundary instead.

**These are traditional cultural regions, not administrative units.** Their
historical limits were never surveyed, shifted over time, and are drawn
differently by different sources — especially along the Gyalrong, Kongpo and
Kokonor margins. Treat the lines as indicative. The **Current borders** toggle
overlays today's TAR and provincial boundaries so a reader can compare.

**Northern rim.** The Changthang and Hoh Xil continue north of the Tibetan
prefectures into Xinjiang and Gansu, so grouping prefectures alone leaves
notches along that edge that no published cultural-area map draws. The northern
boundary is therefore closed to follow the continuous landform. Everywhere else
the outline is the prefecture mosaic as-is.

**Checked against a reference.** The silhouette was compared with a published
Tibetan cultural-area map by extracting that map's outline and fitting the two
together: they agree over 92.9% of their combined area. The residual differences
are the fringe of a few tens of kilometres, plus Arunachal Pradesh, which lies
outside this map by design.

**Areas as drawn:** Ü-Tsang 1,073,363 km² · Kham 542,279 km² ·
Amdo 563,220 km² · combined 2,178,862 km².
