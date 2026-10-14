"""Screenshots of the running dashboard (streamlit run app.py) for the deck's demo slides.

Answers the questionnaire with the middle option everywhere (Balanced, A = 4, the report's
headline investor), then captures each tab of the terminal.
    python shots.py [url]
"""
import sys

from PIL import Image
from playwright.sync_api import sync_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8501"
TABS = {"1 PORTFOLIO": "dash_portfolio.png", "2 COMPANIES": "dash_companies.png", "3 AI": "dash_ai.png",
        "4 RISK": "dash_risk.png", "5 ASK": "dash_ask.png", "6 PROFILE": "dash_profile.png"}


def save(page, name: str, full: bool = False) -> None:
    page.screenshot(path=f"assets/{name}", full_page=full)
    im = Image.open(f"assets/{name}")
    # A tighter crop for small thumbnails (the appendix backup slide): drop the outer margins.
    im.crop((int(im.width * 0.02), 0, int(im.width * 0.98), min(im.height, int(im.width * 0.62)))).save(
        f"assets/{name[:-4]}_crop.png")
    print("saved", name)


with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1440, "height": 860}, device_scale_factor=2)
    page.goto(URL)
    page.get_by_text("BUILD MY PORTFOLIO").wait_for(timeout=90000)
    page.wait_for_timeout(2500)
    save(page, "dash_quiz.png")
    radios = page.locator('[data-testid="stRadio"]')
    for i in range(radios.count()):
        radios.nth(i).locator('[role="radiogroup"] label').nth(2).click()   # middle option: A = 4
    page.get_by_text("BUILD MY PORTFOLIO").click()
    page.get_by_text("YOUR PORTFOLIO ·").wait_for(timeout=90000)
    page.wait_for_timeout(6000)  # let the simulations finish and the faded (stale) elements clear
    for i, (tab, name) in enumerate(TABS.items()):
        if i:
            page.get_by_role("tab", name=tab, exact=True).click()
            page.wait_for_timeout(3500)
        page.evaluate("document.querySelectorAll('*').forEach(e => { if (e.scrollTop) e.scrollTop = 0; })")
        page.wait_for_timeout(500)
        save(page, name)
    # Streamlit scrolls an inner container, so a long view needs a tall viewport rather than full_page.
    page.set_viewport_size({"width": 1440, "height": 4200})
    for tab, name in (("1 PORTFOLIO", "full_portfolio.png"), ("2 COMPANIES", "full_companies.png"),
                      ("3 AI", "full_ai.png"), ("4 RISK", "full_risk.png")):
        page.get_by_role("tab", name=tab, exact=True).click()
        page.wait_for_timeout(4000)
        page.screenshot(path=f"assets/{name}")
        print("saved", name)
    browser.close()
