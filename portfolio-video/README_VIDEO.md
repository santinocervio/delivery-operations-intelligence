# Delivery Operations Intelligence — case-study film

A 48.6-second case-study video and a 10-second seamless hero loop, built from
the repository's own published evidence. Both are reproducible from code: no
screenshots, no video editor, no hand-typed figures.

```
portfolio-video/
├── pedidosya/                     main film (HyperFrames project)
│   ├── BRIEF.md                   confirmed intent
│   ├── frame.md                   design truth — palette, type, motion, bans
│   ├── STORYBOARD.md              per-scene plan with blueprint/rule citations
│   ├── index.html                 thin orchestrator: 9 scene slots on one timeline
│   ├── compositions/              s1-open … s9-close, one file per scene
│   ├── src/data/*.json            frozen extracts of the published CSVs
│   ├── src/components/            VideoHero.jsx, ProjectVideo.jsx, video.css
│   ├── scripts/extract-data.py    CSV → JSON, deterministic
│   ├── scripts/verify-claims.mjs  82 assertions: every on-screen figure vs source
│   ├── assets/vendor/gsap.min.js  vendored (the render host has no CDN egress)
│   └── renders/                   local build output (git-ignored)
└── pedidosya-loop/                hero loop (separate project: one root per project)

Shipped files live in `assets/video/` at the repository root, matching the
convention of the sibling dc-fulfilment-simulation repository.
```

## Rendering

```bash
# 1. Validate, then render the master
cd portfolio-video/pedidosya
npm run check                                   # lint + runtime + layout + motion + contrast
node scripts/verify-claims.mjs                  # 82 figures vs outputs/analysis/*.csv
npx hyperframes render --format mp4 --quality high --fps 30 --output renders/master.mp4

cd ../pedidosya-loop
npx hyperframes render --format mp4 --quality high --fps 30 \
    --output renders/delivery-ops-hero-loop-master.mp4

# 2. Transcode the web deliverables with ffmpeg
#    The renderer's own WebM path produced a 13 MB file for the 10s loop, so the
#    shipped WebM and MP4 are encoded here instead, where the bitrate is controlled.
cd ../pedidosya/renders
ffmpeg -i master.mp4 -c:v libx264 -profile:v high -crf 24 -preset slow \
    -pix_fmt yuv420p -movflags +faststart -an delivery-ops-case-study.mp4
ffmpeg -i master.mp4 -c:v libvpx-vp9 -crf 34 -b:v 0 -row-mt 1 -cpu-used 3 \
    -pix_fmt yuv420p -an delivery-ops-case-study.webm

cd ../../pedidosya-loop/renders
ffmpeg -i delivery-ops-hero-loop-master.mp4 -c:v libx264 -profile:v high -crf 26 \
    -preset slow -pix_fmt yuv420p -movflags +faststart -an delivery-ops-hero-loop.mp4
ffmpeg -i delivery-ops-hero-loop-master.mp4 -c:v libvpx-vp9 -crf 36 -b:v 0 -row-mt 1 \
    -cpu-used 3 -pix_fmt yuv420p -an delivery-ops-hero-loop.webm

# 3. Posters
cd ../../pedidosya/renders
ffmpeg -ss 2.40  -i master.mp4 -frames:v 1 -q:v 3 posters/case-study-poster.jpg
ffmpeg -ss 28.60 -i master.mp4 -frames:v 1 -q:v 3 posters/case-study-thumbnail.jpg
ffmpeg -i ../../pedidosya-loop/renders/delivery-ops-hero-loop.mp4 -frames:v 1 -q:v 3 \
    posters/hero-loop-poster.jpg     # frame 0 exactly, so the loop never pops on load
```

## Shipped files

| File | Format | Duration | Size |
|---|---|---|---|
| `assets/video/delivery-operations-intelligence.mp4` | H.264 1920×1080 30 fps | 48.6 s | 2.4 MB |
| `assets/video/delivery-operations-intelligence.webm` | VP9 1920×1080 30 fps | 48.6 s | 2.3 MB |
| `assets/video/hero-loop.mp4` | H.264 1920×1080 30 fps | 10.0 s | 291 KB |
| `assets/video/hero-loop.webm` | VP9 1920×1080 30 fps | 10.0 s | 258 KB |
| `assets/video/delivery-operations-intelligence-poster.jpg` | JPEG 1920×1080 | — | 114 KB |
| `assets/video/delivery-operations-intelligence-thumbnail.jpg` | JPEG 1920×1080 | — | 121 KB |
| `assets/video/hero-loop-poster.jpg` | JPEG 1920×1080 | — | 81 KB |

The whole `renders/` directory is git-ignored — it is local build output.
Copy the finished encodes into `assets/video/` (the names in the table above)
to ship them.

Regenerate the frozen data after any re-run of the pipeline:

```bash
python3 scripts/extract-data.py && node scripts/verify-claims.mjs
```

`ffmpeg` is required by the renderer (`apt-get install -y ffmpeg`). GSAP is
vendored locally rather than loaded from a CDN so renders work offline and stay
byte-reproducible.

The HyperFrames authoring skills are **not** committed (19 MB of third-party
content). `skills-lock.json` at the repository root pins their exact versions —
restore them with `npx skills add heygen-com/hyperframes`.

## Website integration

