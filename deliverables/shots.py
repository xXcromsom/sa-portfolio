"""Screenshots of the running dashboard (streamlit run app.py) for the deck's demo-backup slide."""
import sys
from PIL import Image
from playwright.sync_api import sync_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8501"
TABS = {"Overview": "dash_overview.png", "AI insights": "dash_ai.png", "Risk": "dash_risk.png",
        "Portfolio": "dash_portfolio.png", "Ask the portfolio": "dash_ask.png"}

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1440, "height": 860}, device_scale_factor=2)
    page.goto(URL)
    page.get_by_role("tab", name="Overview", exact=True).wait_for(timeout=60000)
    page.wait_for_timeout(4000)
    for tab, name in TABS.items():
        page.get_by_role("tab", name=tab, exact=True).click()
        page.wait_for_timeout(2500)
        page.screenshot(path=f"assets/{name}")
        # A sidebar-free crop for small thumbnails (the appendix backup slide).
        im = Image.open(f"assets/{name}")
        im.crop((int(im.width * 0.208), int(im.height * 0.1), im.width, im.height)).save(f"assets/{name[:-4]}_crop.png")
        print("saved", name)
    browser.close()
