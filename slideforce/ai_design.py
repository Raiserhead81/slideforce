"""SlideForce Premium: KI-Design je Folie (GLM 5.3 via b28-Bridge).

Jede Folie bekommt EINEN eigenen GLM-Call, der sie individuell im
BRIDGE28-Design-System layoutet. Die KI liefert Bau-Anweisungen als
striktes JSON-Vokabular von Primitiven (band/linie/text/kachel/pill/
kartenzeile/ring/tabelle); gerendert wird lokal mit den Bewaehrten
Renderern aus profiles.py (kopf/fuss/kachel/_rect/_text/_runs_textbox).
Header, Footer und Logo zeichnet immer die Engine - die KI gestaltet nur
den Inhaltsbereich. Fehler/Timeout/ungueltiges JSON -> statischer
profiles-Fallback fuer genau diese Folie.

Nur python-pptx-API, keine manuellen XML-Manipulationen
(PowerPoint-Corruption-Lektion).
"""
import json
import re
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from threading import Lock

from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

from . import profiles as P

# ---------------------------------------------------------------- Config
CONFIG_PATHS = [
    Path("/opt/slideforce/ai-config.json"),
    Path(__file__).resolve().parent.parent / "web" / "ai-config.json",
]
DEFAULTS = {
    # URL OHNE Token - der Zugangstoken kommt ausschliesslich aus der
    # unversionierten ai-config.json (siehe .gitignore)
    "url": "https://bridge28.gemivo.de/zai.php",
    "model": "glm-5.3",
    "max_tokens": 3500,
    "timeout": 90,
}

PRIMITIVEN = {"band", "linie", "text", "kachel", "pill", "kartenzeile", "ring",
              "tabelle", "trend", "zeitstrahl"}

FARB_MAP = {  # Namen -> profiles-RGBColor (dataport-Brand: navy/gold-Aliase landen SAFE auf Petrol)
    "PETROL": P.V_PETROL, "DUNKEL": P.V_DUNKEL,
    "NAVY": P.V_PETROL, "GOLD": P.V_DUNKEL, "ROT": P.ROT, "GRUEN": P.GRUEN,
    "GRÜN": P.GRUEN, "GREEN": P.GRUEN, "GELB": P.AMB, "AMB": P.AMB, "AMBER": P.AMB,
    "GRAU": P.V_DUNKEL, "GRAU2": P.GRAU2, "LINE": P.LINE, "HELL": P.HELL,
    "WEISS": P.WEISS, "WEIß": P.WEISS, "SCHW": P.SCHW, "SCHWARZ": P.SCHW,
}
ALIGN_MAP = {
    "left": PP_ALIGN.LEFT, "links": PP_ALIGN.LEFT,
    "center": PP_ALIGN.CENTER, "mitte": PP_ALIGN.CENTER, "centered": PP_ALIGN.CENTER,
    "right": PP_ALIGN.RIGHT, "rechts": PP_ALIGN.RIGHT,
}


def load_ai_config():
    """Erste vorhandene Config-Datei laden, mit Defaults mergen. None wenn keine da."""
    for p in CONFIG_PATHS:
        if p.is_file():
            try:
                cfg = json.loads(p.read_text(encoding="utf-8"))
                if isinstance(cfg, dict) and cfg.get("url"):
                    return {**DEFAULTS, **cfg}
            except Exception:
                continue
    return None


