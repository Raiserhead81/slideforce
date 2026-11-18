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

PRIMITIVEN = {"band", "linie", "text", "kachel", "pill", "kartenzeile", "ring", "tabelle"}

FARB_MAP = {  # Namen -> profiles-RGBColor
    "NAVY": P.NAVY, "GOLD": P.GOLD, "ROT": P.ROT, "GRUEN": P.GRUEN,
    "GRÜN": P.GRUEN, "GREEN": P.GRUEN, "GELB": P.AMB, "AMB": P.AMB, "AMBER": P.AMB,
    "GRAU": P.GRAU, "GRAU2": P.GRAU2, "LINE": P.LINE, "HELL": P.HELL,
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
SYSTEM_PROMPT = """Du bist Senior-Slide-Designer bei BRIDGE28 und designt Kundenfolien auf Premium-Niveau: dicht, praezise, hochwertig - niemals leer oder beliebig.

DESIGN-SYSTEM (BRIDGE28):
- Leinwand: 13.33 x 7.5 Zoll (inch), Rand links/rechts MX = 0.55.
- Farben (nutze GENAU diese Namen): NAVY #002846 (dominant, Header, Zahlen, Titel) · GOLD #C9A961 (Akzent: Marker, Linien, Kicker, Ring) · ROT #9E292B · GRUEN #3E7C4F · GELB #B45309 · GRAU #54616E · GRAU2 #8A93A3 (Sekundaertext) · LINE #D0D7E2 (Border) · HELL #F7F9FC (Kartenflaeche) · WEISS · SCHW #1A222B (Fliesstext).
- Typo (Arial): Kicker 10-11pt GOLD bold UPPERCASE (gross geschrieben!) · Folien-Abschnittstitel 15-18pt NAVY bold · Fliesstext 11-13pt SCHW · Labels UPPERCASE 10.5pt GRAU bold · Zahlen dominant gross · Kontext 9.5-10pt GRAU2. Fett im Text mit **so** markieren.
- Stil: weisse/helle Karten mit feiner LINE-Border und GOLD-Marker links; KPI-Kacheln mit farbigem Balken oben; deutliche Zahl-Hierarchie; GOLD sparsam; NAVY tragend.

STRENGES JSON-BAU-VOKABULAR - nur diese Primitive ("typ"-Feld), Koordinaten in inch:
- {"typ":"band","x":..,"y":..,"w":..,"h":..,"farbe":"NAVY"}                        Vollflaechiges Rechteck
- {"typ":"linie","x":..,"y":..,"w":..,"h":0.012,"farbe":"LINE"}                    Feine Linie (h sehr klein)
- {"typ":"text","x":..,"y":..,"w":..,"h":..,"text":"..","size":12,"farbe":"SCHW","bold":false,"align":"left"}
- {"typ":"kachel","x":..,"y":..,"w":..,"h":..,"label":"LABEL","gross":"4,2","unit":"Mio","unter":"plus 12%","kontext":"seit 2023","farbe":"NAVY"}   KPI-Kachel: weisse Karte, LINE-Border, Farbbalken 0.07 oben, Label UPPERCASE, Zahl 30pt NAVY bold + Unit 12.5pt
- {"typ":"pill","x":..,"y":..,"w":..,"h":0.32,"text":"Status","farbe":"GRUEN"}     Abgerundete Status-Pille, weisse bold Schrift
- {"typ":"kartenzeile","x":..,"y":..,"w":..,"h":0.55,"text":"**Migration:** 42 von 60 ...","level":0}   Zeilen-Karte (HELL-Fuellung, LINE-Border, GOLD-Marker links, 13pt); level 1 = Unterpunkt eingerueckt ohne Karte
- {"typ":"ring","x":..,"y":..,"w":3.0,"wert":75,"farbe":"GOLD"}                    Fortschrittsring (Doughnut) mit Prozentwert im Zentrum
- {"typ":"tabelle","x":..,"y":..,"w":12.23,"rows":[["Bereich","Status"],["Build","Gelb"]],"status_spalten":[1]}   Tabelle: Kopfzeile NAVY, Zebra WEISS/HELL; status_spalten = Spalten-Indizes (0-basiert) mit Grun/Gelb/Rot-Status-Pillen

REGELN:
1. Header-Band (NAVY, 0.95 hoch mit Kicker+Titel), Footer und Logo zeichnet die ENGINE - niemals selbst zeichnen. Gestalte nur den Inhaltsbereich.
2. Koordinaten NIE ausserhalb 0..13.33 x 0..7.5. Inhaltsbereich: x 0.55..12.78, y 1.15..6.85 (ausser anders angegeben).
3. Nur die genannten Primitive, keine eigenen Feldnamen. Umlaute korrekt schreiben.
4. PREMIUM-DICHTE: Nutze die Breite (12.23) und Hoehe aus. Kachelreihen: gleiche y/h, Gap 0.2, Balkenfarben NAVY/GOLD mischen (GOLD = Highlight). Kartenzeilen: h 0.55, Gap 0.14-0.35. Weniger als 5 Elemente sind fast immer zu leer; mehr als 16 zu viel.
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
        elif isinstance(v, (str, int, float)):
            z.append(f"{k}: {v}")
    if kind == "title":
        z.append("HINWEIS: Logo, Kicker, Titel, Gold-Linie und Untertitel zeichnet die Engine zentriert. "
                 "Du gestaltest NUR die Zone y 5.4 bis 6.7, x 0.55..12.78 - z.B. 2-4 dezente Meta-Pillen "
                 "(Datum, Autor, Version) oder eine Duftlinie mit Kontextzeile. Maximal 5 Elemente, hintergrund WEISS.")
    elif kind == "section":
        z.append("HINWEIS: Der dunkle NAVY-Hintergrund wird von der Engine gesetzt (hintergrund: NAVY). "
                 "Gestalte Kicker (GOLD, UPPERCASE, 11pt), Kapiteltitel (WEISS, 34-40pt bold), eine kurze "
                 "Gold-Akzentlinie und 2-4 helle kartenzeilen als Vorschau. Textfarben WEISS/GOLD/GRAU2, "
                 "y-Bereich 1.2..6.8.")
    else:
        z.append("HINWEIS: Header (kicker + titel als NAVY-Band) und Footer zeichnet die Engine. "
                 "Gestalte nur y 1.15..6.85, x 0.55..12.78. Setze alle Inhalte dieser Folie vollstaendig "
                 "und dicht um (KPI-Werte als kachel, Listen als kartenzeilen, Tabellen als tabelle mit "
                 "status_spalten). Erfinde keine Zahlen, nutze die gegebenen.")
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


def _ki_call(user_prompt, cfg):
    """Ein GLM-Call (2 Versuche). Gibt validiertes design-dict oder None."""
    body = json.dumps({
        "model": cfg.get("model", "glm-5.3"),
        "max_tokens": int(cfg.get("max_tokens", 3500)),
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
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


def design_folien(slides, config=None, on_progress=None):
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
        return _ki_call(_user_prompt(s, n, m), config)

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
    P.kachel(sl, x, y, w, h, str(el.get("label", "")), str(el.get("gross", "")),
             str(el.get("unit") or ""), str(el.get("unter") or ""),
             str(el.get("kontext") or ""),
             _farbe(farbe) if farbe is not None else None)


def _p_pill(sl, el):
    x, y, w, h = _clamp_box(el, h_d=0.32)
    sh = sl.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE,
                             Inches(x), Inches(y), Inches(w), Inches(h))
    try:
        sh.adjustments[0] = 0.5
    except Exception:
        pass
    sh.fill.solid()
    sh.fill.fore_color.rgb = _farbe(el.get("farbe"), P.GRUEN)
    sh.line.fill.background()
    sh.shadow.inherit = False
    tf = sh.text_frame
    tf.word_wrap = False
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run()
    r.text = str(el.get("text", ""))
    r.font.size = Pt(min(max(_num(el.get("size"), 10.5), 8), 14))
    r.font.bold = True
    r.font.color.rgb = P.WEISS
    r.font.name = P.FONT


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
             "tabelle": _p_tabelle}


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
def build_ai_deck(slides, out_path, config=None, on_progress=None):
    """Premium-Deck: je Folie KI-Design, sonst statischer profiles-Fallback.

    Engine rendert Header (kopf), Footer (fuss) und Logo selbst und fuehrt
    die KI-Bauanweisungen im Inhaltsbereich aus.
    -> (out_path, stats) mit stats = {"folien","ki","fallback","dauer_s"}.
    """
    t0 = time.time()
    config = config or load_ai_config()
    gesamt = max(1, len(slides))
    designs = design_folien(slides, config, on_progress)
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
            if kind == "title":                 # Cover-Geruest zeichnet die Engine
                P._titel_folie(sl, s)
                _render_elemente(sl, design["elemente"])
                P._fuss_titel(sl, nr, gesamt)
            elif kind == "section":             # dunkle Flaeche steht, KI designt frei
                _render_elemente(sl, design["elemente"], dunkel=dunkel)
                P.fuss(sl, nr, gesamt, dunkel=dunkel)
            else:                               # Standard: kopf + KI-Inhalt + fuss
                P.kopf(sl, s.get("kicker"), s.get("title"))
                _render_elemente(sl, design["elemente"], dunkel=dunkel)
                P.fuss(sl, nr, gesamt, dunkel=dunkel)
        if s.get("notes"):
            sl.notes_slide.notes_text_frame.text = str(s["notes"])
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(out_path))
    stats = {"folien": len(slides), "ki": ki, "fallback": len(slides) - ki,
             "dauer_s": round(time.time() - t0, 1)}
    return out_path, stats
