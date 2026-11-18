# -*- coding: utf-8 -*-
"""slideforce/linter.py - Qualitaetspruefung fuer Decks (nur Standardlib).

Beispiel:
    import json, linter
    slides = json.load(open("/tmp/reader_slides.json"))
    ergebnis = linter.pruefe_deck(slides)
    # ergebnis["score"], ergebnis["blockierend"] usw.
"""

import json


def _ist_leer(slide):
    title = (slide.get("title") or "").strip()
    bullets = slide.get("bullets") or []
    hat_text = any((b[1] or "").strip() for b in bullets if isinstance(b, (list, tuple)) and len(b) > 1)
    return not title and not hat_text


def _zeichen(slide):
    text = (slide.get("title") or "") + " " + (slide.get("subtitle") or "")
    for b in slide.get("bullets") or []:
        if isinstance(b, (list, tuple)) and len(b) > 1:
            text += " " + (b[1] or "")
    return len(text)


def _bullet_anzahl(slide):
    return len(slide.get("bullets") or [])


def _titel_hat_zahl(titel):
    return any(ch.isdigit() for ch in titel)


def _woerter(titel):
    return [w for w in titel.replace(":", " ").split() if w.strip()]


def _ist_action_titel(titel):
    w = _woerter(titel)
    return len(w) >= 4 or _titel_hat_zahl(titel)


def pruefe_deck(slides):
    warnungen = []
    kritisch = []
    layout_serie = []
    serien_start = 0

    for i, s in enumerate(slides, start=1):
        # 1) leere Folie
        if _ist_leer(s):
            kritisch.append("Folie %d: leere Folie (kein Titel, keine Bullets)" % i)

        # 2) Zeichenlimit
        z = _zeichen(s)
        if z > 600:
            kritisch.append("Folie %d: %d Zeichen (Limit 600 ueberschritten)" % (i, z))
        elif z > 350:
            warnungen.append("Folie %d: %d Zeichen (Limit 350 ueberschritten)" % (i, z))

        # 3) zu viele Bullets
        n = _bullet_anzahl(s)
        if n > 6:
            warnungen.append("Folie %d: %d Bullets (max. 6 empfohlen)" % (i, n))

        # 4) ACTION-Titel
        titel = (s.get("title") or "").strip()
        if titel and not _ist_action_titel(titel):
            warnungen.append("Folie %d: Titel wirkt als Themenlabel, keine Aussage ('%s')" % (i, titel))

        # 5) gleiche Layout-Kennung 3x hintereinander
        layout = (s.get("layout") or "").strip()
        if layout:
            if layout_serie and layout_serie[-1] == layout:
                if len(layout_serie) - serien_start + 1 >= 3 and (len(layout_serie) - serien_start + 1) == 3:
                    warnungen.append("Layout '%s' ab Folie %d: 3x hintereinander" % (layout, serien_start))
            else:
                serien_start = i
            layout_serie.append(layout)

    # 6) erste Folie
    if not slides or slides[0].get("kind") != "title":
        kritisch.append("Folie 1: erste Folie muss kind 'title' sein")

    # --- Scores ---
    # visuelle_Qualitaet 25
    leer_anzahl = sum(1 for s in slides if _ist_leer(s))
    quetsch = sum(1 for s in slides if _zeichen(s) > 350)
    vis = 100 - 40 * leer_anzahl - 15 * quetsch
    vis = max(0, min(100, vis))

    # managementverstaendlichkeit 20: Anteil guter ACTION-Titel
    titel_folien = [s for s in slides if (s.get("title") or "").strip()]
    gut = sum(1 for s in titel_folien if _ist_action_titel((s.get("title") or "").strip()))
    mgmt = int(round(100.0 * gut / len(titel_folien))) if titel_folien else 100

    # datenintegritaet 20
    daten = max(0, 100 - 20 * len(kritisch))

    # storytelling 15
    letzte_hat_inhalt = bool(slides) and (
        (slides[-1].get("title") or "").strip() or
        any((b[1] or "").strip() for b in (slides[-1].get("bullets") or [])
            if isinstance(b, (list, tuple)) and len(b) > 1)
    )
    story = 100 if (len(slides) >= 3 and letzte_hat_inhalt) else 50 if len(slides) >= 3 else 0

    # layoutqualitaet 10
    layout_warn = sum(1 for w in warnungen if "3x hintereinander" in w)
    lay = 100 - 25 * layout_warn
    lay = max(0, lay)

    # editierbarkeit 10
    edit = 100

    gesamt = (
        vis * 0.25 +
        mgmt * 0.20 +
        daten * 0.20 +
        story * 0.15 +
        lay * 0.10 +
        edit * 0.10
    )
    gesamt = int(round(gesamt))

    blockierend = gesamt < 90 or daten < 100

    ergebnis = {
        "score": gesamt,
        "kriterien": {
            "visuelle_Qualitaet": {"score": vis, "gewicht": 25},
            "managementverstaendlichkeit": {"score": mgmt, "gewicht": 20},
            "datenintegritaet": {"score": daten, "gewicht": 20},
            "storytelling": {"score": story, "gewicht": 15},
            "layoutqualitaet": {"score": lay, "gewicht": 10},
            "editierbarkeit": {"score": edit, "gewicht": 10},
        },
        "warnungen": warnungen,
        "kritisch": kritisch,
        "blockierend": blockierend,
    }

    print("[linter] Score %d/100, %d Warnungen, %d kritisch (blockierend: %s)" % (
        gesamt, len(warnungen), len(kritisch), "ja" if blockierend else "nein"))
    return ergebnis


if __name__ == "__main__":
    with open("/tmp/reader_slides.json", "r", encoding="utf-8") as f:
        deck = json.load(f)
    print(json.dumps(pruefe_deck(deck), ensure_ascii=False, indent=2))