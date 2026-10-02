"""Browser smoke test against a local server or the published GitHub Pages URL.

Usage: .venv/bin/python tests/browser_check.py http://localhost:8000
Optional: CHROMIUM_PATH=/path/to/chrome for an existing Chromium installation.
"""
import os
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
from PIL import Image, ImageChops
from io import BytesIO

url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
out = Path(__file__).resolve().parents[1] / "test-results"
out.mkdir(exist_ok=True)

with sync_playwright() as p:
    executable = os.environ.get("CHROMIUM_PATH")
    if not executable:
        if Path(p.chromium.executable_path).exists():
            executable = p.chromium.executable_path
        else:
            candidates = sorted((Path.home() / ".cache/ms-playwright").glob("chromium-*/chrome-linux64/chrome"))
            if candidates:
                executable = str(candidates[-1])
    browser = p.chromium.launch(headless=True, executable_path=executable)
    page = browser.new_page(viewport={"width":1440,"height":1000}, reduced_motion="reduce")
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on("console", lambda message: errors.append(message.text) if message.type == "error" else None)
    response = page.goto(url, wait_until="networkidle")
    assert response.status == 200
    page.wait_for_function("document.querySelector('#manim-stage').dataset.state === 'ready'")
    expect(page.locator("#manim-stage")).to_have_attribute("data-engine", "manim-web")
    expect(page.locator("#manim-stage canvas")).to_have_count(1)
    expect(page.locator("#animate")).not_to_be_checked()
    page.evaluate("document.fonts.ready")
    narrative_font = page.locator("h1").evaluate("e => getComputedStyle(e).fontFamily")
    code_font = page.locator(".address").evaluate("e => getComputedStyle(e).fontFamily")
    assert "CMU Serif" in narrative_font, narrative_font
    assert "JetBrains Mono" in code_font, code_font
    assert page.evaluate("document.fonts.check('16px \"CMU Serif\"') && document.fonts.check('16px \"JetBrains Mono\"')")
    assert page.locator(".note-equation").evaluate_all("images => images.length === 3 && images.every(image => image.complete && image.naturalWidth > 0)")
    expect(page.locator(".chapter")).to_have_count(6)
    expect(page.locator("#metric-used")).to_have_text("9")
    expect(page.locator("#metric-blocks")).to_have_text("3 / 12")
    page.locator("#fork").click()
    expect(page.locator("#metric-shared")).to_have_text("2")
    expect(page.locator("#requests .active")).to_have_text("C")
    page.locator("#append").click()
    expect(page.locator("#event")).to_contain_text("Copy-on-write")
    expect(page.locator("#address")).to_contain_text("P5[2]")
    expect(page.locator("#metric-shared")).to_have_text("1")
    page.locator('[data-request="A"]').click()
    expect(page.locator("#request-length")).to_have_text("6 tokens · request A")
    page.locator("#release").click()
    expect(page.locator("#event")).to_contain_text("Released 1 physical block")
    page.locator("#reset").click()
    page.locator("#append").click()
    page.locator("#append").click()
    page.locator("#append").click()
    expect(page.locator("#metric-blocks")).to_have_text("4 / 12")
    expect(page.locator("#address")).to_contain_text("P5[0]")
    page.locator("#block-size").select_option("8")
    expect(page.locator("#metric-blocks")).to_have_text("2 / 12")
    page.locator("#block-size").select_option("4")
    for _ in range(60):
        page.locator("#append").click()
    expect(page.locator("#event")).to_contain_text("pool is full")
    expect(page.locator("#metric-blocks")).to_have_text("12 / 12")
    page.locator("#release").click()
    page.locator("#release").click()
    expect(page.locator("#append")).to_be_disabled()
    expect(page.locator("#metric-blocks")).to_have_text("0 / 12")
    page.locator("#reset").click()
    page.locator("#token").focus()
    page.keyboard.press("ArrowRight")
    expect(page.locator("#address")).to_contain_text("P7[1]")

    # Check real decoding and all six seek targets, not just the presence of an MP4 link.
    page.wait_for_function("document.querySelector('video').readyState >= 1")
    metadata = page.locator("video").evaluate("v => ({duration:v.duration,width:v.videoWidth,height:v.videoHeight})")
    assert metadata["duration"] > 100, metadata
    for i in range(6):
        chapter = page.locator(".chapter").nth(i)
        target = float(chapter.get_attribute("data-start"))
        chapter.click()
        page.wait_for_function("t => {const v=document.querySelector('video');return v.readyState>=2 && !v.seeking && v.currentTime>=t && v.currentTime<t+3}",arg=target)
        page.locator("video").evaluate("v => v.pause()")
        expect(chapter).to_have_class("chapter active")
    page.locator(".transcript summary").click()
    expect(page.locator("#transcript-content h3")).to_have_count(6)
    assert page.locator("#transcript-content p").count() >= 20
    page.locator(".transcript summary").click()
    page.locator("#reset").click()
    page.evaluate("scrollTo(0,0)")
    page.screenshot(path=str(out / "desktop.png"),full_page=True)
    for width in [360,390,768,1024,1440]:
        page.set_viewport_size({"width":width,"height":900})
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), f"Overflow at {width}px"
        for size in ['4','8']:
            page.locator("#block-size").select_option(size)
            page.locator("#fork").click()
            page.locator("#append").click()
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), f"Overflow at {width}px / B={size}"
    page.set_viewport_size({"width":390,"height":844})
    page.locator("#block-size").select_option("4")
    page.evaluate("scrollTo(0,0)")
    page.screenshot(path=str(out / "mobile.png"),full_page=True)

    # Exercise the actual Manim canvas and timed animation path, with motion enabled.
    page.set_viewport_size({"width":1440,"height":1000})
    page.locator("#reset").click()
    canvas = page.locator("#manim-stage canvas")
    page.wait_for_function("document.querySelector('#manim-stage canvas').clientWidth > 1000")
    bounds = canvas.bounding_box()
    canvas.click(position={"x":bounds["width"] * (0.5 - 4.2625 / 14),
                           "y":bounds["height"] * (0.5 - 2.15 / 7.8)})
    expect(page.locator("#address")).to_contain_text("P7[2]")
    canvas.click(position={"x":bounds["width"] * (0.5 + 0.95 / 14),
                           "y":bounds["height"] * (0.5 - 1.08 / 7.8)})
    expect(page.locator("#address")).to_contain_text("P2[0]")
    page.locator("#animate").check()
    page.locator("#trace").click()
    expect(page.locator("#manim-stage")).to_have_attribute("aria-busy", "true")
    expect(page.locator("#append")).to_be_disabled()
    page.wait_for_function("document.querySelector('#manim-stage').dataset.state === 'ready'")
    page.locator("#fork").click()
    page.wait_for_function("document.querySelector('#manim-stage').dataset.state === 'ready'")
    page.locator("#append").click()
    expect(page.locator("#motion-caption")).to_contain_text("Copy P2 into P5")
    expect(page.locator("#reset")).to_be_disabled()
    first = canvas.screenshot()
    page.wait_for_timeout(220)
    second = canvas.screenshot()
    difference = ImageChops.difference(Image.open(BytesIO(first)).convert("RGB"), Image.open(BytesIO(second)).convert("RGB"))
    assert difference.getbbox(), "The Manim scene did not animate during copy-on-write"
    (out / "manim-cow-moving.png").write_bytes(second)
    page.wait_for_function("document.querySelector('#manim-stage').dataset.state === 'ready'")
    expect(page.locator("#address")).to_contain_text("P5[2]")
    expect(page.locator("#metric-shared")).to_have_text("1")
    page.locator("#release").click()
    page.wait_for_function("document.querySelector('#manim-stage').dataset.state === 'ready'")
    page.locator("#reset").click()
    for _ in range(3):
        page.locator("#append").click()
        page.wait_for_function("document.querySelector('#manim-stage').dataset.state === 'ready'")
    expect(page.locator("#address")).to_contain_text("P5[0]")
    page.locator("#manim-stage").screenshot(path=str(out / "manim-desktop.png"))
    page.locator("#animate").uncheck()
    page.set_viewport_size({"width":390,"height":844})
    page.locator("#reset").click()
    page.wait_for_function("document.querySelector('#manim-stage canvas').clientWidth < 400")
    page.locator("#manim-stage").screenshot(path=str(out / "manim-mobile.png"))

    # GPU failure must leave the allocator, text view, and movie usable.
    fallback = browser.new_page()
    fallback.add_init_script("""const original = HTMLCanvasElement.prototype.getContext;
      HTMLCanvasElement.prototype.getContext = function(kind, ...args) {
        return kind.startsWith('webgl') ? null : original.call(this, kind, ...args);
      };""")
    fallback.goto(url, wait_until="networkidle")
    expect(fallback.locator("#manim-stage")).to_have_attribute("data-state", "unavailable")
    expect(fallback.locator("#memory-data")).to_have_attribute("open", "")
    fallback.locator("#fork").click()
    fallback.locator("#append").click()
    expect(fallback.locator("#address")).to_contain_text("P5[2]")
    expect(fallback.locator(".chapter")).to_have_count(6)
    fallback.close()
    assert not errors, errors
    print(f"PASS: live Manim canvas, token clicks, animated lookup/copy-on-write/allocation/release, input locking, reduced motion, GPU fallback, fonts, allocator controls, full pool, keyboard input, six video seeks, transcript, and five responsive widths. Video: {metadata}")
    browser.close()
