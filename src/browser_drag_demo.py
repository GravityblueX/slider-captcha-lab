from pathlib import Path
from playwright.sync_api import sync_playwright
from trajectory import generate_trajectory

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / 'demo' / 'index.html'

def run(headless=False):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        page = browser.new_page(viewport={"width": 900, "height": 600})
        page.goto(DEMO.as_uri())
        knob = page.locator('#knob').bounding_box()
        slider = page.locator('#slider').bounding_box()
        start = (knob['x'] + knob['width'] / 2, knob['y'] + knob['height'] / 2)
        end = (slider['x'] + slider['width'] - 30, start[1])
        path = generate_trajectory(start, end)
        page.mouse.move(path[0].x, path[0].y)
        page.mouse.down()
        last_t = 0
        for pt in path[1:]:
            page.wait_for_timeout(max(1, int(pt.t - last_t)))
            page.mouse.move(pt.x, pt.y)
            last_t = pt.t
        page.mouse.up()
        page.wait_for_timeout(1000)
        browser.close()

if __name__ == '__main__':
    run()
