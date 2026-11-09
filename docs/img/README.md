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
| `demo.gif` | 1180×720, 76 s, about 740 KB | README and LinkedIn: the judge (gpt-6-luna) on both directions, then the free tier, on the planted repository. Rendered by vhs from `docs/demo/adrcheck.tape` with a judge key in the environment, then the two model waits cut to two seconds each (recipe below); exempt from the 500 KB gate by name. The MP4 twin is rendered beside it and not committed |

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

## The demo recording

`vhs docs/demo/adrcheck.tape` writes the raw render, 98 s, with the two live judge calls waited out in
full. The README copy cuts each wait to two seconds, so a reader sees `judging ... with openai:gpt-6-luna`
and then the result; the `judged ... in 17.5 s` line that follows keeps the real wait on record. The cut
is mechanical: `ffmpeg -vf freezedetect=n=0.001:d=3` lists the still segments, a wait is a still segment
over eight seconds that ends exactly where the next still segment begins (the output arrived and the screen
went quiet again), and a reading pause is followed by typing instead. Keep two seconds of each wait,
concatenate with `trim` and `concat`, then encode the GIF at six frames a second with a 16-colour
palette, which keeps it under a megabyte:

```sh
ffmpeg -i docs/demo/adrcheck.mp4 -vf "freezedetect=n=0.001:d=3" -an -f null -   # read the segments
ffmpeg -i docs/demo/adrcheck.mp4 -filter_complex "<trim/concat of the kept ranges>" -map "[v]" -an cut.mp4
ffmpeg -i cut.mp4 -vf "fps=6,split[a][b];[a]palettegen=max_colors=16:stats_mode=diff[p];[b][p]paletteuse=dither=none:diff_mode=rectangle" docs/img/demo.gif
```
