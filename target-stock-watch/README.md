# target-stock-watch

Watches a Target product page and alerts you (beep, desktop notification, opens the page) when a buy button shows up. It does not auto-buy.

Defaults to the Nintendo Switch 2 – Zelda 40th Anniversary Edition console.

## Run

Needs Python 3.9+.

**Windows:** double-click `run.bat` (or run it from a terminal).

**macOS / Linux:**

```bash
./run.sh
```

The first run creates a virtual environment, installs dependencies, and downloads Chromium (a few minutes). After that it starts right away.

To watch a different item, pass its URL:

```bash
./run.sh "https://www.target.com/p/..."
```

## Notes

- Checks every 45–90 seconds. Don't shorten this much; Target will rate-limit you.
- A Chrome window stays open while it runs; leave it alone.
- Be signed in to Target in your normal browser with payment saved so checkout is fast.
- If it keeps reporting "no buy button" while the item is clearly in stock, Target probably changed its page markup. Update `BUY_SELECTORS` in `target_stock_watch.py`.
