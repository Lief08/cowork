"""
Target stock watcher - polls a Target product page and alerts you when it
looks purchasable. It does NOT auto-buy; it just pings you and opens the page.

Setup (one time):
    pip install playwright plyer
    playwright install chromium

Run:
    python target_stock_watch.py            # watches the Zelda Switch 2 console by default
    python target_stock_watch.py "<any other Target product URL>"

Tips:
  - Keep the interval reasonable (default ~60s with jitter). Hammering the site
    gets you rate-limited and isn't nice.
  - The browser window runs visibly (headless browsers get blocked more often).
  - Sign in to Target in your normal browser with payment saved so checkout is fast.
"""

import random
import sys
import time
import webbrowser
from datetime import datetime

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

try:
    from plyer import notification
except ImportError:
    notification = None

DEFAULT_URL = (
    "https://www.target.com/p/nintendo-8482-switch-2-the-legend-of-zelda-"
    "40th-anniversary-edition-console-system/-/A-1013322047"
)

MIN_WAIT = 45   # seconds
MAX_WAIT = 90   # seconds

# Target's buy buttons have used these data-test values; text check is a fallback.
BUY_SELECTORS = [
    'button[data-test="shippingButton"]',
    'button[data-test="addToCartButton"]',
    'button[data-test="orderPickupButton"]',
    'button[data-test="scheduledDeliveryButton"]',
]
BUY_TEXT = ["add to cart", "ship it", "pick it up", "deliver it"]
OOS_TEXT = ["out of stock", "sold out", "not available", "temporarily out"]


def alert(url: str) -> None:
    msg = "Zelda Switch 2 may be in stock at Target!"
    print(f"\n*** {msg} ***\n{url}\n")
    print("\a" * 3, end="", flush=True)  # terminal beep
    if notification:
        try:
            notification.notify(title="IN STOCK", message=msg, timeout=30)
        except Exception:
            pass
    webbrowser.open(url)


def looks_in_stock(page) -> bool:
    for sel in BUY_SELECTORS:
        btn = page.query_selector(sel)
        if btn and btn.is_visible() and btn.is_enabled():
            return True

    # Fallback: any enabled button whose text says add/ship/pickup
    for btn in page.query_selector_all("button"):
        try:
            text = (btn.inner_text() or "").strip().lower()
        except Exception:
            continue
        if any(t in text for t in BUY_TEXT) and btn.is_enabled() and btn.is_visible():
            return True
    return False


def main() -> None:
    url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_URL
    print(f"Watching: {url}\nChecking every {MIN_WAIT}-{MAX_WAIT}s. Ctrl+C to stop.\n")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        checks = 0
        while True:
            checks += 1
            stamp = datetime.now().strftime("%H:%M:%S")
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
                page.wait_for_timeout(4000)  # let the buy box render
                body = page.inner_text("body").lower()

                if looks_in_stock(page):
                    alert(url)
                    input("Press Enter to keep watching, or Ctrl+C to quit...")
                else:
                    status = "out of stock" if any(t in body for t in OOS_TEXT) else "no buy button"
                    print(f"[{stamp}] check #{checks}: {status}")
            except PWTimeout:
                print(f"[{stamp}] check #{checks}: page timed out")
            except Exception as e:
                print(f"[{stamp}] check #{checks}: error {e}")

            time.sleep(random.uniform(MIN_WAIT, MAX_WAIT))


if __name__ == "__main__":
    main()
