#!/usr/bin/env python3
"""Screenshot a studio page, so UI work can be looked at instead of guessed at.

    python3 studio/_tools/shot.py /                     -> /tmp/shot_home.png
    python3 studio/_tools/shot.py /styles --width 1400
    python3 studio/_tools/shot.py /wizard --dark --out /tmp/w.png
    python3 studio/_tools/shot.py /styles --click ".s" --wait 900   # open a card first
    python3 studio/_tools/shot.py /loras --console                  # report JS errors too

WHY THIS EXISTS. For most of this project nobody has ever LOOKED at these pages. Four
agents tried and failed, and their reports say so: this box has no Xvfb, and Firefox
headless dies with "RenderCompositorSWGL failed mapping default framebuffer". The result
was UI shipped blind - a LoRA page and a wizard layer band that were verified only through
DOM text and card counts, with layout, legibility and light mode entirely unseen.

The fix is a real browser: playwright's chromium-headless-shell, installed into the user
cache with pip, which needs no root and no X server.

TWO THINGS THIS TOOL DOES THAT MATTER:

  networkidle never settles on these pages, because the grids lazy-load dozens of sample
  thumbnails and the gallery holds 1828. Waiting for it times out and yields nothing, which
  is what happened on the first attempt. So this waits for the DOM plus a settling delay
  and then fires, which is what you actually want for a layout check.

  JS ERRORS ARE REPORTED. A page can look plausible in a screenshot while its console is
  full of failures - a filter that never binds, a fetch that 404s and is swallowed by a
  catch. --console prints them, and any page error is printed regardless, because a
  screenshot that hides a broken page is worse than no screenshot.
"""
import argparse, os, sys

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sys.exit("playwright is not installed. python3 -m pip install --user playwright "
             "&& python3 -m playwright install chromium")

HOST = os.environ.get("STUDIO_HOST", "127.0.0.1:8777")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("page", nargs="?", default="/")
    ap.add_argument("--host", default=HOST)
    ap.add_argument("--out")
    ap.add_argument("--width", type=int, default=1440)
    ap.add_argument("--height", type=int, default=1000)
    ap.add_argument("--full", action="store_true", default=True)
    ap.add_argument("--viewport-only", action="store_true",
                    help="just the fold, rather than the whole scroll height")
    ap.add_argument("--dark", action="store_true", help="force dark scheme")
    ap.add_argument("--light", action="store_true", help="force light scheme")
    ap.add_argument("--wait", type=int, default=1400, help="settle ms after load")
    ap.add_argument("--click", help="CSS selector to click before shooting")
    ap.add_argument("--eval", dest="js", help="JS to run before shooting")
    ap.add_argument("--console", action="store_true", help="print all console output")
    a = ap.parse_args()

    page = a.page if a.page.startswith("/") else "/" + a.page
    url = page if page.startswith("http") else "http://%s%s" % (a.host, page)
    out = a.out or ("/tmp/shot_%s.png" % (page.strip("/").replace("/", "_") or "home"))

    msgs, errors = [], []
    with sync_playwright() as p:
        b = p.chromium.launch(args=["--no-sandbox"])
        ctx = b.new_context(
            viewport={"width": a.width, "height": a.height},
            device_scale_factor=1,
            color_scheme=("dark" if a.dark else "light" if a.light else None))
        pg = ctx.new_page()
        pg.on("console", lambda m: msgs.append("%s: %s" % (m.type, m.text[:200])))
        pg.on("pageerror", lambda e: errors.append(str(e)[:300]))
        # domcontentloaded, NOT networkidle: these grids lazy-load many thumbnails and
        # networkidle simply never fires. See the module docstring.
        pg.goto(url, wait_until="domcontentloaded", timeout=45000)
        pg.wait_for_timeout(a.wait)
        if a.click:
            try:
                pg.click(a.click, timeout=6000)
                pg.wait_for_timeout(700)
            except Exception as e:
                print("  click %r failed: %s" % (a.click, str(e)[:120]))
        if a.js:
            try:
                pg.evaluate(a.js)
                pg.wait_for_timeout(600)
            except Exception as e:
                print("  eval failed: %s" % str(e)[:150])
        pg.screenshot(path=out, full_page=not a.viewport_only)
        h = pg.evaluate("document.documentElement.scrollHeight")
        b.close()

    print("%s  (%.0f KB, page height %spx)" % (out, os.path.getsize(out) / 1024.0, h))

    # A clean-looking screenshot of a page whose console is on fire is a trap.
    bad = [m for m in msgs if m.startswith("error")]
    if errors or bad:
        print("  JS PROBLEMS - the screenshot may look fine and the page still be broken:")
        for e in errors[:6]:
            print("    pageerror: %s" % e)
        for m in bad[:6]:
            print("    %s" % m)
    else:
        print("  no JS errors")
    if a.console:
        for m in msgs[:40]:
            print("    %s" % m)


if __name__ == "__main__":
    main()
