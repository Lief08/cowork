"""
Target stock watcher - polls a Target product page and alerts you when it
looks purchasable. It does NOT auto-buy; it just pings you and opens the page.

Setup (one time):
    pip install playwright plyer
    playwright install chromium

Run:
    python target_stock_watch.py            # watches the Zelda Switch 2 console by default
    python target_stock_watch.py "<any other Target product URL>"

Phone alerts (ntfy):
    On first run the script creates a private topic name, saves it to
    .ntfy_topic, and prints it. Install the free ntfy app (iOS/Android),
    tap +, and subscribe to that topic. A test push is sent at startup.
    Set NTFY_TOPIC to use your own topic, or NTFY_TOPIC=off to disable.

Tips:
  - Keep the interval reasonable (default ~60s with jitter). Hammering the site
    gets you rate-limited and isn't nice.
  - The browser window runs visibly (headless browsers get blocked more often).
  - Sign in to Target in your normal browser with payment saved so checkout is fast.
"""

import os
import random
import secrets
import ssl
import sys
import urllib.request
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

TOPIC_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".ntfy_topic")
NTFY_SERVER = "https://ntfy.sh"

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
OOS_TEXT = ["out of stock", "sold out", "not available", "temporarily out",
            "isn't available", "unavailable", "coming soon"]


def get_ntfy_topic():
    env = os.environ.get("NTFY_TOPIC", "").strip()
    if env.lower() == "off":
        return None
    if env:
        return env
    try:
        with open(TOPIC_FILE) as f:
            topic = f.read().strip()
            if topic:
                return topic
    except FileNotFoundError:
        pass
    topic = "target-watch-" + secrets.token_hex(6)
    try:
        with open(TOPIC_FILE, "w") as f:
            f.write(topic)
    except OSError:
        pass
    return topic


def push(topic, title: str, message: str, url: str = "", priority: str = "default") -> bool:
    if not topic:
        return False
    headers = {"Title": title, "Priority": priority, "Tags": "video_game"}
    if url:
        headers["Click"] = url
        headers["Actions"] = f"view, Open Target, {url}"
    req = urllib.request.Request(
        f"{NTFY_SERVER}/{topic}", data=message.encode("utf-8"), headers=headers, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=10, context=_ssl_context()) as resp:
            return 200 <= resp.status < 300
    except Exception as e:
        print(f"(phone push failed: {e})")
        return False


NTFY_TOPIC = None


def _ssl_context():
    # Use certifi's up-to-date CA bundle; older Python installs on Windows can
    # fail with "certificate has expired" using the system store.
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


def alert(url: str) -> None:
    msg = "Zelda Switch 2 may be in stock at Target!"
    print(f"\n*** {msg} ***\n{url}\n")
    print("\a" * 3, end="", flush=True)  # terminal beep
    if notification:
        try:
            notification.notify(title="IN STOCK", message=msg, timeout=30)
        except Exception:
            pass
    push(NTFY_TOPIC, "IN STOCK at Target", msg + " Tap to open.", url, priority="urgent")
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
    global NTFY_TOPIC
    url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_URL
    NTFY_TOPIC = get_ntfy_topic()
    if NTFY_TOPIC:
        print("=" * 60)
        print("PHONE ALERTS: in the ntfy app, subscribe to this topic:")
        print(f"    {NTFY_TOPIC}")
        print("=" * 60)
        if push(NTFY_TOPIC, "Target watcher started",
                "Test push - you'll get an urgent alert here when it's in stock.", url):
            print("Test push sent. Check your phone.\n")
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