# ---------------------------------------------------------------- Prompt
SP_KOPF = """Du bist Senior-Slide-Designer bei BRIDGE28 und designt Kundenfolien auf Premium-Niveau: dicht, praezise, hochwertig - niemals leer oder beliebig.

DESIGN-SYSTEM (Kundenvorlage aus dem hochgeladenen Master, hell):
- Leinwand: 13.33 x 7.5 Zoll (inch), Rand links/rechts MX = 0.55.
"""
SP_BRAND_DEFAULT = """- Farben (nutze GENAU diese Namen): PETROL #39756F (dominant, Header, Zahlen, Titel) · ROT #9E292B (nur Spaetzen-Akzent) · DUNKEL #39424A (Ueberschriften) · GRAU #54616E · GRAU2 #8A93A3 (Sekundaertext) · LINE #D8DEE2 (Border) · HELL #F4F5F6 (Kartenflaeche) · TINT1 #F8E8E8 · TINT2 #FBF0DC · WEISS · SCHW #1A222B (Fliesstext). KEIN Navy, KEIN Gold.
- Typo (Arial): Kicker 10-11pt PETROL bold UPPERCASE (gross geschrieben!) · Folien-Abschnittstitel 15-18pt DUNKEL bold · Fliesstext 11-13pt SCHW · Labels UPPERCASE 10.5pt GRAU bold · Zahlen dominant gross (PETROL) · Kontext 9.5-10pt GRAU2. Fett im Text mit **so** markieren.
- Stil: helle Karten (HELL) mit feiner LINE-Border und PETROL-Marker links; KPI-Kacheln mit PETROL-Balken oben; ROT nur fuer einen einzelnen Spaetzenakzent; ruhig, viel Weissraum, vorstandstauglich.
"""
SP_REST = """
- HARTE LAYOUT-REGELN (Verstoss = abgelehnt): maximal 10 Elemente je Folie · jedes Element muss voll im Canvas liegen: x>=0.55, x+w<=12.78, y>=0.55, y+h<=7.1 · zwei Elemente duerfen sich NIEMALS ueberlappen (pruefe x/y-Rechtecke!) · Fliesstext je Folie max 120 Woerter (Richtung 40-80, Ruhe schlaegt Dichte) · folienrand: nichts innerhalb 0.3 inch vom Rand.
- KERNBEFUND-REGEL: Das Kernelement jeder Folie bekommt eine sichtbare Annotation (trend-Chip, status-Pill oder kurzer text) mit dem "So what" - die Folie muss ohne Praesentierer verstaendlich sein.
- FARBE LENKT: Farbe nur fuer den Kernbefund und Status - niemals als Dekoration. Alles Nicht-Kernige bleibt GRAU2/DUNKEL.
- ANTI-SLOP: keine erfundenen Farben (nur die Palette oben) · keine Deko-Icons/Emojis · keine Deko-Verlaeufe · keine "data slop" (nutzlose Zahlen/Kennzahlen zur Deko) · jedes Element muss seinen Platz VERDIENEN - eine leere Flaeche wird mit Komposition geloest, nie mit Fuellinhalt.
- KEINE ERFUNDENEN DATEN: fehlt eine Zahl, lasse das Element weg - niemals plausibel aussehende Zahlen raten.

STRENGES JSON-BAU-VOKABULAR - nur diese Primitive ("typ"-Feld), Koordinaten in inch:
- {"typ":"band","x":..,"y":..,"w":..,"h":..,"farbe":"NAVY"}                        Vollflaechiges Rechteck
- {"typ":"linie","x":..,"y":..,"w":..,"h":0.012,"farbe":"LINE"}                    Feine Linie (h sehr klein)
- {"typ":"text","x":..,"y":..,"w":..,"h":..,"text":"..","size":12,"farbe":"SCHW","bold":false,"align":"left"}
- {"typ":"kachel","x":..,"y":..,"w":..,"h":..,"label":"LABEL","gross":"4,2","unit":"Mio","unter":"plus 12%","kontext":"seit 2023","farbe":"NAVY","status":"Am Limit"}   KPI-Kachel: weisse Karte, Border + Balken oben in Statusfarbe, Label UPPERCASE, Zahl 30pt NAVY bold + Unit 12.5pt; status (optional) = abgerundete Pill unten (Grün/Gelb/Rot/Am Limit/In Arbeit -> automatisch gefärbt)
- {"typ":"pill","x":..,"y":..,"w":..,"h":0.32,"text":"Status","farbe":"GRUEN"}     Abgerundete Status-Pille mit farbigem Fill + bold Text (WEISS, bei GOLD NAVY). Standard-Statusworte: Grün/rot gefärbt, "Am Limit" = GOLD
- {"typ":"trend","x":..,"y":..,"w":1.5,"delta":"+12 %","richtung":"up","farbe":"GRUEN"}   Trend-Chip: Pfeil ▲/▼ + Delta in Statusfarbe auf heller Karte - neben Kachel-Zahlen fuer Entwicklung gg. Vorjahr/Woche
- {"typ":"kartenzeile","x":..,"y":..,"w":..,"h":0.55,"text":"**Migration:** 42 von 60 ...","level":0}   Zeilen-Karte (HELL-Fuellung, LINE-Border, GOLD-Marker links, 13pt); level 1 = Unterpunkt eingerueckt ohne Karte
- {"typ":"ring","x":..,"y":..,"w":3.0,"wert":75,"farbe":"GOLD"}                    Fortschrittsring (Doughnut) mit Prozentwert im Zentrum
- {"typ":"tabelle","x":..,"y":..,"w":12.23,"rows":[["Bereich","Status"],["Build","Gelb"]],"status_spalten":[1]}   Tabelle: Kopfzeile NAVY, Zebra WEISS/HELL; status_spalten = Spalten-Indizes (0-basiert) mit Grun/Gelb/Rot-Status-Pillen (abgerundet, farbiger Fill, weisse Schrift)
- {"typ":"zeitstrahl","x":0.55,"y":1.6,"w":12.23,"heute":"2026-11-18","meilensteine":[["2026-11-30","M0 Start","fertig"],["2027-04-30","M3 Go-Live","kritisch"]]}   BRIDGE28-Bruecken-Zeitstrahl: goldener Spannbogen, 2 NAVY-Pylonen, Meilenstein-Punkte auf dem Bogen (farbig nach Status), HEUTE-Marker, Countdown-Chip, Quartals-Achse. Nutze ihn FUER ALLE Fahrplan-/Meilenstein-/Termin-Themen statt kahler Listen

REGELN:
1. Header-Band (NAVY, 0.95 hoch mit Kicker+Titel), Footer und Logo zeichnet die ENGINE - niemals selbst zeichnen. Gestalte nur den Inhaltsbereich.
2. Koordinaten NIE ausserhalb 0..13.33 x 0..7.5. Inhaltsbereich: x 0.55..12.78, y 1.15..6.85 (ausser anders angegeben).
3. Nur die genannten Primitive, keine eigenen Feldnamen. Umlaute korrekt schreiben.
4. PREMIUM-DICHTE wie der b28-Original-Export: Nutze die volle Breite (12.23) und Hoehe (1.15..6.85). 4 KPI-Werte -> 4-spaltige Kachelreihe (w je 2.91, Gap 0.2); 2 Werte -> 2 Kacheln je 6.01. Jede Kennzahl bekommt trend-Chip oder status-Pill, wenn Zahlen dazu da sind. Kartenzeilen: h 0.55, Gap 0.14-0.35. Weniger als 5 Elemente sind fast immer zu leer; mehr als 10 fast immer ueberladen. Keine einsamen Textblocks.
5. Zahlen und Kernaussagen dominant, Meta-Info dezent (GRAU2). Keine ueberlappenden Boxen, konsistentes Raster.
6. ANTWORTE NUR MIT JSON, genau diesem Format, kein erklaerender Text, keine Markdown-Fences:
{"folie":<n>,"hintergrund":"WEISS","elemente":[ ... ]}
"hintergrund": "WEISS", "HELL" oder "NAVY" (NAVY nur fuer dunkle Statement-/Kapitelfolien; Textfarben dann WEISS/GOLD).

BEISPIEL einer fertigen Bauanweisung (KPI-Folie, 2 Kennzahlen + Massnahmen):
{"folie":2,"hintergrund":"WEISS","elemente":[
 {"typ":"kachel","x":0.55,"y":1.30,"w":6.01,"h":2.30,"label":"Umsatz Q4","gross":"4,2","unit":"Mio EUR","unter":"plus 12% gg. Vorjahr","kontext":"bestes Quartal seit 2023","farbe":"NAVY"},
 {"typ":"kachel","x":6.77,"y":1.30,"w":6.01,"h":2.30,"label":"Offene Standorte","gross":"18","unit":"","unter":"bis 31.12. geplant","kontext":"Ziel: alle 60 bis Q1","farbe":"GOLD"},
 {"typ":"text","x":0.55,"y":3.90,"w":6.0,"h":0.30,"text":"NACHSTE SCHRITTE","size":10.5,"farbe":"GRAU","bold":true},
 {"typ":"kartenzeile","x":0.55,"y":4.25,"w":12.23,"h":0.55,"text":"**Migration:** 42 von 60 Standorten versorgt, Tendenz steigend","level":0},
 {"typ":"kartenzeile","x":0.55,"y":4.94,"w":12.23,"h":0.55,"text":"Budget-Nachtrag bis Freitag einreichen","level":0},
 {"typ":"kartenzeile","x":0.55,"y":5.63,"w":12.23,"h":0.55,"text":"Teststart Montag mit Bereich Mitte","level":0},
 {"typ":"linie","x":0.55,"y":6.55,"w":12.23,"h":0.012,"farbe":"LINE"}
]}"""
SYSTEM_PROMPT = SP_KOPF + SP_BRAND_DEFAULT + SP_REST

