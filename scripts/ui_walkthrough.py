#!/usr/bin/env python3
"""
Drive the local web UI through a full run in headless Chromium and save
screenshots of every step. Used for visual QA of src/web/static.

    venv/bin/python3 -m src.cli.main web --no-browser &      # server on :8765
    venv/bin/python3 scripts/ui_walkthrough.py output/ui-shots [--iterations 3]

Needs the dev extras: `venv/bin/pip install playwright && venv/bin/playwright install chromium`.
Prints the headline numbers, the change list, any console errors, and the
phone-width scroll width (must equal the viewport width: no horizontal scroll).
"""

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("out", type=Path)
    ap.add_argument("--url", default="http://127.0.0.1:8765")
    ap.add_argument("--iterations", type=int, default=3)
    ap.add_argument("--build", type=Path, default=ROOT / "tests/fixtures/builds/cyclone_slayer.txt")
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("playwright is not installed: venv/bin/pip install playwright && venv/bin/playwright install chromium")
        return 2

    code = args.build.read_text().strip()
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
        page.on("console", lambda m: errors.append(f"console.{m.type}: {m.text}") if m.type in ("error", "warning") else None)

        page.goto(args.url, wait_until="networkidle")
        page.screenshot(path=str(args.out / "1_landing.png"), full_page=True)

        page.click("button.tab[data-tab=paste]")
        page.fill("#paste-code", code)
        page.click("#paste-form button[type=submit]")
        page.wait_for_selector("#build-card .who", timeout=30000)
        page.wait_for_selector("#step-goal:not([hidden])")
        page.screenshot(path=str(args.out / "2_build.png"), full_page=True)

        page.evaluate(f"document.querySelector('#iterations').value = {args.iterations}")
        page.click("#run")
        page.wait_for_selector("#ticker li", timeout=180000)
        page.screenshot(path=str(args.out / "3_working.png"), full_page=True)

        page.wait_for_selector("#step-result:not([hidden])", timeout=600000)
        page.wait_for_selector("#tree-wrap svg", timeout=60000)
        time.sleep(1.5)
        page.screenshot(path=str(args.out / "4_result.png"), full_page=True)
        page.locator("#hero").screenshot(path=str(args.out / "5_hero.png"))

        print("hero:", page.inner_text("#hero-num"), "|", page.inner_text("#hero-lbl"))
        print("stats:", page.inner_text("#stats").replace("\n", " / "))
        print("changes:", page.inner_text("#changes").replace("\n", " | "))
        print("note:", page.inner_text("#result-note") if page.is_visible("#result-note") else "(none)")

        page.set_viewport_size({"width": 400, "height": 800})
        time.sleep(0.5)
        page.screenshot(path=str(args.out / "6_phone.png"), full_page=True)
        width = page.evaluate("document.documentElement.scrollWidth")
        print("phone scrollWidth:", width, "(ok)" if width <= 400 else "(HORIZONTAL SCROLL)")
        browser.close()

    print("console errors:", errors or "none")
    print("screenshots in", args.out)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
