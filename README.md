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

## Reproduce the animation

Python 3.12, Manim Community 0.19.0, FFmpeg, Cairo, Pango, and DejaVu fonts are used. No GPU or LaTeX is needed. On Ubuntu/Debian:

```sh
sudo apt-get update
sudo apt-get install -y python3-venv python3-dev build-essential pkg-config libcairo2-dev libpango1.0-dev ffmpeg fonts-dejavu-core
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python scripts/render.py
```

The default render is **1920 × 1080 at 30 fps**. The script renders six scenes, combines them into a browser-compatible H.264 MP4, and derives the chapter times, captions, transcript, and poster from the render. Captions also appear within the animation, so it works without audio or enabled subtitle tracks.

```sh
# Fast visual draft, or assemble already-rendered chapters:
.venv/bin/python scripts/render.py --quality l
.venv/bin/python scripts/render.py --assemble-only
```

`--quality l` overwrites the published assets with a draft; run the default render again before publishing. The checked-in MP4 lets GitHub Pages deploy without installing Manim in CI.

## Develop the site

```sh
python3 scripts/serve.py
# Open http://localhost:8000
npm test
```

No frontend build step or runtime dependencies. The preview server supports HTTP byte ranges so chapter seeking works before the full video downloads. GitHub Pages supports these natively. The allocator tests cover physical address translation, partial-block copy-on-write isolation, shared full blocks, reference-counted release, atomic allocation failure, and 2,400 deterministic mixed operations across two block sizes.

Optional browser checks (uses Playwright Chromium):

```sh
.venv/bin/pip install playwright
.venv/bin/playwright install chromium
.venv/bin/python tests/browser_check.py http://localhost:8000
```

Push to `main` to run the tests and publish `docs/` through the GitHub Pages workflow. Repository Settings → Pages → Source must be **GitHub Actions**.

## Scope and accuracy

The allocator is a teaching model, not a vLLM implementation. One cell stands for the KV vectors associated with a token; real tensor layouts include layers, KV heads, and head dimensions. Memory pages here are GPU KV-cache blocks, not necessarily hardware virtual-memory pages.

The attention chapter shows the mathematical result. Real kernels can fuse operations or combine partition statistics; they do not need to materialize the complete score vector shown in the diagram. The normalization covers the request’s valid causal context, not each physical block independently.

The reservation example compares a simplified 12-slot-per-request policy with block allocation. It is not a benchmark. Blocks avoid external fragmentation within a uniform pool, but the final block can still have unused slots. Larger blocks trade allocation granularity for other implementation costs; the playground does not model throughput, eviction, retained prefix caches, scheduling, or device transfer. Copy-on-write is illustrated with forked continuations; production prefix-caching policies vary.

## Sources

- [Kwon et al., Efficient Memory Management for Large Language Model Serving with PagedAttention (SOSP 2023)](https://arxiv.org/abs/2309.06180)
- [vLLM: PagedAttention kernel design](https://docs.vllm.ai/en/latest/design/paged_attention/)
- [vLLM introduction: blocks, sharing, and copy-on-write](https://vllm.ai/blog/2023-06-20-vllm)
- [Manim Community documentation](https://docs.manim.community/)

## Layout

```text
scenes/paged_attention.py   Six original Manim scene classes
scripts/render.py          Video assembly and timed web assets
scripts/serve.py           Local preview with video byte-range support
docs/                      Self-contained GitHub Pages site
docs/allocator.js          Deterministic KV block allocator
docs/assets/               Rendered film, poster, captions, metadata
tests/                     Model invariants and browser checks
.github/workflows/          Validation and Pages deployment
```
