# Static profile redesign (2026-10-26)

The current README replaces the animated dashboard with one static, theme-aware
SVG lab dossier containing the member file, a data-driven contribution world-line
diagram, three current projects, and a lab equipment inventory. Both theme assets
are about **20.2 KB each**; the browser selects one. Three theme-aware navigation
controls add about **2.1 KB combined** for the selected theme. The previously displayed dark-theme panels totalled about
2.9 MiB. Legacy assets and generators remain in the repository for reference but
are not loaded by the README.

The dossier uses plain text, rectangles, circles, and a small number of paths.
There are no animations, GIFs, embedded raster images, SVG filters, scripts,
remote fonts, or third-party image services. Its divergence number is decorative,
not a live statistic. Activity numbers and projects come from a checked-in public
GitHub snapshot. An expandable Markdown transcript includes the same content,
complete project descriptions, and clickable project links; it also offers a
readable alternative to scaling the artwork on small screens.

Footer links use small static SVG controls with the dossier's palette, borders,
monospace labels, and amber registration marks. Links remain native HTML anchors;
there is no script-based interaction. The expandable transcript uses a monospace
disclosure label, terminal-record data blocks, and clickable project names.

The equipment section replaces the repetitive activity inbox. Its language counts
use the primary language of public, non-fork repositories (not proficiency or code
volume). The tools/environment list is maintained explicitly in `static_profile.py`.

Section 02 is an inset instrument plate driven by the actual contribution calendar.
Each active week is a curved world-line branch: its endpoint height encodes weekly
contributions on a shared linear scale. Branches converge into monthly bundles,
grouped by week start; months and scale ticks make the diagram readable. Zero
weeks have zero height, and the peak week is highlighted. The transcript includes
the corresponding month-bundle totals. These are GitHub contributions, not
commit-only counts. The anime informs the branching visual language, not a
decorative diagram copied from the show. Everything is static and filter-free.

The workflow checks static artwork on pushes and pull requests, and refreshes
the public snapshot and static files daily or on manual dispatch. It never
downloads GIFs or regenerates the old animated panels. Normal generation is
offline and reproducible. Image paths are relative, so previews
follow the current branch and still work after merging or deleting that branch.

## Verification

Both themes were rendered and visually inspected. Twelve local regression tests
pass, including eight static tests enforcing reproducible artwork and transcript,
a 24 KB per-theme budget, fewer than 240 SVG elements, escaping and empty-data
handling, and no runtime animation or external assets.
The inventory test also excludes private repositories and forks from counts.
Diagram tests verify weekly totals, proportional heights, monthly convergence,
zero weeks, the peak-week path, data-dependent rendering, and the payload budget
for a fully active year.
Footer tests also check reproducibility, destination links, theme variants, and
a 1.8 KB budget per navigation control.
CI runs the eight static tests with the Python standard library; the four legacy
tests still require the old renderer dependencies.

Isolated headless Chromium, 1000×1200 viewport, local HTTP assets, 3-second
warmup, then 15 seconds of measurement (CPU across the browser process group):
These measurements used the prior inbox layout, before the equipment, chart, and footer updates;
the updated artwork has the same no-animation/no-filter constraints but was not
rebenchmarked.

| Artwork | Browser CPU seconds / 15s | Average one-core CPU |
| --- | ---: | ---: |
| Previous five panels, dark | 12.56 | 83.64% |
| Static dossier, dark | 0.04 | 0.27% |
| Static dossier, light | 0.02 | 0.13% |

The harness now retains observed CPU counters for exited Chromium helper
processes, avoiding negative deltas from summing only currently live processes.
This measures artwork at rest, not the complete GitHub page, initial load time,
or every browser/device. It does not guarantee that unrelated browser freezes
are fixed. The historical results below use a different timing window.

## Build and check

```sh
python3 .github/scripts/static_profile.py
python3 -m unittest discover -s .github/scripts -p 'test_static_profile.py'
```

To fetch a new snapshot first, use `python3 .github/scripts/static_profile.py --refresh`.
An optional `GITHUB_TOKEN` raises API rate limits; no credentials are saved.
Edit layout in `static_profile.py`, not the generated README or SVGs.

