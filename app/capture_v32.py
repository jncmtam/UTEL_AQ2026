"""Screenshots of the V3.2 product flow for the deck, report and guide (Playwright + installed Chrome).

    python app/capture_v32.py https://data1--agqo-v32.us-east.modal.run docs/prototype_shots/v32

Shots: the pitch preset waiting for confirmation, the confirmed form, the result (live Modal run), a
clarification question, an infeasible request, and the lot-cost chart. Interface copy stays Vietnamese.
"""

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else "https://data1--agqo-v32.us-east.modal.run"
OUT = Path(sys.argv[2] if len(sys.argv) > 2 else "docs/prototype_shots/v32")
OUT.mkdir(parents=True, exist_ok=True)
SETTLE = ("document.querySelectorAll('.reveal').forEach(e=>{e.style.transition='none';e.classList.add('in')});"
          "document.querySelector('.topbar').style.position='static';")


def shot(page, selector, name, pad=0):
    el = page.locator(selector).first
    el.scroll_into_view_if_needed()
    page.wait_for_timeout(1200)
    el.screenshot(path=str(OUT / f"{name}.png"))
    print("saved", name)


with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome")
    page = b.new_page(viewport={"width": 1440, "height": 1000}, device_scale_factor=2)
    page.goto(URL + "/?live=0")
    page.wait_for_selector("body[data-done='1']", state="attached", timeout=90000)
    page.evaluate(SETTLE)
    shot(page, "#problem .card", "lot_cost_chart")
    page.evaluate("choosePreset('pitch20')")
    page.wait_for_timeout(2500)
    shot(page, "#constraintCard", "pitch_constraints_pending")
    page.evaluate("document.querySelector('#confirmBtn').click()")
    shot(page, "#constraintCard", "pitch_constraints_confirmed")
    page.evaluate("runClicked()")
    page.wait_for_function("document.querySelector('#execLabel').innerText.length > 0", timeout=120000)
    page.wait_for_timeout(1500)
    shot(page, "#p7", "pitch_result")
    shot(page, "#resKpis", "pitch_kpis")
    page.evaluate("choosePreset('vague_bank')")
    page.wait_for_timeout(2500)
    shot(page, "#try .card.form:nth-of-type(2)", "clarification")
    page.evaluate("choosePreset('cap2_20'); runClicked()")
    page.wait_for_function("document.querySelector('#infeasible').innerText.length > 0", timeout=120000)
    page.wait_for_timeout(1200)
    shot(page, "#infeasible", "infeasible")
    b.close()
