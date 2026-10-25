# Profile rendering experiment

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
