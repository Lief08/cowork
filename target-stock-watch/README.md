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

## Phone alerts

1. Install the free **ntfy** app (iOS or Android).
2. Start the watcher. It prints a topic name like `target-watch-1a2b3c4d5e6f` (saved in `.ntfy_topic`, reused on later runs).
3. In the app, tap **+** and subscribe to that topic. You'll get a test push right away.

When stock shows up you get an urgent push that opens the Target page when tapped. Set `NTFY_TOPIC=off` to disable, or `NTFY_TOPIC=your-topic` to pick your own name. Anyone who knows the topic name can see its messages, so keep it random.

## Notes

- Checks every 45–90 seconds. Don't shorten this much; Target will rate-limit you.
- A Chrome window stays open while it runs; leave it alone.
- Be signed in to Target in your normal browser with payment saved so checkout is fast.
- If it keeps reporting "no buy button" while the item is clearly in stock, Target probably changed its page markup. Update `BUY_SELECTORS` in `target_stock_watch.py`.
