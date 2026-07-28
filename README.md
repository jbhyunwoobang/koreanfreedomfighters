# KoreanFreedomFighters — static rebuild

**Live: <https://jbhyunwoobang.github.io/koreanfreedomfighters/>**

A hand-built static copy of [koreanfreedomfighters.com](https://www.koreanfreedomfighters.com/)
(originally on Squarespace). **All text is reproduced exactly as it appears on the
original site** — the pipeline extracts it mechanically rather than retyping it, and a
verifier proves nothing was dropped or altered.

## Run it

```bash
cd ~/kff-site && python3 -m http.server 5601
```

Then open <http://localhost:5601>. There is no build step at serve time — the `.html`
files are the deliverable. It is plain static output, so it drops onto GitHub Pages,
Netlify, Cloudflare Pages or any static host as-is.

## Layout

| Path | What it is |
| --- | --- |
| `index.html`, `about.html`, `korean-*.html`, `foreign-*.html` | the 14 generated pages |
| `styles.css` | the whole design system, one file |
| `app.js` | progressive enhancements (site works without it) |
| `assets/` | 124 images pulled down from the original |
| `data/site.json` | extracted content — the source of truth for the build |
| `tools/scrape.py` | fetches the original, extracts content + images |
| `tools/build.py` | renders the pages from `data/site.json` |
| `tools/verify.py` | asserts every extracted string/image survives into the HTML |

## Regenerating

```bash
python3 tools/build.py && python3 tools/verify.py
```

Only re-run `tools/scrape.py` when the original site changes; it caches downloaded
images in `data/assets.json`, so repeat runs re-fetch only what is new.

Editing wording is best done in `data/site.json` followed by `build.py`, so the text
stays in one place instead of being duplicated across 14 HTML files.

## What matches the original

Palette (`#e5e0da` paper, `#583b1f` brown), Open Sans 800 uppercase headings over Inter
body copy, the black hero slab, the pill outline button, the two-level
KoreanActivists / ForeignActivists nav, and the GET IN TOUCH footer with its oversized
`KOREAN / INDEPENDENT ACTIVIST` wordmark.

## What was improved

Content is untouched; these are structural, and none of them change wording.

**Structure & accessibility**
- One `<h1>` per page and a correct heading hierarchy beneath it. The original used
  `<h1>` for every activist name, so each page had dozens of them.
- Real landmarks (`header` / `main` / `nav` / `footer` / `article`), a skip link, and
  visible focus rings throughout.
- The nav is a real disclosure widget: `aria-expanded`, `aria-controls`, Escape to
  close, closes when focus leaves. Hover opens it on pointer devices, and a click then
  pins it open rather than closing what hover just opened.
- `aria-current="page"` marks the page you are on in both the bar and the dropdown.
- Decorative images use empty `alt`; portraits get a real description.

**Navigation on long pages**
- Class pages carry an "On this page" index of every activist with an instant
  name filter — `korean-2nd-class.html` has 48 entries, which is a long scroll otherwise.
- Deep links: every profile has a stable `id`, so `#gu-kim` addresses one directly.
- A back-to-top button appears after the first screen.

**Layout & performance**
- Genuinely responsive: a fluid type scale via `clamp()`, a two-column profile grid
  that collapses on narrow screens, and a mobile drawer with accordion submenus.
- Images are local (no Squarespace CDN dependency), `loading="lazy"` below the fold,
  with the hero marked `fetchpriority="high"`, and fixed aspect ratios so nothing
  reflows as they load.
- Sticky portraits and section headings while you read a long profile.
- No framework and no tracking — one stylesheet and one small script.

**Polish**
- Scroll-reveal transitions and hover states that respect `prefers-reduced-motion`.
- Print stylesheet: hides chrome, avoids splitting a profile across pages.
- Per-page `<title>`, description and Open Graph tags for link previews.
- Footer EMAIL / INSTAGRAM are working links showing the address and handle.

## Known deviations

- Per-section layout is inferred from content shape (portrait + name + dates → profile
  card; image + prose → split; lone image → banner), not copied from Squarespace's
  per-block settings, so column widths and image sizes differ slightly from the original.
- Open Sans and Inter load from Google Fonts. Self-host them in `assets/` if you want
  the site fully offline and request-free.
- Two entries on the original repeat another activist's biography verbatim
  (`Byeong-se Jo` carries `Byeong-jik Lim`'s text). That was copied as-is rather than
  corrected — it looks like a content bug worth fixing at the source.