# ------------------------------------------------ Master-Theme (Premium lernt Master)
_AI_LOCK = Lock()   # Premium-Builds seriell (Farb-Theming ist prozessglobal)


def _hex_rgb(h):
    return RGBColor.from_string(h.lstrip("#").upper()[:6])


def _hell(h):
    r, g, b = int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16)
    return (0.299 * r + 0.587 * g + 0.114 * b) / 255


def _farb_haeufigkeit(master_path):
    """Alle srgbClr/lastClr-Hexes im Master-Zaehlen (Proxy fuer Marken-Farbe)."""
    import zipfile
    from collections import Counter
    z = Counter()
    try:
        with zipfile.ZipFile(str(master_path)) as zf:
            for name in zf.namelist():
                if not name.endswith(".xml"):
                    continue
                xml = zf.read(name).decode("utf-8", "replace")
                for m in re.finditer(r'(?:srgbClr val="([0-9A-Fa-f]{6})"|lastClr="([0-9A-Fa-f]{6})")', xml):
                    z[(m.group(1) or m.group(2)).lower()] += 1
    except Exception:
        pass
    return z


def _gesaettigt(h):
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return _hell("#" + h) < 0.72 and _hell("#" + h) > 0.12 and (max(r, g, b) - min(r, g, b)) > 36


def master_farben(master_path):
    """Master-Farben nach HAEUFIGKEIT im XML (robust gegen vertauschte
    Theme-Slots): dominant = haeufigste gesaettigte Farbe usw.
    -> dict oder None."""
    from .masterprofil import lade_profil
    try:
        prof = lade_profil(master_path) or {}
        t = prof.get("theme") or {}
        c = t.get("colors") or {}
        fonts = t.get("fonts") or {}
    except Exception:
        c, fonts = {}, {}
    if not c:
        return None
    zaehler = _farb_haeufigkeit(master_path)
    ges = [h for h, _ in sorted(zaehler.items(), key=lambda kv: -kv[1]) if _gesaettigt(h)]
    dom = ges[0] if ges else c.get("accent1", "39756f").lstrip("#")
    a2 = next((h for h in ges if h != dom), dom)
    a3 = next((h for h in ges if h not in (dom, a2)), a2)
    # dunkles Neutral (Ueberschriften): haeufigste neutrale Farbe mit Helligkeit 0.18..0.45
    dunkel = next((h for h, _ in sorted(zaehler.items(), key=lambda kv: -kv[1])
                   if 0.18 < _hell("#" + h) < 0.45 and not _gesaettigt(h)), "39424a")
    # helle Flaeche (Karten/Borders): haeufigste helle Farbe ausser reinem Weiss
    hell = next((h for h, _ in sorted(zaehler.items(), key=lambda kv: -kv[1])
                 if _hell("#" + h) > 0.88 and h != "ffffff" and not _gesaettigt(h)),
                c.get("lt2", "d8dee2").lstrip("#"))
    return {"dominant": dom, "akzent2": a2, "akzent3": a3, "dunkel": dunkel,
            "hell": hell, "text": c.get("dk1", "1a222b").lstrip("#"),
            "font": (fonts.get("major") or "Arial")}


def master_farben(master_path):
    """Master-Farben aus den Theme-Slots (gleiche bewaehrte Heuristik wie
    html_export: lt2 kann die dominante Marke tragen, accent1 oft nur
    Spitzen-Akzent - vertauschte Slots sind in realen Masters ueblich).
    -> dict oder None."""
    from .masterprofil import lade_profil
    try:
        prof = lade_profil(master_path) or {}
        t = prof.get("theme") or {}
        c = t.get("colors") or {}
        fonts = t.get("fonts") or {}
    except Exception:
        c, fonts = {}, {}
    if not c:
        return None

    def hexs(name, default):
        v = c.get(name)
        return v.lstrip("#").lower() if v else default

    dom_kands = [h for h in (hexs("lt2", ""), hexs("accent1", ""),
                             hexs("accent2", ""), hexs("accent5", ""))
                 if h and _gesaettigt(h)]
    dom = dom_kands[0] if dom_kands else hexs("accent1", "39756f")
    a3 = next((h for h in (hexs("accent1", ""), hexs("accent2", ""),
                           hexs("accent5", ""), hexs("accent4", ""))
               if h and _gesaettigt(h) and h != dom), dom)
    a2 = next((h for h in (hexs("accent5", ""), hexs("accent4", ""),
                           hexs("accent2", ""), hexs("accent1", ""))
               if h and _gesaettigt(h) and h != dom and h != a3), a3)
    dunkel = hexs("accent3", "")
    if not dunkel or _hell("#" + dunkel) > 0.45:
        dunkel = hexs("dk2", "39424a")
    if _hell("#" + dunkel) > 0.45:
        dunkel = "39424a"
    hell = hexs("accent6", "")
    if not hell or hell == "ffffff" or _hell("#" + hell) < 0.88:
        hell = hexs("dk2", "f4f6f8")
    if hell == "ffffff" or _hell("#" + hell) < 0.88:
        hell = "f4f6f8"
    return {"dominant": dom, "akzent2": a2, "akzent3": a3, "dunkel": dunkel,
            "hell": hell, "text": hexs("dk1", "1a222b"),
            "font": (fonts.get("major") or "Arial")}


def master_farb_map(master_path):
    """Master-Farben -> FARB_MAP-Kopie: PETROL/NAVY=dominant, GOLD=akzent2,
    ROT=akzent3, DUNKEL/GRAU=dunkel, SCHW=text, HELL/LINE=helle Flaeche."""
    f = master_farben(master_path)
    if not f:
        return None
    fm = dict(FARB_MAP)
    fm["PETROL"] = fm["NAVY"] = _hex_rgb(f["dominant"])
    fm["GOLD"] = _hex_rgb(f["akzent2"])
    fm["ROT"] = _hex_rgb(f["akzent3"])
    fm["DUNKEL"] = fm["GRAU"] = _hex_rgb(f["dunkel"])
    fm["SCHW"] = _hex_rgb(f["text"])
    fm["LINE"] = fm["HELL"] = _hex_rgb(f["hell"])
    return fm


