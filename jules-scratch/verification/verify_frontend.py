from playwright.sync_api import sync_playwright

def run(playwright):
    browser = playwright.chromium.launch()
    page = browser.new_page()
    page.goto("http://127.0.0.1:8000")
    # Wait for the assets list to be populated, indicating the initial_data call has finished
    page.wait_for_selector('#assetsList:not(:empty)')
    page.screenshot(path="jules-scratch/verification/screenshot.png")
    browser.close()

with sync_playwright() as playwright:
    run(playwright)
