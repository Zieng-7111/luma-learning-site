# Shelf interaction regression checks

This repository contains deployment files. The active application bundle imports the readable drag logic in `assets/shelf-drag.js`, shared by the reading and writing shelves. Drag direction follows the starting half of the ring and stays fixed until release; vertical touch gestures remain available for page scrolling.

Run the logic tests from the repository root:

```sh
node --test tests/shelf-drag.test.mjs
```

For browser checks, install Python Playwright (`python -m pip install playwright` and `python -m playwright install chromium`), start `python -m http.server 4173` from the repository root, then run `python tests/shelf-browser.py` in another terminal.

The browser checks cover desktop and mobile dragging, snapping, clicks, pointer capture, keyboard/wheel controls and the horizontal rail. `python tests/shelf-browser.py --baseline` loads the original deployment bundle and is expected to fail on the bottom-half direction regression.

Run `python tests/additional-browser.py` against the same server to check continuous rail dragging, Enter to open the selected notebook, wheel events measured in lines/pages, and persistence after clearing an untitled writing draft. `python tests/additional-browser.py --baseline` replays commit `8fc46f4` and is expected to fail all four checks.
