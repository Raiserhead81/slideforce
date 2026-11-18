"""SlideForce: Template-Distillation. Master-PPTX vermessen -> Profil.

Lernt aus einem echten Master: Canvas, Theme, alle Layouts mit
Platzhalter-Geometrie (in % der Canvas) und Zweck (role). Das Profil
steuert dann PPTX-Bau (Layout-Wahl) und HTML-Bau (Geometrie + Farben).
"""
import re
import zipfile

from .html_theme import extract_theme
from .layoutmap import norm

# Namens-Keywords -> Rolle (Reihenfolge = Prioritaet)
ROLLEN = [
    ("titel", ("titelfolie", "titleslide")),
    ("section", ("kapiteltrenner", "sectionheader", "section")),
    ("statement", ("statement", "botschaft", "quote")),
    ("kpi", ("grossezahl", "kennzahlen", "kennzahl", "bignumber")),
    ("agenda", ("agenda", "zusammenfassung", "summary", "steckbrief")),
    ("table", ("tabelle", "table")),
    ("chart", ("diagramm", "chart")),
    ("roadmap", ("roadmap", "phasen", "meilenstein", "vorgehen", "planundist")),
    ("risiko", ("risiko",)),
    ("two", ("zweispalten", "twocolumn")),
    ("three", ("dreispalten", "dreisa", "vierfeld", "vier", "threecolumn", "three")),
    ("picture", ("bildrandabfallend", "bild", "picture", "image")),
    ("closing", ("abschluss", "kontakt", "thank", "endslide")),
    ("content", ("titelundinhalt", "nurtitel", "titleandcontent", "titlecontent",
                 "titleonly")),
]

PH_TYP_NAMEN = {1: "body", 3: "title", 7: "table", 13: "picture", 18: "picture",
                2: "body", 4: "body", 6: "body", 15: "body", 12: "pic"}


def _rolle_von(name):
    n = norm(name)
    for rolle, keys in ROLLEN:
        for k in keys:
            if k in n:
                return rolle
    return None


def _ph_zeile(ph, w, h):
    pf = ph.placeholder_format
    try:
        x, y = ph.left, ph.top
        bw, bh = ph.width, ph.height
    except Exception:
        x = y = bw = bh = 0
    typ = PH_TYP_NAMEN.get(int(pf.type), "body")
    if typ == "body" and pf.idx == 0:
        typ = "title"
    elif typ == "body" and norm(ph.name).startswith("titel"):
        typ = "title"
    return {
        "idx": pf.idx,
        "name": ph.name,
        "type": typ,
        "x": round(100.0 * x / w, 2) if w else 0,
        "y": round(100.0 * y / h, 2) if h else 0,
        "w": round(100.0 * bw / w, 2) if w else 0,
        "h": round(100.0 * bh / h, 2) if h else 0,
    }


def analyse(master_path):
    """PPTX-Master vermessen -> Profil-Dict (canvas, theme, layouts)."""
    from pptx import Presentation
    prs = Presentation(str(master_path))
    w, h = prs.slide_width, prs.slide_height
    layouts = []
    rollen = {}
    entwurf = []
    for i, lay in enumerate(prs.slide_layouts):
        phs = [_ph_zeile(ph, w, h) for ph in lay.placeholders]
        entwurf.append((i, lay.name, phs, _rolle_von(lay.name)))
    # Pass 1: Keyword-Rollen (Reihenfolge Master) festschreiben
    for i, name, phs, rolle in entwurf:
        if rolle and rolle not in rollen:
            rollen[rolle] = i
            layouts.append(None)  # Platzhalter, Index = i
        else:
            layouts.append(None)
    # Pass 2: Fallback nur fuer Layouts ohne Keyword-Rolle und unbesetzte Rollen
    for i, name, phs, _ in entwurf:
        rolle = _rolle_von(name)
        if rolle:
            eintrag_rolle = rolle
        else:
            typen = {p["type"] for p in phs}
            namen = norm(name)
            if ("picture" in typen and any(k in namen for k in ("bild", "picture", "image"))
                    and "picture" not in rollen):
                eintrag_rolle = "picture"
            elif "table" in typen and "table" not in rollen:
                eintrag_rolle = "table"
            elif "title" in typen and "content" not in rollen:
                eintrag_rolle = "content"
            else:
                eintrag_rolle = None
        eintrag = {"i": i, "name": name, "norm": norm(name),
                   "role": eintrag_rolle, "phs": phs}
        layouts[i] = eintrag
        if eintrag_rolle and eintrag_rolle not in rollen:
            rollen[eintrag_rolle] = i
    return {
        "canvas": {"w": int(w), "h": int(h)},
        "theme": extract_theme(master_path) or {"colors": {}, "fonts": {}},
        "layouts": layouts,
        "rollen": rollen,
    }


def lade_profil(master_path):
    """Profil aus Datei (<master>.profil.json) oder frisch analysieren."""
    import json
    from pathlib import Path
    side = Path(str(master_path) + ".profil.json")
    if side.is_file():
        try:
            return json.loads(side.read_text(encoding="utf-8"))
        except Exception:
            pass
    try:
        return analyse(master_path)
    except Exception:
        return None


def speichere_profil(master_path, profil=None):
    """Profil neben den Master legen (uploads/<master>.profil.json)."""
    import json
    from pathlib import Path
    if profil is None:
        profil = analyse(master_path)
    side = Path(str(master_path) + ".profil.json")
    side.write_text(json.dumps(profil, ensure_ascii=False, indent=1),
                    encoding="utf-8")
    return side


def rolle_zu_layout(profil, rolle):
    """Layout-Index fuer eine Rolle aus dem Profil (oder None)."""
    if not profil:
        return None
    return (profil.get("rollen") or {}).get(rolle)


def layout_profil(profil, idx):
    """Einzelnes Layout-Dict aus dem Profil (oder None)."""
    if not profil:
        return None
    for lay in profil.get("layouts", []):
        if lay["i"] == idx:
            return lay
    return None