def master_brand_block(master_path):
    """Prompt-Brand-Block aus den Master-Farben (echte Hex-Werte + Font)."""
    f = master_farben(master_path)
    if not f:
        return None
    return (
        f"- Farben (nutze GENAU diese Namen): PETROL #{f['dominant'].upper()} (dominant: Header, Zahlen, Titel) · "
        f"GOLD #{f['akzent2'].upper()} (zweiter Akzent) · ROT #{f['akzent3'].upper()} (nur Spaetzen-Akzent) · "
        f"DUNKEL #{f['dunkel'].upper()} (Ueberschriften, dunkle Kapitel-Folien) · GRAU2 Sekundaertext · "
        f"LINE #{f['hell'].upper()} (Border) · HELL #{f['hell'].upper()} (Kartenflaeche) · WEISS · "
        f"SCHW #{f['text'].upper()} (Fliesstext).\n"
        f"- Typo ({f['font']}): Kicker 10-11pt PETROL bold UPPERCASE · Abschnittstitel 15-18pt DUNKEL bold · "
        f"Fliesstext 11-13pt SCHW · Labels UPPERCASE 10.5pt GRAU bold · Zahlen dominant gross PETROL · "
        f"Kontext 9.5-10pt GRAU2. Fett im Text mit **so** markieren.\n"
        "- Stil: helle Karten (HELL) mit feiner LINE-Border und PETROL-Marker links; KPI-Kacheln mit "
        "PETROL-Balken oben; ROT nur fuer einen einzelnen Spaetzenakzent; ruhig, viel Weissraum, "
        "vorstandstauglich - die Vorlage ist der MARKEN-MASTER des Kunden, niemals davon abweichen.\n"
    )


def setze_master_theme(master_path):
    """FARB_MAP + profiles-Modul-Farben auf die Master-Marke umstellen.
    Rueckgabe: Restore-Snapshot (oder None, wenn kein Theme)."""
    fm = master_farb_map(master_path)
    if fm is None:
        return None
    felder = {n: getattr(P, n) for n in
              ("PETROL", "NAVY", "GOLD", "ROT", "DUNKEL", "GRAU", "SCHW",
               "LINE", "HELL", "V_PETROL", "V_DUNKEL", "V_GRAU", "V_TEXT",
               "V_LINE", "V_KARTE") if hasattr(P, n)}
    snap = {"FARB_MAP": dict(FARB_MAP), "P": felder}
    FARB_MAP.clear()
    FARB_MAP.update(fm)
    for k, v in (("PETROL", fm["PETROL"]), ("NAVY", fm["NAVY"]),
                 ("GOLD", fm["GOLD"]), ("ROT", fm["ROT"]),
                 ("DUNKEL", fm["DUNKEL"]), ("GRAU", fm["GRAU"]),
                 ("SCHW", fm["SCHW"]), ("LINE", fm["LINE"]), ("HELL", fm["HELL"]),
                 ("V_PETROL", fm["PETROL"]), ("V_DUNKEL", fm["DUNKEL"]),
                 ("V_GRAU", fm["GRAU"]), ("V_TEXT", fm["SCHW"]),
                 ("V_LINE", fm["LINE"]), ("V_KARTE", fm["HELL"])):
        if hasattr(P, k):
            setattr(P, k, v)
    return snap


def restore_theme(snap):
    if not snap:
        return
    FARB_MAP.clear()
    FARB_MAP.update(snap["FARB_MAP"])
    for k, v in snap["P"].items():
        setattr(P, k, v)


def _user_prompt(s, n, m):
    """Inhalts-Prompt fuer EINE Folie."""
    kind = s.get("kind", "content")
    typ = {"title": "TITELFOLIE (Deck-Cover)", "section": "KAPITELFOLIE (dunkel)"}.get(kind, "INHALTSFOLIE")
    z = [f"Folie {n} von {m} - Typ: {typ}"]
    if s.get("kicker"):
        z.append(f"kicker: {s['kicker']}")
    if s.get("title"):
        z.append(f"titel: {s['title']}")
    if s.get("subtitle"):
        z.append(f"untertitel: {s['subtitle']}")
    for lvl, t in (s.get("bullets") or []):
        z.append(("  - " if lvl else "- ") + str(t))
    for k, v in s.items():
        if k in ("kind", "layout", "title", "subtitle", "bullets", "image", "notes", "kicker"):
            continue
        if k == "table":
            z.append("tabelle:")
            for row in (v or []):
                z.append("| " + " | ".join(str(c) for c in row) + " |")
        elif isinstance(v, list):
            z.append(f"{k}:")
            for eintrag in v:
                if isinstance(eintrag, (list, tuple)):
                    eintrag = "|".join(str(t) for t in eintrag)
                z.append(f"- {eintrag}")
        elif isinstance(v, (str, int, float)):
            z.append(f"{k}: {v}")
    if kind == "title":
        z.append("HINWEIS: Kicker, Meta, das Petrol-Band unten (Titel/Untertitel) und das Logo "
                 "zeichnet die ENGINE. Du gestaltest NUR die Zone y 1.7 bis 4.1 - "
                 "z.B. 2-3 dezente Meta-Karten oder Pills (Datum, Autor, Version, Kernzahl) "
                 "oder eine Gold-Linie mit Kontextzeile. Maximal 4 Elemente, KEINE Flaechen "
                 "unter y 4.3 (dort steht das Band). Hintergrund WEISS.")
    elif kind == "section":
        z.append("HINWEIS: Der dunkle NAVY-Hintergrund wird von der Engine gesetzt (hintergrund: NAVY). "
                 "Gestalte Kicker (GOLD, UPPERCASE, 11pt), Kapiteltitel (WEISS, 34-40pt bold), eine kurze "
                 "Gold-Akzentlinie und 2-4 helle kartenzeilen als Vorschau. Textfarben WEISS/GOLD/GRAU2, "
                 "y-Bereich 1.2..6.8.")
    else:
        if s.get("zeitstrahl") or s.get("meilensteine"):
            z.append("HINWEIS: Baue die primitive {\"typ\":\"zeitstrahl\"} mit ALLEN Meilensteinen "
                     "(x 0.55, y 1.6, w 12.23, heute = heutiges Datum) - nicht als Liste. "
                     "Darunter Platz fuer bis zu 2 Kartenzeilen lassen (y ab 5.3).")
        z.append("HINWEIS: Header (kicker + titel als NAVY-Band) und Footer zeichnet die Engine. "
                 "Gestalte nur y 1.15..6.85, x 0.55..12.78. Setze alle Inhalte dieser Folie vollstaendig "
                 "und dicht um (KPI-Werte als kachel mit status/trend, Listen als kartenzeilen, Tabellen "
                 "als tabelle mit status_spalten, Fahrplaene als zeitstrahl). Erfinde keine Zahlen, "
                 "nutze die gegebenen.")
    return "\n".join(z)