```jsx
import VideoHero from "./portfolio-video/pedidosya/src/components/VideoHero";
import ProjectVideo from "./portfolio-video/pedidosya/src/components/ProjectVideo";

// Project card / page header
<VideoHero
  webm="/video/delivery-ops-hero-loop.webm"
  mp4="/video/delivery-ops-hero-loop.mp4"
  poster="/video/hero-loop-poster.jpg"
>
  <h2>Delivery Operations Intelligence</h2>
  <p>334,144 orders · operations diagnosis · Python</p>
</VideoHero>

// Project detail page
<ProjectVideo
  webm="/video/delivery-ops-case-study.webm"
  mp4="/video/delivery-ops-case-study.mp4"
  poster="/video/case-study-poster.jpg"
/>
```

Both components autoplay muted, loop where appropriate, use `playsInline`,
carry a poster, defer the download until the element is near the viewport via
`IntersectionObserver`, pause when scrolled away, and honour
`prefers-reduced-motion` by showing the poster with an explicit play control
instead of moving image. They are plain `.jsx` with no dependencies beyond
React — rename to `.tsx` and add prop types if the portfolio is TypeScript.

## Data and charts reused from the project

Every figure comes from an already-published aggregate table. Nothing was
recomputed for the film and nothing was invented.

| Source | Used for |
|---|---|
| `outputs/analysis/kpis.csv` | Scene 2 — orders, mean/median/P90 service, late >5 min, recorded cost per order, completed/cancelled split |
| `outputs/analysis/operational_segments.csv` (`family=hour`) | Scene 3 — all 24 hourly order counts, mean service and support flags |
| `outputs/analysis/operational_segments.csv` (`vertical_distance`) | Scene 6 — restaurant distance ladder |
| `outputs/analysis/headline_contrasts.csv` | Scenes 4 and 6 — pressure contrast, pre-event cohort, distance contrast, all bootstrap intervals |
| `outputs/analysis/threshold_assessment.csv` | Scene 4 — the rejected threshold and its exact wording |
| `outputs/analysis/threshold_discovery_bins.csv` | Scene 4 — the four non-monotonic discovery quartiles |
| `outputs/analysis/temporal_holdout.csv` | Scene 4 — the 20/10 discovery–holdout split |
| `outputs/analysis/stage_summary.csv` | Scene 5 — five stage means, P90s and time shares |
| `outputs/analysis/stage_late_contrasts.csv` | Scene 5 — the late-vs-on-time gap per stage |
| `outputs/analysis/priorities.csv` | Scene 7 — three supported priorities with triggers, cohorts, actions, trade-offs |
| `outputs/executive_findings.json` | Scenes 2, 6 — F02 cohort evidence, F04 rider-hours and throughput |
| `outputs/manifest.json` | Scenes 2, 8 — source row counts, seed, bootstrap samples |
| `delivery_ops/analysis.py` | Scene 8 — the real support-gate fragment, quoted verbatim |

The Streamlit dashboard's charts were used as a **reference for which questions
matter** (stage time, late contribution, hourly demand, distance P90), then
rebuilt as inline SVG so every mark is animatable and every value is traceable.

## Visuals recreated (not reused as images)

| Visual | Status |
|---|---|
| Hourly demand histogram + mean-service line | Rebuilt as SVG from the 24 published hourly rows. The Streamlit original is a static Plotly bar chart |
| Stage share bars (time vs late gap) | Rebuilt as SVG. New comparison — the dashboard shows the two as separate charts |
| Confidence-interval number line | **New.** No equivalent exists in the project; built to make "the interval contains zero" visible |
| Discovery-quartile bars | Rebuilt as SVG from `threshold_discovery_bins.csv` |
| Cohort proportion tracks (3.1% → 36.6%) | **New** framing of published F02 evidence |
| Distance ladder | Rebuilt as SVG from the segment table |
| Priority cards | **New** layout of `priorities.csv` rows |
| Dispatch network (scenes 1, 9, loop) | **Schematic and authored** — see below |

## Honest limits

- **No geographic data exists, so no map was drawn.** The dataset carries
  `pu_distance` and `do_distance` in assumed metres and no coordinates. The
  network graphic is an authored schematic with hard-coded constants; it
  represents order flow, not places. The only spatial claim in the film is the
  distance-**band** contrast, which is real.
- **No SQL is shown, because the project contains none.** The pipeline is
  pandas / NumPy / SciPy / statsmodels. Adding SQL to the tech beat would have
  been a fabrication.
- **No audio.** The film is silent by design so it can autoplay muted on a web
  page, and it is built to read without narration.
- **No PedidosYa logo or official typeface.** Neither exists in the repository
  and neither was recreated. The film uses a brand-adjacent palette with an
  original typographic lockup, and carries the repository's own disclaimer on
  the final frame (`docs/PUBLICATION.md`, `docs/DATA_ACCESS.md`).
- **Intervention effects are labelled as untested pilots**, mirroring the
  `confidence` and `trade_off` columns of `priorities.csv`. The film never
  claims a saving.

## Remaining manual actions

1. **Wire the two CTAs.** Scene 9 shows `LIVE CASE STUDY` and `GITHUB` as
   labels; the actual links live on the page around the video, not inside it.
2. **Copy the renders into the site's public directory** (for example
   `public/video/`) and point the components at those paths.
3. **Optional: a 720p cut.** The shipped 1080p MP4 is already 2.4 MB. If you
   want a lighter mobile variant:
   `ffmpeg -i renders/master.mp4 -vf scale=1280:720 -c:v libx264 -crf 26 -movflags +faststart -an renders/delivery-ops-case-study-720.mp4`
4. **If you want SQL on screen**, add a real SQL artefact to the repository
   first (a DuckDB view layer over the canonical tables would be honest and
   small), then scene 8's chip row can include it.
5. **Decide on the brand name.** The film says "PedidosYa" only in the closing
   disclaimer. If you would rather it not appear at all, edit the last line of
   `compositions/s9-close.html`.
