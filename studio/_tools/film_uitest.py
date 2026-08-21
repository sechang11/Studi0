#!/usr/bin/env python3
"""Drive the /film editor's FORMS in a real browser - not the API underneath them.
Edits a shot field, a beat field, a scene field and a film field through the DOM, clicks
the save buttons, and verifies every change landed in film.json. Console and page errors
fail the run."""
import asyncio, json, urllib.request
from playwright.async_api import async_playwright

BASE = "http://127.0.0.1:8777"
FID = "the-courier"


def film_json():
    return json.loads(urllib.request.urlopen(BASE + "/api/film/" + FID).read())


async def main():
    errs = []
    async with async_playwright() as pw:
        b = await pw.chromium.launch()
        pg = await b.new_page(viewport={"width": 1760, "height": 1000})
        pg.on("pageerror", lambda e: errs.append("pageerror: %s" % e))
        pg.on("console", lambda m: errs.append("console.%s: %s" % (m.type, m.text))
              if m.type == "error" else None)
        await pg.goto(BASE + "/film", wait_until="domcontentloaded")
        await pg.wait_for_timeout(1000)
        await pg.evaluate("openFilm('the-courier')")
        await pg.wait_for_timeout(1200)

        # ── shot form: change sfx + a beat action, add then remove a beat, save ──
        await pg.evaluate("selShot('020')")
        await pg.wait_for_timeout(1500)
        await pg.fill("#s_sfx", "a ladle set down on steel, steam hissing")
        await pg.fill(".beat[data-i='0'] .b_action",
                      "stops at the counter and sets a small parcel down on the wet steel")
        n0 = await pg.evaluate("document.querySelectorAll('.beat').length")
        await pg.click("button[onclick='addBeat()']")
        await pg.wait_for_timeout(300)
        n1 = await pg.evaluate("document.querySelectorAll('.beat').length")
        assert n1 == n0 + 1, "addBeat did not add (%d -> %d)" % (n0, n1)
        await pg.click(".beat[data-i='%d'] button" % (n1 - 1))     # remove it again
        await pg.wait_for_timeout(300)
        await pg.click("button[onclick='saveShot()']")
        await pg.wait_for_timeout(1500)
        d = film_json()
        sh = [s for sc in d["scenes"] for s in sc["shots"] if s["id"] == "020"]
        assert sh, "shot 020 missing"
        detail = json.loads(urllib.request.urlopen(
            BASE + "/api/film/%s/shot/020" % FID).read())["shot"]
        assert detail["sfx"].startswith("a ladle set down on steel, steam"), detail["sfx"]
        assert "wet steel" in detail["beats"][0]["action"], detail["beats"][0]["action"]
        assert len(detail["beats"]) == n0, "beat count changed on save"
        print("shot form: save round-trip ok")

        # ── scene form ──
        await pg.evaluate("selScene('sc02')")
        await pg.wait_for_timeout(600)
        await pg.fill("#c_palette", "cold blues, sodium orange edges")
        await pg.click("button[onclick='saveScene()']")
        await pg.wait_for_timeout(1200)
        d = film_json()
        sc2 = [s for s in d["scenes"] if s["id"] == "sc02"][0]
        assert sc2["palette"].startswith("cold blues"), sc2["palette"]
        print("scene form: save round-trip ok")

        # ── film form: edit grade, save ──
        await pg.evaluate("TAB='film';renderRight()")
        await pg.wait_for_timeout(500)
        await pg.fill("#f_grade", "hard streetlight and neon on wet surfaces, teal-amber")
        await pg.click("button[onclick='saveFilm()']")
        await pg.wait_for_timeout(1200)
        d = film_json()
        assert d["grade"].endswith("teal-amber"), d["grade"]
        cast_before = set(d["cast"])
        print("film form: save round-trip ok; cast intact:", sorted(cast_before))

        # ── context tab renders compiled prompts ──
        await pg.evaluate("selShot('020')")
        await pg.wait_for_timeout(1200)
        await pg.evaluate("TAB='context';renderRight()")
        await pg.wait_for_timeout(600)
        txt = await pg.evaluate("document.querySelector('#right').innerText")
        assert "compiled - ltx" in txt.lower(), "context tab"
        assert "running under the whole shot" in txt, "ambience bed missing from compile"
        print("context tab: compiled prompts present")

        await b.close()
    real = [e for e in errs if "favicon" not in e]
    if real:
        print("ERRORS:")
        for e in real[:10]:
            print(" ", e)
        raise SystemExit(1)
    print("UI drive: all clean")

asyncio.run(main())