# ---------------------------------------------------------------- KI-Call
def _extract_json(txt):
    """Erstes vollstaendiges {...} aus Text ziehen (robust gegen Codefences/Prosa)."""
    if not txt:
        return None
    fence = re.search(r"```(?:json)?\s*(.*?)```", txt, re.S)
    if fence:
        txt = fence.group(1)
    start = txt.find("{")
    while start != -1:
        depth, in_str, esc = 0, False, False
        for i in range(start, len(txt)):
            c = txt[i]
            if in_str:
                if esc:
                    esc = False
                elif c == "\\":
                    esc = True
                elif c == '"':
                    in_str = False
            elif c == '"':
                in_str = True
            elif c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(txt[start:i + 1])
                    except Exception:
                        break
        start = txt.find("{", start + 1)
    return None


def _validiere(d):
    """KI-Antwort pruefen: elemente-Liste mit mind. 1 gueltiger Primitive."""
    if not isinstance(d, dict):
        return None
    elemente = d.get("elemente")
    if not isinstance(elemente, list):
        return None
    gut = [e for e in elemente
           if isinstance(e, dict) and (e.get("typ") or e.get("type")) in PRIMITIVEN]
    if not gut:
        return None
    return {"hintergrund": str(d.get("hintergrund", "WEISS")).upper(), "elemente": gut}


