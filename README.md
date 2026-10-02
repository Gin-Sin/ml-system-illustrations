# ML Systems, Illustrated

Original Manim animations and interactive explanations of machine learning systems, by Gin-Sin.

**Watch and explore: https://gin-sin.github.io/ml-system-illustrations/**

## Visual note 001: PagedAttention

A six-chapter, silent, captioned visual essay inspired by 3Blue1Brown’s geometric teaching approach. This is an independent project with original scenes, not an official 3Blue1Brown production.

1. Why the KV cache grows during autoregressive decoding.
2. Reserving a maximum context versus allocating fixed-size blocks on demand.
3. Translating a logical token index through a block table.
4. Computing attention over noncontiguous physical blocks with a shared softmax normalization.
5. Appending tokens, allocating at block boundaries, and releasing unshared blocks.
6. Sharing prefix blocks and copying a shared partial block before writing.

The web page includes chapter navigation, a searchable browser-native text transcript, downloadable MP4, WebVTT captions, and a responsive allocator playground. Fork a request and append to see reference counting and copy-on-write. A four-token block is chosen for legibility, not as a production recommendation. The playground also supports eight-token blocks.

The interactive diagram uses **[manim-web](https://github.com/maloyan/manim-web) 0.3.24**, a community TypeScript implementation of Manim's scene and animation model. `Scene`, `VGroup`, `Rectangle`, `Text`, `Clickable`, `Shift`, `Indicate`, and `FadeOut` render and animate live objects in the browser. Click a token, trace its address, or append to a fork: the shared tail is copied, the table is redirected, and the new KV entry arrives at its destination. These are live animations driven by the allocator state, not video clips.

The film and exported equation SVGs use **Python Manim Community**. The playground uses the **browser port**, not a running Python Manim interpreter. `docs/allocator.js` supplies the allocation rules; HTML controls provide keyboard access and a matching text view. All runtime assets are hosted on this site, with no rendering server or CDN dependency. WebGL is required for the animated view; the text view remains interactive when WebGL is unavailable. Reduced-motion preferences disable transitions by default.

## Reproduce the animation

Python 3.12, Manim Community 0.19.0, FFmpeg, Cairo, Pango, LaTeX, and dvisvgm are used. No GPU is needed. On Ubuntu/Debian:

```sh
sudo apt-get update
sudo apt-get install -y python3-venv python3-dev build-essential pkg-config libcairo2-dev libpango1.0-dev ffmpeg texlive-latex-base texlive-latex-extra texlive-fonts-recommended dvisvgm fonts-cmu fonts-jetbrains-mono fonts-lato
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python scripts/render.py
```

The default render is **1920 × 1080 at 60 fps**. The script renders six scenes, combines them into a browser-compatible H.264 MP4, and derives the chapter times, captions, transcript, and poster from the render. Captions also appear within the animation, so it works without audio or enabled subtitle tracks.

The visual system uses **CMU Serif** for narration, **JetBrains Mono** for code and physical addresses, and real **Computer Modern LaTeX** for mathematics. Serif labels, symbolic vectors, memory strips, restrained brackets, and data-linked highlights replace the original rounded-card diagrams. The website embeds the fonts locally and uses LaTeX SVGs for its takeaway equations. Font redistribution notices are included in `docs/assets/fonts/`.

Visual references: [3Blue1Brown’s attention lesson and video frames](https://www.3blue1brown.com/lessons/attention/) and [its original Manim source](https://github.com/3b1b/videos/blob/master/_2024/transformers/attention.py). Reference artwork is not bundled into this project.

```sh
# Fast visual draft, or assemble already-rendered chapters:
.venv/bin/python scripts/render.py --quality l
.venv/bin/python scripts/render.py --assemble-only
# Extract the authored visual review moments:
.venv/bin/python scripts/review_frames.py
```

`--quality l` overwrites the published assets with a draft; run the default render again before publishing. The checked-in MP4 lets GitHub Pages deploy without installing Manim in CI.

## Develop the site

```sh
npm ci
npm run build
python3 scripts/serve.py
# Open http://localhost:8000
npm test
```

Node 22 builds `web/playground.js` into a local browser bundle using esbuild. Dependency versions are locked in `package-lock.json`; bundled license notices live in `docs/assets/playground/LICENSES.txt`. Run `npm run build` after editing the scene. The generated bundle is checked in for immediate local previews and rebuilt during deployment.

The preview server supports HTTP byte ranges so chapter seeking works before the full video downloads. GitHub Pages supports these natively. The allocator tests cover physical address translation, partial-block copy-on-write isolation, shared full blocks, reference-counted release, atomic allocation failure, and 2,400 deterministic mixed operations across two block sizes. Browser checks exercise the actual canvas, token clicks, changing animation frames, action locking, allocation/release, reduced motion, WebGL fallback, responsive layouts, and movie playback.

Optional browser checks (uses Playwright Chromium):

```sh
.venv/bin/pip install playwright
.venv/bin/playwright install chromium
.venv/bin/python tests/browser_check.py http://localhost:8000
```

Push to `main` to run the tests and publish `docs/` through the GitHub Pages workflow. Repository Settings → Pages → Source must be **GitHub Actions**.

## Scope and accuracy

The allocator is a teaching model, not a vLLM implementation. One cell stands for the KV vectors associated with a token; real tensor layouts include layers, KV heads, and head dimensions. Memory pages here are GPU KV-cache blocks, not necessarily hardware virtual-memory pages.

The attention chapter shows the mathematical result. Token vectors are columns, so the introductory equation is $\mathbf{o}_t = V_{\leq t}\operatorname{softmax}(K_{\leq t}^{\mathsf T}\mathbf{q}_t/\sqrt{d_k})$; this is equivalent to the usual row-vector convention. The numerical scores in chapter four are illustrative, and their probabilities are computed with an actual softmax. Displayed values are rounded. Real kernels can fuse operations or combine partition statistics; they do not need to materialize the complete score vector shown in the diagram. The normalization covers the request’s valid causal context, not each physical block independently.

The reservation example compares a simplified 12-slot-per-request policy with block allocation. It is not a benchmark. Blocks avoid external fragmentation within a uniform pool, but the final block can still have unused slots. Larger blocks trade allocation granularity for other implementation costs; the playground does not model throughput, eviction, retained prefix caches, scheduling, or device transfer. Copy-on-write is illustrated with forked continuations; production prefix-caching policies vary.

## Sources

- [Kwon et al., Efficient Memory Management for Large Language Model Serving with PagedAttention (SOSP 2023)](https://arxiv.org/abs/2309.06180)
- [vLLM: PagedAttention kernel design](https://docs.vllm.ai/en/latest/design/paged_attention/)
- [vLLM introduction: blocks, sharing, and copy-on-write](https://vllm.ai/blog/2023-06-20-vllm)
- [Manim Community documentation](https://docs.manim.community/)

## Layout

```text
scenes/paged_attention.py   Six original Manim scene classes
web/playground.js          Live manim-web scene and action animations
scripts/build_web.mjs      Browser bundling and dependency notices
scripts/render.py          Video assembly and timed web assets
scripts/serve.py           Local preview with video byte-range support
scripts/build_typography.py Font bundling and LaTeX SVG generation
scripts/review_frames.py   Authored frame extraction for visual QA
docs/                      Self-contained GitHub Pages site
docs/allocator.js          Deterministic KV block allocator
docs/assets/               Rendered film, poster, captions, metadata
docs/assets/playground/    Self-hosted browser animation runtime
tests/                     Model invariants and browser checks
.github/workflows/          Validation and Pages deployment
```