Optional benchmark (requires Chromium and Python `websockets`):

```sh
TMPDIR=/tmp/opencode python3 .github/scripts/profile_performance.py \
  --panel static --warmup 3 --seconds 15 --out /tmp/opencode/static-profile.json
```

Use `--theme light` for the paper-colored version and `--panel all` for the legacy
five-panel comparison. The default benchmark target is now `static`.

---

# Historical profile rendering experiment

The measured rendering optimizations were developed on `perf/profile-performance`
and merged into `master`. Intermittent freezes were still reported after testing;
the CPU reduction does not establish their cause or guarantee they are fixed.
Further lighter-design experiments should stay on a separate branch.
The README generator chooses the current branch for image URLs, so branch
READMEs preview their own assets rather than `master`.

## Changes

- Preserve the hero dimensions, GIF footage/frame rate, world-line scrambling
  timeline, greeting/link, panel layout, and data collection logic.
- Pre-render ten transparent 2× nixie digit/glow tiles and reuse them across all
  70 digit states. Ghost cathodes and scrambling remain animated/vector-based.
- Retain the graph's vector drawing entrance; at eight seconds swap its settled
  paths and glows for a 2× transparent PNG. Its tracer remains a separate animated
  element. The old highlighted-branch shimmer is static after the swap.
- Separate the blinking terminal cursor from the large filtered text group.
- Step subtle CRT flicker, warm glow breathing, and scan bands instead of
  continuously interpolating them. Scan bands update at 12 Hz; the tracer at 15 Hz.
- Keep GIF bytes unchanged. The console's font/CSP warnings are not addressed by
  these changes.

This trades somewhat larger assets for less runtime rasterization. The hero grows
from about 2.2 MiB to 2.4 MiB, and the graph from ~38 KiB to ~440 KiB (dark).
There are no new browser scripts or third-party image services.

## Local measurements (2026-10-25)

Isolated headless Chromium, local HTTP assets, dark theme, 1000×1200 viewport,
12-second warmup, then 30 seconds including a complete 24-second meter cycle.
CPU time includes Chromium's renderer and GPU child processes. Percent is relative
to **one CPU core**, so values above 100% are possible. This is not a Firefox or
live GitHub benchmark, and no one-to-two-second stall was reproduced locally.

| Full README | Browser CPU seconds / 30s | Average one-core CPU |
| --- | ---: | ---: |
| Original, matched profile data | 49.42 | 164.7% |
| Optimized | 20.34 | 67.8% |
| Optimized repeat | 21.24 | 70.8% |

The optimized runs show a **57–59% reduction**. A separate hero-only comparison (15 seconds,
3-second warmup) was 9.07 → 4.59 CPU seconds, a 49.4% reduction. These measurements
support lower rendering cost, not a guarantee that every visitor's freeze is fixed.

Both themes were visually checked. Regression tests cover digit states in all
world-line phases, graph backdrop timing/tracer separation, branch-correct URLs,
cache invalidation and idempotence. Workflow runs the tests before committing.

## Reproduce

Normal panel generation needs `rsvg-convert` (`librsvg2-bin` on Ubuntu); the workflow
installs it. The cached digit tiles need rebuilding only when their source artwork
or rasterizer changes:

```sh
python3 .github/scripts/nixie_tiles.py
python3 .github/scripts/version_panels.py
python3 -m unittest discover -s .github/scripts -p 'test_*.py'
```

The optional benchmark also needs Chromium and Python's `websockets` package:

```sh
TMPDIR=/tmp/opencode python3 .github/scripts/profile_performance.py \
  --panel all --warmup 12 --seconds 30 --out /tmp/opencode/profile-result.json
```

Use `--root PATH` to benchmark a separate checkout's assets, `--panel hero` or
`--panel rest` to isolate costs, and `--theme light --screenshot PATH.png` for visual
checks. The harness uses a fresh temporary browser profile with extensions disabled;
it never opens the user's signed-in browser. For a fair comparison, regenerate both
checkouts from the same collected JSON before measuring.

Reduced-motion variants, further GIF compression, and a full Firefox/browser
interaction trace remain possible follow-up work; none is claimed implemented here.