def _ki_call(user_prompt, cfg, system=None):
    """Ein GLM-Call (2 Versuche). Gibt validiertes design-dict oder None."""
    body = json.dumps({
        "model": cfg.get("model", "glm-5.3"),
        "max_tokens": int(cfg.get("max_tokens", 3500)),
        "messages": [
            {"role": "system", "content": system or SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    }).encode("utf-8")
    for _versuch in range(2):
        try:
            req = urllib.request.Request(
                cfg["url"], data=body,
                headers={"Content-Type": "application/json", "User-Agent": "slideforce-ai"})
            raw = urllib.request.urlopen(req, timeout=int(cfg.get("timeout", 90))).read()
            msg = (json.loads(raw).get("choices") or [{}])[0].get("message") or {}
            d = _extract_json(msg.get("content") or "")
            if d is None:
                d = _extract_json(msg.get("reasoning_content") or "")
            return _validiere(d)
        except (urllib.error.URLError, TimeoutError, OSError, ValueError, KeyError,
                json.JSONDecodeError):
            time.sleep(1.5)
    return None


def design_folien(slides, config=None, on_progress=None, system=None):
    """JEDE Folie EIN GLM-Call, max 4 parallel.

    -> Liste (Reihenfolge = slides) mit design-dict oder None (= Fallback).
    on_progress(fertig, gesamt) wird nach jeder beendeten Folie gerufen.
    """
    config = config or load_ai_config()
    if not config:
        return [None] * len(slides)
    m = len(slides)
    results = [None] * m
    done, lock = 0, Lock()

    def arbeit(n, s):
        return _ki_call(_user_prompt(s, n, m), config, system)

    with ThreadPoolExecutor(max_workers=4) as ex:
        futs = {ex.submit(arbeit, n, s): n for n, s in enumerate(slides, 1)}
        for fut in as_completed(futs):
            n = futs[fut]
            try:
                results[n - 1] = fut.result()
            except Exception:
                results[n - 1] = None
            with lock:
                done += 1
                if on_progress:
                    try:
                        on_progress(done, m)
                    except Exception:
                        pass
    return results


# ---------------------------------------------------------------- Renderer
def _cover_engine(sl, s):
    """Editorial-Cover der ENGINE: Kicker oben, grosse Tint-Karte Mitte
    (Platz fuer die KI-Meta-Zone), Petrol-Band unten mit Titel+Untertitel
    + Gold-Linie. Farben automatisch Master-Marke (Theming ist aktiv)."""
    from pptx.enum.shapes import MSO_SHAPE
    from pptx.enum.text import PP_ALIGN
    P._rect(sl, 0, P.H - 2.55, P.W, 2.55, P.NAVY)
    P._rect(sl, 0.55, P.H - 2.95, 1.6, 0.05, P.GOLD)
    P._text(sl, 0.55, P.H - 2.25, 9.5, 1.15, str(s.get("title", "")), 30,
            P.WEISS, bold=True)
    if s.get("subtitle"):
        P._text(sl, 0.55, P.H - 1.02, 10.5, 0.62, str(s.get("subtitle")), 13.5,
                P.WEISS, bold=False)
    P._text(sl, 0.55, 0.75, 11.5, 0.4, str(s.get("kicker") or "PREMIUM-DECK").upper(),
            11, P.NAVY, bold=True)
    meta = str(s.get("meta") or "")
    if meta:
        P._text(sl, 0.55, 1.22, 11.5, 0.36, meta, 10.5, P.GRAU2)


def _farbe(v, default=P.NAVY):
    if isinstance(v, str):
        t = v.strip().upper()
        if t in FARB_MAP:
            return FARB_MAP[t]
        if t.startswith("#") and len(t) == 7:
            try:
                return RGBColor.from_string(t[1:])
            except Exception:
                pass
    return default


def _num(v, default):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _clamp_box(el, x_d=0.0, y_d=1.15, w_d=12.23, h_d=0.5):
    """x/y/w/h lesen und in die Leinwand zwängen."""
    x = min(max(_num(el.get("x"), x_d), 0.0), P.W)
    y = min(max(_num(el.get("y"), y_d), 0.0), P.H)
    w = max(0.05, min(_num(el.get("w"), w_d), P.W - x))
    h = max(0.01, min(_num(el.get("h"), h_d), P.H - y))
    return x, y, w, h


def _p_band(sl, el):
    x, y, w, h = _clamp_box(el, h_d=0.3)
    P._rect(sl, x, y, w, h, _farbe(el.get("farbe"), P.NAVY))


def _p_linie(sl, el):
    x, y, w, h = _clamp_box(el, h_d=0.012)
    P._rect(sl, x, y, w, max(h, 0.008), _farbe(el.get("farbe"), P.LINE))


def _p_text(sl, el, dunkel=False):
    x, y, w, h = _clamp_box(el)
    size = min(max(_num(el.get("size"), 12), 6), 60)
    align = ALIGN_MAP.get(str(el.get("align", "left")).strip().lower(), PP_ALIGN.LEFT)
    farbe = _farbe(el.get("farbe"), P.WEISS if dunkel else P.SCHW)
    P._text(sl, x, y, w, h, str(el.get("text", "")), size, farbe,
            bold=bool(el.get("bold")), align=align)


def _p_kachel(sl, el):
    x, y, w, h = _clamp_box(el, y_d=1.3, w_d=6.0, h_d=2.3)
    farbe = el.get("farbe")
    status = el.get("status")
    sf = P._status_farbe(status) if status else None
    P.kachel(sl, x, y, w, h, str(el.get("label", "")), str(el.get("gross", "")),
             str(el.get("unit") or ""), str(el.get("unter") or ""),
             str(el.get("kontext") or ""),
             sf or (_farbe(farbe) if farbe is not None else None),
             status=status if status else None)


def _p_pill(sl, el):
    x, y, w, h = _clamp_box(el, h_d=0.32)
    P._pill(sl, x, y, w, h, str(el.get("text", "")),
            _farbe(el.get("farbe"), P.GRUEN),
            size=min(max(_num(el.get("size"), 10.5), 8), 14))


def _p_trend(sl, el):
    """Trend-Chip: Pfeil + Delta in Statusfarbe auf heller Karte."""
    x, y, w, h = _clamp_box(el, w_d=1.5, h_d=0.34)
    delta = str(el.get("delta", ""))
    up = str(el.get("richtung", "up")).strip().lower() not in ("down", "ab", "runter", "minus")
    farbe = _farbe(el.get("farbe"), P.GRUEN if up else P.ROT)
    P._rect(sl, x, y, w, h, P.HELL, line=P.LINE)
    pfeil = "\u25b2" if up else "\u25bc"
    P._text(sl, x + 0.08, y, w - 0.16, h, f"{pfeil} {delta}",
            min(max(_num(el.get("size"), 11), 8), 14), farbe, bold=True)


def _p_zeitstrahl(sl, el):
    """BRIDGE28-Bruecken-Zeitstrahl (Bogen/Pylonen/Punkte/HEUTE/Countdown)."""
    x = min(max(_num(el.get("x"), P.MX), 0), P.W)
    y = min(max(_num(el.get("y"), 1.6), 1.0), P.H)
    w = min(max(_num(el.get("w"), P.W - 2 * P.MX), 3.0), P.W - x - 0.1)
    P._bruecke(sl, x, y, w, el.get("meilensteine") or [], el.get("heute"))


def _p_kartenzeile(sl, el):
    x, y, w, h = _clamp_box(el, w_d=P.W - 2 * P.MX, h_d=0.55)
    text = str(el.get("text", ""))
    if int(_num(el.get("level"), 0)) >= 1:      # Unterpunkt: ohne Karte, eingerueckt
        P._rect(sl, x + 0.55, y + h / 2 - 0.015, 0.16, 0.03, P.GOLD)
        P._runs_textbox(sl, x + 0.82, y - 0.015, max(1.0, w - 0.95), h + 0.03,
                        text, 12, base_color=P.GRAU, bold_color=P.NAVY,
                        anchor=MSO_ANCHOR.TOP)
        return
    P._rect(sl, x, y, w, h, P.HELL, line=P.LINE)
    P._rect(sl, x, y, 0.08, h, P.GOLD)
    P._runs_textbox(sl, x + 0.26, y + 0.02, max(1.0, w - 0.42), max(0.2, h - 0.04),
                    text, 13 if h >= 0.45 else 12)


def _p_ring(sl, el):
    x, y = min(max(_num(el.get("x"), P.MX), 0), P.W), min(max(_num(el.get("y"), 1.45), 0), P.H)
    size = min(max(_num(el.get("w"), 3.0), 1.5), min(5.0, P.H - y - 0.2, P.W - x - 0.2))
    wert = min(max(_num(el.get("wert"), 0), 0), 100)
    akzent = _farbe(el.get("farbe"), P.GOLD)
    cd = CategoryChartData()
    cd.categories = ["Wert", "Rest"]
    cd.add_series("Anteil", (wert, max(0.0, 100.0 - wert)))
    gf = sl.shapes.add_chart(XL_CHART_TYPE.DOUGHNUT, Inches(x), Inches(y),
                             Inches(size), Inches(size), cd)
    ch = gf.chart
    ch.has_legend = False
    ch.has_title = False
    for pt, farbe in zip(list(ch.plots[0].series[0].points), (akzent, P.NAVY)):
        pt.format.fill.solid()
        pt.format.fill.fore_color.rgb = farbe
        pt.format.line.color.rgb = P.WEISS
        pt.format.line.width = Pt(1.5)
    cx = x + size / 2
    P._text(sl, cx - 0.85, y + size / 2 - 0.3, 1.7, 0.6, f"{wert:g} %", 28, P.NAVY,
            bold=True, align=PP_ALIGN.CENTER)


def _p_tabelle(sl, el):
    rows = el.get("rows") or []
    if not isinstance(rows, list) or not rows:
        return
    rows = [[str(c) for c in r] if isinstance(r, list) else [str(r)] for r in rows]
    x, y, w, _ = _clamp_box(el, w_d=P.W - 2 * P.MX)
    try:
        status_cols = {int(i) for i in (el.get("status_spalten") or [])}
    except (TypeError, ValueError):
        status_cols = set()
    ncols = max(len(r) for r in rows)
    nrows = len(rows)
    row_h = min(0.62, max(0.40, 5.4 / nrows))
    gf = sl.shapes.add_table(nrows, ncols, Inches(x), Inches(y), Inches(w),
                             Inches(row_h * nrows))
    tbl = gf.table
    tbl.first_row = False
    tbl.horz_banding = False
    for r in range(nrows):
        tbl.rows[r].height = Inches(row_h)
    for r, row in enumerate(rows):
        for c in range(ncols):
            cell = tbl.cell(r, c)
            cell.text = row[c] if c < len(row) else ""
            cell.margin_left = Inches(0.1)
            cell.margin_top = Inches(0.03)
            cell.margin_bottom = Inches(0.03)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            pill = None if r == 0 else (
                P._status_farbe(cell.text) if c in status_cols else None)
            fill = cell.fill
            fill.solid()
            if r == 0:
                fill.fore_color.rgb = P.NAVY
            elif pill is not None:
                fill.fore_color.rgb = pill
            else:
                fill.fore_color.rgb = P.HELL if r % 2 else P.WEISS
            for p in cell.text_frame.paragraphs:
                for run in p.runs:
                    run.font.size = Pt(11.5 if r == 0 else 11)
                    run.font.bold = r == 0 or pill is not None
                    run.font.name = P.FONT
                    run.font.color.rgb = P.WEISS if (r == 0 or pill is not None) else P.SCHW


_RENDERER = {"band": _p_band, "linie": _p_linie, "text": _p_text, "kachel": _p_kachel,
             "pill": _p_pill, "kartenzeile": _p_kartenzeile, "ring": _p_ring,
             "tabelle": _p_tabelle, "trend": _p_trend, "zeitstrahl": _p_zeitstrahl}


def _render_elemente(sl, elemente, dunkel=False):
    """Bauanweisungen ausfuehren; einzelne Fehler ueberspringen, Rest baut weiter."""
    for el in elemente or []:
        fn = _RENDERER.get((el.get("typ") or el.get("type")))
        if not fn:
            continue
        try:
            if fn is _p_text:
                fn(sl, el, dunkel=dunkel)
            else:
                fn(sl, el)
        except Exception:
            continue


# ---------------------------------------------------------------- Deck-Bau
# ------------------------------------------------ Folienplan (Min/Max-Regler)
PLAN_SYSTEM_PROMPT = """Du bist Slide-Architekt bei BRIDGE28: Aus rohem Inhalt (Transkript, Notizen, Zahlen) erstellst du einen praegnanten, logisch gegliederten FOLIENPLAN - nur Struktur, kein Design. Du triffst die perfekte Folienzahl: zusammenfassen, wo zu viel Stoff fuer eine Folie da ist, aufteilen, wo eine Folie ueberladen waere. Niemals Informationen erfinden - jeder Punkt muss aus dem Input belegt sein."""

PLAN_SCHEMA = """FOLIEN-SCHEMA (reines JSON, dein kompletter Output):
{"folien":[
 {"kind":"title","title":"Deck-Titel","subtitle":"Untertitel"},
 {"kind":"section","title":"Kapitel-Titel"},
 {"kind":"content","title":"Folien-Titel","kicker":"KURZLABEL","bullets":[[0,"Kernaussage"],[1,"Unterpunkt"]],"zahl":"93 %","einheit":"Migrationsstand","botschaft":"Kernbotschaft der Folie"}
]}
Feld-Erklaerung:
- kind: "title" (NUR Folie 1, Deck-Cover), "section" (Kapitel-Trenner), "content" (alle anderen).
- title: kurzer, praegnanter Folientitel. bullets: [[level,text],...], level 0 = Punkt, 1 = Unterpunkt, MAX 6 pro Folie, auf das Wesentliche verdichtet.
- Optionale kv-Keys je Folie: "kicker" (Kurzlabel ueberm Titel, UPPERCASE), "zahl"+"einheit" (KPI-Wert + Label, z.B. "84.000" + "Euro Jahreskosten"), "erklaerung" (Kontextsatz), "ring" (Fortschritt in %, 0-100), "botschaft" (die eine Kernaussage), "meilensteine" ([["JJJJ-MM-TT","Name","fertig|kritisch"],...] fuer Fahrplaene).
Gib AUSSCHLIESSLICH das JSON aus, kein Markdown/Prosa drumherum."""

PLAN_KV_KEYS = {"kicker", "zahl", "einheit", "erklaerung", "ring", "botschaft",
                "meilensteine", "notes"}


def _plan_call(user_prompt, cfg):
    """Ein GLM-Call fuer den Folienplan (2 Versuche). dict oder None."""
    body = json.dumps({
        "model": cfg.get("model", "glm-5.3"),
        "max_tokens": int(cfg.get("max_tokens", 3500)),
        "messages": [
            {"role": "system", "content": PLAN_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    }).encode("utf-8")
    for _versuch in range(2):
        try:
            req = urllib.request.Request(
                cfg["url"], data=body,
                headers={"Content-Type": "application/json", "User-Agent": "slideforce-ai"})
            raw = urllib.request.urlopen(req, timeout=int(cfg.get("timeout", 90))).read()
            msg = (json.loads(raw).get("choices") or [{}])[0].get("message") or {}
            d = _extract_json(msg.get("content") or "")
            if d is None:
                d = _extract_json(msg.get("reasoning_content") or "")
            if isinstance(d, dict) and isinstance(d.get("folien"), list):
                return d
        except (urllib.error.URLError, TimeoutError, OSError, ValueError, KeyError,
                json.JSONDecodeError):
            time.sleep(1.5)
    return None


def _norm_plan_folie(f):
    """KI-Folien-Dict -> Reader-Schema (layout+kind+bullets) oder None."""
    if not isinstance(f, dict):
        return None
    kind = str(f.get("kind") or f.get("layout") or "content").lower()
    if kind not in ("title", "section", "content"):
        kind = "content"
    out = {"kind": kind, "layout": kind,
           "title": str(f.get("title") or f.get("titel") or "").strip()[:120],
           "bullets": []}
    sub = f.get("subtitle") or f.get("untertitel")
    if sub:
        out["subtitle"] = str(sub).strip()[:200]
    if kind == "content" and not out["title"]:
        out["title"] = "Inhalt"
    bl = f.get("bullets")
    if isinstance(bl, list):
        for b in bl[:8]:
            if isinstance(b, (list, tuple)) and len(b) >= 2:
                try:
                    lvl = 1 if int(float(b[0])) > 0 else 0
                except (TypeError, ValueError):
                    lvl = 0
                out["bullets"].append([lvl, str(b[1]).strip()])
            elif isinstance(b, str) and b.strip():
                out["bullets"].append([0, b.strip()])
    for k in PLAN_KV_KEYS:
        v = f.get(k)
        if v is None or v == "":
            continue
        if isinstance(v, (str, int, float)):
            out[k] = v
        elif isinstance(v, list):
            out[k] = ["|".join(str(t) for t in x) if isinstance(x, (list, tuple))
                      else str(x) for x in v]
    hat_inhalt = out["bullets"] or kind in ("title", "section") \
        or any(k in out for k in PLAN_KV_KEYS)
    return out if hat_inhalt else None


def _slides_as_text(slides):
    """Folien-Dicts kompakt als Text abbilden (Plan-Input fuer docx/xlsx/csv)."""
    zeilen = []
    for s in slides or []:
        zeilen.append(f"[{s.get('kind', 'content')}] {s.get('title', '')}")
        if s.get("subtitle"):
            zeilen.append("  untertitel: " + str(s["subtitle"]))
        for lvl, t in (s.get("bullets") or []):
            zeilen.append("  " * (int(lvl) + 1) + "- " + str(t))
        if s.get("table"):
            zeilen.append("  tabelle:")
            for row in s["table"]:
                zeilen.append("    | " + " | ".join(str(c) for c in row) + " |")
        for k, v in s.items():
            if k in ("kind", "layout", "title", "subtitle", "bullets", "table", "image"):
                continue
            zeilen.append(f"  {k}: {v}")
    return "\n".join(zeilen)


def struktur_slide_plan(content_text, ziel_min, ziel_max, config=None):
    """EIN GLM-Call: ROHER Content-Text -> Folienplan im Zielbereich (Reader-Schema).

    Clamp: zu viele Folien -> abschneiden (ok); zu wenige (< ziel_min) -> None,
    dann baut der Aufrufer den normalen Reader-Pfad weiter.
    -> list[slide-dicts] oder None.
    """
    config = config or load_ai_config()
    if not config or not (ziel_min or ziel_max):
        return None
    text = (content_text or "").strip()
    if not text:
        return None
    if len(text) > 60000:                      # Prompt-Schutz bei Riesen-Inputs
        text = text[:60000] + "\n[... Content gekuerzt ...]"
    ziele = []
    if ziel_min:
        ziele.append(f"MINIMAL {ziel_min} Folien")
    if ziel_max:
        ziele.append(f"MAXIMAL {ziel_max} Folien")
    user = ("ERSTELLE EINEN FOLIENPLAN mit " + " und ".join(ziele) + ".\n\n"
            "INHALT (roh):\n<<<\n" + text + "\n>>>\n\n" + PLAN_SCHEMA +
            "\n\nWICHTIG: Die Folienzahl muss IM Zielbereich liegen - die Titelfolie "
            "zaehlt mit. Fasse dicht zusammen, aber erhalte ALLE wichtigen Zahlen, "
            "Namen und Fakten aus dem Input.")
    daten = _plan_call(user, config)
    if daten is None:
        print("[ai] Folienplan: KI-Call gescheitert -> Reader-Pfad", flush=True)
        return None
    plan = [f for f in (_norm_plan_folie(x) for x in daten["folien"]) if f]
    if not plan:
        print("[ai] Folienplan: keine gueltigen Folien -> Reader-Pfad", flush=True)
        return None
    plan[0]["kind"] = plan[0]["layout"] = "title"      # Folie 1 = Cover erzwingen
    if ziel_max and len(plan) > ziel_max:
        plan = plan[:ziel_max]                         # zu viele -> abschneiden ok
    print(f"[ai] Folienplan: {len(plan)} Folien (Ziel min {ziel_min or '-'}/max {ziel_max or '-'})",
          flush=True)
    if ziel_min and len(plan) < ziel_min:
        print(f"[ai] Folienplan: {len(plan)} < Ziel min {ziel_min} -> Reader-Pfad", flush=True)
        return None
    return plan


def build_ai_deck(slides, out_path, config=None, on_progress=None,
                  ziel_min=None, ziel_max=None, content_text=None, master_path=None):
    """Premium-Deck: je Folie KI-Design, sonst statischer profiles-Fallback.

    Engine rendert Header (kopf), Footer (fuss) und Logo selbst und fuehrt
    die KI-Bauanweisungen im Inhaltsbereich aus.
    master_path: wenn gesetzt, lernt das Deck die Master-Marke (Farben+Font
    aus clrScheme, Prompt-Brand-Block + Renderer-Farb-Mapping).
    -> (out_path, stats) mit stats = {"folien","ki","fallback","dauer_s"}.
    """
    with _AI_LOCK:
        snap = None
        sp = SYSTEM_PROMPT
        if master_path:
            try:
                block = master_brand_block(master_path)
                if block:
                    sp = SP_KOPF + block + SP_REST
                    snap = setze_master_theme(master_path)
            except Exception:
                snap = None
        try:
            return _build_ai_deck_intern(slides, out_path, config, on_progress,
                                         ziel_min, ziel_max, content_text, sp)
        finally:
            restore_theme(snap)


def _build_ai_deck_intern(slides, out_path, config, on_progress,
                          ziel_min, ziel_max, content_text, sp):
    t0 = time.time()
    config = config or load_ai_config()
    if ziel_min or ziel_max:                # Min/Max-Regler: ERST Plan, DANN Design-Loop
        plan = struktur_slide_plan(
            content_text if content_text is not None else _slides_as_text(slides),
            ziel_min, ziel_max, config)
        if plan:
            slides = plan
        # plan=None -> Reader-Folien (normaler Pfad), Log kam aus struktur_slide_plan
    gesamt = max(1, len(slides))
    designs = design_folien(slides, config, on_progress, system=sp)
    ki = sum(1 for d in designs if d)

    prs = Presentation()
    prs.slide_width = Inches(P.W)
    prs.slide_height = Inches(P.H)
    for nr, (s, design) in enumerate(zip(slides, designs), 1):
        kind = s.get("kind", "content")
        if design is None:                      # Fallback: statisch, wie build_profile
            sl = P._slide_bg(prs.slides.add_slide(prs.slide_layouts[6]))
            dunkel, ist_titel = P.render_slide_body(sl, s)
            if ist_titel:
                P._fuss_titel(sl, nr, gesamt)
            else:
                P.fuss(sl, nr, gesamt, dunkel=dunkel)
        else:
            dunkel = design.get("hintergrund") == "NAVY"
            sl = prs.slides.add_slide(prs.slide_layouts[6])
            bg = sl.background.fill
            bg.solid()
            bg.fore_color.rgb = P.NAVY if dunkel else (
                P.HELL if design.get("hintergrund") == "HELL" else P.WEISS)
            if kind == "title":                 # Cover: Engine-Band + KI-Meta-Zone
                _cover_engine(sl, s)
                _render_elemente(sl, design["elemente"])
                P._v_dp_logo(sl)
            elif kind == "section":             # dunkle Flaeche steht, KI designt frei
                _render_elemente(sl, design["elemente"], dunkel=dunkel)
                P.fuss(sl, nr, gesamt, dunkel=dunkel)
            else:                               # Standard: kopf + KI-Inhalt + fuss
                P.kopf(sl, s.get("kicker"), s.get("title"))
                _render_elemente(sl, design["elemente"], dunkel=dunkel)
                P.fuss(sl, nr, gesamt, dunkel=dunkel)
        P._v_dp_logo(sl, klein=(kind != "title"))   # dataport-Logo auf jeder Premium-Folie
        if s.get("notes"):
            sl.notes_slide.notes_text_frame.text = str(s["notes"])
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(out_path))
    stats = {"folien": len(slides), "ki": ki, "fallback": len(slides) - ki,
             "dauer_s": round(time.time() - t0, 1)}
    return out_path, stats
