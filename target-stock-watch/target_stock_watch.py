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

HERE = os.path.dirname(os.path.abspath(__file__))
TOPIC_FILE = os.path.join(HERE, ".ntfy_topic")
PROFILE_DIR = os.path.join(HERE, ".browser-profile")  # keeps cookies between runs
NTFY_SERVER = "https://ntfy.sh"

MIN_WAIT = 45   # seconds
MAX_WAIT = 90   # seconds
ALERT_COOLDOWN = 300      # after an alert, wait 5 min before alerting again
CHALLENGE_BACKOFF = 240   # after a bot check, wait 4 min before reloading

# Target's buy buttons have used these data-test values; text check is a fallback.
BUY_SELECTORS = [
    'button[data-test="shippingButton"]',
    'button[data-test="addToCartButton"]',
    'button[data-test="orderPickupButton"]',
    'button[data-test="scheduledDeliveryButton"]',
]
BUY_TEXT = ["add to cart", "ship it", "pick it up", "deliver it"]
CHALLENGE_TEXT = ["press & hold", "press and hold", "confirm you are a human",
                  "verify you are a human", "access to this page has been denied"]
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


# Target often greys out buttons with aria-disabled or a CSS class instead of
# the real "disabled" attribute, so Playwright's is_enabled() isn't enough.
_REALLY_CLICKABLE_JS = """
el => {
  if (el.disabled) return false;
  if ((el.getAttribute('aria-disabled') || '').toLowerCase() === 'true') return false;
  if (/disabled/i.test(el.className || '')) return false;
  const st = getComputedStyle(el);
  if (st.pointerEvents === 'none') return false;
  if (parseFloat(st.opacity || '1') < 0.6) return false;
  const r = el.getBoundingClientRect();
  return r.width > 0 && r.height > 0;
}
"""


def _clickable(btn) -> bool:
    try:
        return bool(btn.evaluate(_REALLY_CLICKABLE_JS))
    except Exception:
        return False


def looks_in_stock(page) -> bool:
    for sel in BUY_SELECTORS:
        for btn in page.query_selector_all(sel):
            if _clickable(btn):
                return True

    # Fallback: any clickable button whose text says add/ship/pickup
    for btn in page.query_selector_all("button"):
        try:
            text = (btn.inner_text() or "").strip().lower()
        except Exception:
            continue
        if any(t in text for t in BUY_TEXT) and _clickable(btn):
            return True
    return False


def is_bot_challenge(page, body: str) -> bool:
    if any(t in body for t in CHALLENGE_TEXT):
        return True
    try:
        return page.query_selector("#px-captcha") is not None
    except Exception:
        return False


def load(page, url: str) -> str:
    page.goto(url, wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(5000)  # let the buy box render
    return page.inner_text("body").lower()


def launch(p):
    """Persistent profile so cookies (and a solved bot check) survive between
    checks and runs. Prefer the real installed Chrome; fall back to Chromium."""
    opts = dict(headless=False, viewport={"width": 1280, "height": 900})
    try:
        return p.chromium.launch_persistent_context(PROFILE_DIR, channel="chrome", **opts)
    except Exception:
        return p.chromium.launch_persistent_context(PROFILE_DIR, **opts)


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
        ctx = launch(p)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        checks = 0
        challenge_notified = False
        while True:
            checks += 1
            stamp = datetime.now().strftime("%H:%M:%S")
            wait = random.uniform(MIN_WAIT, MAX_WAIT)
            try:
                body = load(page, url)

                if is_bot_challenge(page, body):
                    print(f"[{stamp}] check #{checks}: Target is showing a bot check. "
                          "Press & hold the button in the watcher's Chrome window.")
                    if not challenge_notified:
                        push(NTFY_TOPIC, "Watcher needs you",
                             "Target is showing a 'press & hold' bot check. Solve it in the "
                             "watcher's Chrome window on your PC so checks can continue.",
                             priority="high")
                        challenge_notified = True
                    wait = CHALLENGE_BACKOFF
                elif looks_in_stock(page):
                    # Confirm with a second load so one glitchy render doesn't page you.
                    page.wait_for_timeout(3000)
                    body = load(page, url)
                    if looks_in_stock(page):
                        challenge_notified = False
                        alert(url)
                        print(f"Cooling down {ALERT_COOLDOWN // 60} min before checking again.")
                        wait = ALERT_COOLDOWN
                    else:
                        print(f"[{stamp}] check #{checks}: buy button flickered, not confirmed")
                else:
                    challenge_notified = False
                    status = "out of stock" if any(t in body for t in OOS_TEXT) else "no clickable buy button"
                    print(f"[{stamp}] check #{checks}: {status}")
            except PWTimeout:
                print(f"[{stamp}] check #{checks}: page timed out")
            except Exception as e:
                print(f"[{stamp}] check #{checks}: error {e}")

            time.sleep(wait)


if __name__ == "__main__":
    main()
