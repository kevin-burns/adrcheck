# Images

`banner.svg` is the source of truth. Everything else is rendered from it; edit the SVG and regenerate, never
touch the raster files by hand. Every line of report text in the banner is real output from the planted
corpus (`evals/planted/build.py`, commit `36f6b01`, Haiku 5.5 via OpenRouter, 2026-11-09). It names no
version of anything.

| file | size | use |
|---|---|---|
| `banner.svg` | vector | **source.** Edit this one. |
| `banner.webp` | 2752×1536 | README and web |
| `banner.png` | 2752×1536 | blog posts and anything that will not take WebP |
| `social-preview.png` | 1280×640 | GitHub repository social preview: Settings, General, Social preview |
| `og-image.png` | 1200×630 | Open Graph and Twitter cards |
| `demo.gif` | 1180×640, 58 s | README and LinkedIn: both directions on the planted repository, free tier. Rendered by vhs from `docs/demo/adrcheck.tape`; the MP4 twin is not committed (over the 500 KB gate) and is rendered beside it |

PNG exists because WebP does not work for social cards: Open Graph scrapers and several platforms fail on
WebP silently, and a failed card renders as a blank rectangle rather than an error. GitHub wants 1280×640,
Open Graph wants 1200×630; they are different specs, not a rounding.

## Regenerating

```sh
cd docs/img
rsvg-convert -w 2752 -h 1536 banner.svg -o banner.png
magick banner.png -quality 92 banner.webp
rsvg-convert -w 1280 banner.svg -o /tmp/sp.png
magick /tmp/sp.png -gravity center -crop 1280x640+0+0 +repage -quality 92 social-preview.png
rsvg-convert -w 1200 banner.svg -o /tmp/og.png
magick /tmp/og.png -gravity center -crop 1200x630+0+0 +repage -quality 95 og-image.png
```

The crops trim the white margin, not the artwork: the SVG is 1.79:1 and both card specs are wider.
Every file stays under 500 KB; the pre-commit gate rejects anything larger.
