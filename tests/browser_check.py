"""Browser smoke test against a local server or the published GitHub Pages URL.

Usage: .venv/bin/python tests/browser_check.py http://localhost:8000
Optional: CHROMIUM_PATH=/path/to/chrome for an existing Chromium installation.
"""
import os
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

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
    response = page.goto(url, wait_until="networkidle")
    assert response.status == 200
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
    assert not errors, errors
    print(f"PASS: allocator controls, full-pool handling, keyboard input, six video seeks, transcript, and five responsive widths. Video: {metadata}")
    browser.close()
