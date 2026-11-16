"""Capture the prototype's panels as PNG images (used in the slides, the report and the guide).

    uvicorn app.server:api --port 8765 &        # or any deployed URL
    python app/capture.py http://localhost:8765 docs/prototype_shots

Uses the locally installed Google Chrome through Playwright (no browser download).
"""

import sys
import urllib.parse
from pathlib import Path

from playwright.sync_api import sync_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8765"
OUT = Path(sys.argv[2] if len(sys.argv) > 2 else "docs/prototype_shots")
OUT.mkdir(parents=True, exist_ok=True)
Q = "Không mua VIC, VHM, VRE vì tôi đã có nhiều cổ phiếu nhóm này"


def shoot(page, selector: str, name: str) -> None:
    el = page.locator(selector).first
    el.scroll_into_view_if_needed()
    page.wait_for_timeout(1600)                       # let ECharts animations finish
    el.screenshot(path=str(OUT / f"{name}.png"))
    print("saved", name)


with sync_playwright() as p:
    browser = p.chromium.launch(channel="chrome")
    page = browser.new_page(viewport={"width": 1440, "height": 900}, device_scale_factor=2)
    page.goto(URL + "/")
    page.wait_for_timeout(2500)
    page.screenshot(path=str(OUT / "00_hero.png"))
    print("saved 00_hero")
    shoot(page, "#problem .card", "01_lot_slider")
    page.goto(URL + "/?run=1&live=0&capital=20&q=" + urllib.parse.quote(Q))
    page.wait_for_selector("body[data-done='1']", state="attached", timeout=60000)
    page.add_style_tag(content=".topbar{position:static!important}")    # keep the sticky bar out of panel shots
    for i, name in enumerate(["mandate", "market", "hamiltonian", "ai_design", "circuit", "sampling", "portfolio"], 1):
        shoot(page, f"#p{i}", f"p{i}_{name}")
    shoot(page, "#try .form", "form")
    shoot(page, "#stepper", "stepper")
    shoot(page, "#inside", "inside")
    shoot(page, "#results", "results")
    shoot(page, "#honest", "honest")
    browser.close()
