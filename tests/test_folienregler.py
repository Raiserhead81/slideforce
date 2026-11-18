"""Folien-Regler (min/max): Premium-KI-Plan + statische Verteilung + Web-Test.

Aufruf: .venv/bin/python tests/test_folienregler.py [--quick]
Braucht fuer a/b/d-ai die GLM-Bridge (web/ai-config.json), sonst SKIP.
--quick = nur c/d (statisch + Web ohne KI).
"""
import json
import subprocess
import sys
import time
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

from pptx import Presentation  # noqa: E402
from slideforce.readers import read_content  # noqa: E402
from slideforce.ai_design import (build_ai_deck, load_ai_config,  # noqa: E402
                                  struktur_slide_plan)
from slideforce.profiles import build_vorlage  # noqa: E402
from web.app import _verteile_folien  # noqa: E402

SRC = Path("/tmp/normales-transkript.txt").read_text(encoding="utf-8")
LANG = (SRC + "\n\n") * 12
KURZ = SRC
CFG = load_ai_config()
QUICK = "--quick" in sys.argv


def _write(name, text):
    p = Path("/tmp") / name
    p.write_text(text, encoding="utf-8")
    return p


def _reopen_ok(path, erwartet):
    r = subprocess.run(["unzip", "-t", str(path)], capture_output=True, text=True)
    assert r.returncode == 0 and "No errors" in r.stdout, f"unzip -t fehlgeschlagen: {r.stdout}"
    prs = Presentation(str(path))
    assert len(prs.slides) == erwartet, f"reopen: {len(prs.slides)} != {erwartet}"
    return len(prs.slides)


def test_a_premium_max10():
    if QUICK or not CFG:
        print("a) SKIP (keine KI / --quick)"); return
    t0 = time.time()
    cp = _write("lang12.md", LANG)
    slides = read_content(cp, source_title="lang12")
    print(f"a) Reader-Folien (12x-Transkript): {len(slides)}")
    # Beispiel-Plan separat (Beweis-Ausgabe):
    plan = struktur_slide_plan(LANG, None, 10, CFG)
    assert plan, "struktur_slide_plan lieferte None"
    print("a) PLAN (gekuerzt, Folie 1-2):")
    print(json.dumps(plan[:2], ensure_ascii=False, indent=2)[:1200])
    out, stats = build_ai_deck(slides, "/tmp/rl-a.pptx", config=CFG,
                               ziel_max=10, content_text=LANG)
    print(f"a) build_ai_deck: {stats} ({time.time() - t0:.0f}s)")
    assert stats["folien"] <= 10, f"maxfolien=10 verletzt: {stats['folien']}"
    n = _reopen_ok(out, stats["folien"])
    print(f"a) OK: Premium-Deck <= 10 Folien (X-Deck-Folien = {stats['folien']}, reopen = {n})")


def test_b_premium_min6():
    if QUICK or not CFG:
        print("b) SKIP (keine KI / --quick)"); return
    cp = _write("kurz.md", KURZ)
    slides = read_content(cp, source_title="kurz")
    print(f"b) Reader-Folien (kurzes Transkript): {len(slides)}")
    out, stats = build_ai_deck(slides, "/tmp/rl-b.pptx", config=CFG,
                               ziel_min=6, ziel_max=10, content_text=KURZ)
    print(f"b) build_ai_deck: {stats}")
    assert stats["folien"] >= 6, f"minfolien=6 verletzt: {stats['folien']}"
    _reopen_ok(out, stats["folien"])
    print(f"b) OK: Premium-Deck >= 6 Folien ({stats['folien']})")


def test_c_vorpptx_max5():
    cp = _write("lang12.md", LANG)
    slides = read_content(cp, source_title="lang12")
    print(f"c) Reader-Folien: {len(slides)}")
    slides = _verteile_folien(slides, 5)
    assert len(slides) <= 5, f"maxfolien=5 verletzt: {len(slides)}"
    out = Path("/tmp/rl-c.pptx")
    build_vorlage(slides, out)
    n = _reopen_ok(out, len(slides))
    print(f"c) OK: vorpptx {n} Folien (<= 5), unzip+reopen sauber")


def test_d_web():
    from web.app import app, TOKEN
    c = app.test_client()
    r = c.get("/", query_string={"token": TOKEN})
    assert r.status_code in (200, 302), f"login fehlgeschlagen: {r.status_code}"
    # d1: vorpptx maxfolien=5 auf 12x-Text
    r = c.post("/api/build", data={"text": LANG, "fmt": "vorpptx", "maxfolien": "5"})
    assert r.status_code == 200, f"build fehlgeschlagen: {r.status_code} {r.data[:200]}"
    n = int(r.headers["X-Deck-Folien"])
    print(f"d1) vorpptx maxfolien=5 via test_client: X-Deck-Folien = {n}")
    assert n <= 5, f"maxfolien=5 verletzt: {n}"
    # d2: min nicht erreichbar -> X-Warnung
    r = c.post("/api/build", data={"text": KURZ, "fmt": "b28pptx", "minfolien": "20"})
    assert r.status_code == 200
    warn = r.headers.get("X-Warnung")
    print(f"d2) b28pptx minfolien=20: X-Deck-Folien = {r.headers['X-Deck-Folien']}, "
          f"X-Warnung = {warn!r}")
    assert warn and "Premium" in warn, "X-Warnung fehlt"
    # d3: ungueltige Werte = None (normal gebaut)
    r = c.post("/api/build", data={"text": KURZ, "fmt": "b28pptx",
                                   "minfolien": "0", "maxfolien": "abc"})
    assert r.status_code == 200 and "X-Warnung" not in r.headers
    print(f"d3) ungueltige Grenzen ignoriert: {r.headers['X-Deck-Folien']} Folien, keine Warnung")
    # d4: min > max -> 400
    r = c.post("/api/build", data={"text": KURZ, "fmt": "b28pptx",
                                   "minfolien": "10", "maxfolien": "5"})
    assert r.status_code == 400, f"min>max sollte 400 sein: {r.status_code}"
    print("d4) minfolien > maxfolien -> 400 OK")
    # d5: Premium via Web mit min+max (KI-Plan)
    if QUICK or not CFG:
        print("d5) SKIP (keine KI / --quick)"); return
    r = c.post("/api/build", data={"text": KURZ, "fmt": "aipptx",
                                   "minfolien": "6", "maxfolien": "10"})
    assert r.status_code == 200, f"ai-build fehlgeschlagen: {r.status_code} {r.data[:200]}"
    n = int(r.headers["X-Deck-Folien"])
    print(f"d5) aipptx min=6/max=10 via test_client: X-Deck-Folien = {n}, "
          f"X-AI-Folien = {r.headers.get('X-AI-Folien')}")
    assert n >= 6, f"minfolien=6 verletzt: {n}"
    print("d) WEB OK")


if __name__ == "__main__":
    test_a_premium_max10()
    test_b_premium_min6()
    test_c_vorpptx_max5()
    test_d_web()
    print("\nFOLIENREGLER: ALLE TESTS OK")
