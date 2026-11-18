"""SlideForce: BRIDGE28-Design-Profil. Folien von Hand designt (b28-Export-Stil).

1:1-Port aus bridge28-handbuch/b28-pptx-edit.js: kopf(), fuss(), kachel()
(gleiche Maße W=13.33/H=7.5/MX=0.55, Farben, Typo) plus Zeilen-Karten,
KPI-Kachelreihen (zahl/zahl2/zahl3), Ring-Folien (Doughnut-Chart),
Status-Pills in Tabellen und das BRIDGE-Logo aus b28-folien.js
(tools/gen_logo.py -> slideforce/assets/*.png).
Nur python-pptx-API, keine manuellen XML-Attribute.
"""
import re
import time
from datetime import date, datetime
from pathlib import Path

from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE
from pptx.enum.shapes import MSO_SHAPE, MSO_CONNECTOR
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

NAVY = RGBColor(0x00, 0x28, 0x46)
GOLD = RGBColor(0xC9, 0xA9, 0x61)
ROT = RGBColor(0x9E, 0x29, 0x2B)
GRUEN = RGBColor(0x3E, 0x7C, 0x4F)
AMB = RGBColor(0xB4, 0x53, 0x09)
GRAU = RGBColor(0x54, 0x61, 0x6E)
GRAU2 = RGBColor(0x8A, 0x93, 0xA3)
LINE = RGBColor(0xD0, 0xD7, 0xE2)
HELL = RGBColor(0xF7, 0xF9, 0xFC)
WEISS = RGBColor(0xFF, 0xFF, 0xFF)
SCHW = RGBColor(0x1A, 0x22, 0x2B)
W, H, MX = 13.333, 7.5, 0.55
FONT = "Arial"
BRIDGE = "Dataport"
ASSETS = Path(__file__).parent / "assets"
LOGO_GROSS = ASSETS / "bridge_logo.png"   # Bruecke + Schriftzug (Titelfolie)
LOGO_MINI = ASSETS / "bridge_mini.png"    # Footer-Emblem (jede Folie)
LOGO_DP = ASSETS / "vorlage_dataport.png"  # Dataport-Schriftzug (Vorlage-Profil)


# ---------------------------------------------------------------- Bausteine
def _rect(sl, x, y, w, h, color, line=None):
    sh = sl.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    sh.fill.solid()
    sh.fill.fore_color.rgb = color
    if line is None:
        sh.line.fill.background()
    else:
        sh.line.color.rgb = line
        sh.line.width = Pt(1)
    sh.shadow.inherit = False
    return sh


def _text(sl, x, y, w, h, text, size, color, bold=False, align=PP_ALIGN.LEFT,
          spacing=None, italic=False):
    """spacing (CharSpacing) kann python-pptx nicht - wird ignoriert."""
    tb = sl.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.alignment = align
    r = p.add_run()
    r.text = text
    r.font.size = Pt(size)
    r.font.bold = bold
    r.font.italic = italic
    r.font.color.rgb = color
    r.font.name = FONT
    return tb


def _logo(sl, png, x, y, h):
    """PNG einbetten, falls vorhanden (Fallback: kein Logo). Gibt Breite in Inch zurueck."""
    if not png.is_file():
        return 0.0
    pic = sl.shapes.add_picture(str(png), Inches(x), Inches(y), height=Inches(h))
    return pic.width / 914400


def kopf(sl, kicker, titel):
    """NAVY-Band 0.95h wie b28-Export: Kicker exakt 'BRIDGE28 · KW NN · THEMA'
    (gold 10pt bold), Titel weiss 23pt, Dataport-Marke rechts."""
    _rect(sl, 0, 0, W, 0.95, NAVY)
    thema = (str(kicker).strip() if kicker else "") or "Wochenbericht"
    kicker_line = f"BRIDGE28 \u00b7 {time.strftime('KW %V', time.gmtime())} \u00b7 {thema}"
    _text(sl, MX, 0.09, 9.6, 0.28, kicker_line.upper(), 10, GOLD, bold=True)
    _text(sl, MX, 0.32, 10.6, 0.52, titel or "", 23, WEISS, bold=True)
    _text(sl, W - 1.75, 0.33, 1.25, 0.34, BRIDGE, 10.5, WEISS, align=PP_ALIGN.RIGHT)


def fuss(sl, nr, gesamt, dunkel=False):
    """b28 1:1: LINE-Trennlinie, BRIDGE28 · KW links (mit Mini-Logo), Folie n/g rechts."""
    kw = time.strftime("KW %V", time.gmtime())
    farbe = GOLD if dunkel else GRAU2
    if not dunkel:
        _rect(sl, MX, H - 0.42, W - 2 * MX, 0.012, LINE)
    lw = _logo(sl, LOGO_MINI, MX, H - 0.385, 0.165)
    _text(sl, MX + lw + 0.1, H - 0.37, 6, 0.28, f"BRIDGE28 \u00b7 {kw}", 9, farbe)
    _text(sl, W - 2.55, H - 0.37, 2.0, 0.28, f"Folie {nr} / {gesamt}", 9, farbe,
          align=PP_ALIGN.RIGHT)


def kachel(sl, x, y, w, h, label, gross, unit, unter, kontext, farbe=None, status=None):
    """KPI-Kachel wie b28-Export: weisse Karte, Border in der Status-Farbe
    (LINE als neutraler Fallback), Farbbalken 0.07 oben, Label uppercase 10.5
    GRAU, Zahl 30pt NAVY bold + Unit 12.5 GRAU, Unterzeile 10.5 bold,
    Kontext 9.5 GRAU2; optional Status-Pill (z.B. 'Am Limit') unten links."""
    balken = farbe if farbe is not None else NAVY
    border = balken if balken not in (NAVY, WEISS) else LINE
    pad = 0.16
    _rect(sl, x, y, w, h, WEISS, line=border)
    _rect(sl, x, y, w, 0.07, balken)
    _text(sl, x + pad, y + 0.17, w - 2 * pad, 0.28, (label or "").upper(), 10.5, GRAU, bold=True)
    tb = sl.shapes.add_textbox(Inches(x + pad), Inches(y + 0.48), Inches(w - 2 * pad), Inches(0.72))
    p = tb.text_frame.paragraphs[0]
    r = p.add_run()
    r.text = gross or ""
    r.font.size = Pt(30)
    r.font.bold = True
    r.font.color.rgb = NAVY
    r.font.name = FONT
    if unit:
        r2 = p.add_run()
        r2.text = " " + unit
        r2.font.size = Pt(12.5)
        r2.font.color.rgb = GRAU
        r2.font.name = FONT
    if unter:
        _text(sl, x + pad, y + 1.24, w - 2 * pad, 0.28, unter, 10.5, GRAU, bold=True)
    if status:
        sf = _status_farbe(status) or balken
        pw = min(1.9, w - 2 * pad)
        _pill(sl, x + pad, y + 1.54, pw, 0.34, status, sf, size=10)
        if kontext:
            _text(sl, x + pad, y + h - 0.42, w - 2 * pad, 0.28, kontext, 9.5, GRAU2)
    elif kontext:
        _text(sl, x + pad, y + h - 0.44, w - 2 * pad, 0.28, kontext, 9.5, GRAU2)


def _inline(text):
    """**fett** -> (text, True/False)-Runs."""
    out = []
    for part in re.split(r"(\*\*.+?\*\*)", text):
        if not part:
            continue
        if part.startswith("**") and part.endswith("**"):
            out.append((part[2:-2], True))
        else:
            out.append((part, False))
    return out or [("", False)]


def _runs_textbox(sl, x, y, w, h, text, size, base_color=SCHW, bold_color=NAVY,
                  anchor=MSO_ANCHOR.MIDDLE):
    tb = sl.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    p = tf.paragraphs[0]
    for part, bold in _inline(text):
        r = p.add_run()
        r.text = part
        r.font.size = Pt(size)
        r.font.bold = bold
        r.font.color.rgb = bold_color if bold else base_color
        r.font.name = FONT
    return tb


def _zeilen_karten(sl, items, x=MX, y=1.35, w=W - 2 * MX, unten=6.85):
    """Haupt-Bullets als Zeilen-Karten (HELL-Fill, LINE-Border, 0.55h, gold Marker
    0.08 breit links, 13pt), Unterpunkte eingerueckt ohne Karte (12pt).
    Karten verteilen sich ueber den available Bereich (dicht, keine Einsamkeit)."""
    zeilen = [(0, t) for lvl, t in (items or []) if not lvl] + \
             [(1, t) for lvl, t in (items or []) if lvl]
    if not zeilen:
        zeilen = [(0, "")]
    n_karten = sum(1 for lvl, _ in zeilen if lvl == 0)
    card_h, sub_h = 0.55, 0.32
    gap_c, gap_cs, gap_s = 0.14, 0.08, 0.04
    total = 0.0
    for i, (lvl, _) in enumerate(zeilen):
        total += card_h if lvl == 0 else sub_h
        if i:
            total += gap_c if lvl == 0 else (gap_cs if zeilen[i - 1][0] == 0 else gap_s)
    avail = unten - y
    if n_karten > 1 and total < avail:            # Luft fair auf Kartenabstaende verteilen
        extra = min((avail - total) / (n_karten - 1), 0.42 - gap_c)
        gap_c += extra
    elif total > avail:                            # Notfall: stauchen
        f = avail / total
        card_h, sub_h, gap_c, gap_cs, gap_s = (v * f for v in (card_h, sub_h, gap_c, gap_cs, gap_s))
    cy = y
    for i, (lvl, text) in enumerate(zeilen):
        if i:
            cy += gap_c if lvl == 0 else (gap_cs if zeilen[i - 1][0] == 0 else gap_s)
        if lvl == 0:
            _rect(sl, x, cy, w, card_h, HELL, line=LINE)
            _rect(sl, x, cy, 0.08, card_h, GOLD)
            _runs_textbox(sl, x + 0.26, cy + 0.02, w - 0.42, card_h - 0.04, text, 13)
        else:
            _rect(sl, x + 0.55, cy + sub_h / 2 - 0.015, 0.16, 0.03, GOLD)
            _runs_textbox(sl, x + 0.82, cy - 0.015, w - 0.95, sub_h + 0.03, text, 12,
                          base_color=GRAU, bold_color=NAVY, anchor=MSO_ANCHOR.TOP)
        cy += card_h if lvl == 0 else sub_h


def _status_farbe(value):
    """Status-Wort -> Pill-/Punkt-Farbe (Wortanfang, kein Substring-Match)."""
    t = str(value).strip().lower()
    if re.match(r"^(gr\u00fcn|gruen|green|fertig|ok|erledigt)\b", t):
        return GRUEN
    if re.match(r"^(gelb|amber|warnung|riskant)\b", t):
        return AMB
    if re.match(r"^(rot|red|kritisch|versp\u00e4tet|verspaetet|verzug|blockiert)\b", t):
        return ROT
    if re.match(r"^(am limit|limit)\b", t):
        return GOLD
    if re.match(r"^(in arbeit|l\u00e4uft|laeuft|running|aktiv)\b", t):
        return NAVY
    if re.match(r"^(offen|geplant|wartet)\b", t):
        return GRAU
    return None


def _pill(sl, x, y, w, h, text, farbe, size=10, textfarbe=None):
    """Abgerundete Status-Pill: farbiger Fill + kontrastierter bold Text
    (GOLD-Fill -> NAVY-Schrift wie 'Am Limit' im b28-Export, sonst WEISS)."""
    sh = sl.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE,
                             Inches(x), Inches(y), Inches(w), Inches(h))
    try:
        sh.adjustments[0] = 0.5
    except Exception:
        pass
    sh.fill.solid()
    sh.fill.fore_color.rgb = farbe
    sh.line.fill.background()
    sh.shadow.inherit = False
    tf = sh.text_frame
    tf.word_wrap = False
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run()
    r.text = str(text)
    r.font.size = Pt(size)
    r.font.bold = True
    r.font.color.rgb = textfarbe if textfarbe is not None else (
        NAVY if farbe == GOLD else WEISS)
    r.font.name = FONT
    return sh


# ---------------------------------------------------------------- Folienarten
def _slide_bg(sl):
    sl.background.fill.solid()
    sl.background.fill.fore_color.rgb = WEISS
    return sl


def _titel_folie(sl, s):
    _rect(sl, 0, 0, W, 0.16, NAVY)
    _rect(sl, 0, H - 0.16, W, 0.16, NAVY)
    lw = 1.9                                    # 180px-Aequivalent (96 dpi)
    _logo(sl, LOGO_GROSS, W / 2 - lw / 2, 1.30, lw * 120 / 200)
    _text(sl, MX, 2.62, W - 2 * MX, 0.4, (s.get("kicker") or "BRIDGE28").upper(), 13, GOLD,
          bold=True, align=PP_ALIGN.CENTER)
    _text(sl, MX, 3.08, W - 2 * MX, 1.0, s.get("title") or "", 32, NAVY, bold=True,
          align=PP_ALIGN.CENTER)
    _rect(sl, W / 2 - 1.6, 4.42, 3.2, 0.03, GOLD)
    if s.get("subtitle"):
        _text(sl, MX, 4.74, W - 2 * MX, 0.4, s["subtitle"], 15, GRAU, align=PP_ALIGN.CENTER)
    if s.get("meta"):                          # b28-Metazeile: Projekt · Verfahren · Gremium
        _text(sl, MX, 5.18, W - 2 * MX, 0.3, s["meta"], 10.5, GRAU2, align=PP_ALIGN.CENTER)
    _text(sl, MX, 6.42, W - 2 * MX, 0.26,
          time.strftime("automatisiert erzeugt am %d.%m.%Y", time.gmtime()),
          9, GRAU2, align=PP_ALIGN.RIGHT)
    if s.get("status"):                        # Status-Pill wie 'Am Limit' (gold/NAVY)
        st = str(s["status"])
        _pill(sl, W / 2 - 0.85, 5.55, 1.7, 0.34, st, _status_farbe(st) or GOLD, size=10.5)
    _text(sl, 2, 6.05, W - 4, 0.3, "BRIDGE28 \u00b7 Projektbericht", 10.5, GRAU2,
          align=PP_ALIGN.CENTER)


def _kapitel_folie(sl, s):
    _rect(sl, 0, 0, W, H, NAVY)
    _text(sl, MX, 2.7, W - 2 * MX, 0.4, "KAPITEL", 13, GOLD, bold=True)
    _text(sl, MX, 3.15, W - 2 * MX, 1.1, s.get("title") or "", 36, WEISS, bold=True)
    _rect(sl, MX, 4.35, 1.4, 0.05, GOLD)


def _content_folie(sl, s):
    kopf(sl, s.get("kicker"), s.get("title"))
    items = s.get("bullets") or []
    img = s.get("image")
    if img and Path(img).is_file():
        w_text = W - 2 * MX - 4.3
        _zeilen_karten(sl, items, x=MX, y=1.35, w=w_text)
        sl.shapes.add_picture(str(img), Inches(MX + w_text + 0.3), Inches(1.5), width=Inches(4.0))
    else:
        _zeilen_karten(sl, items)


def _zahl_suffixe(s):
    """zahl, zahl2, zahl3, zahl4 ... in Reihenfolge (max. 4 Kacheln, b28-Raster)."""
    keys = [k for k in s if re.fullmatch(r"zahl\d*", str(k))]
    keys.sort(key=lambda k: (k != "zahl", len(k), k))
    return [k[4:] for k in keys[:4]]


def _kpi_folie(sl, s):
    kopf(sl, s.get("kicker"), s.get("title"))
    suffixe = _zahl_suffixe(s)
    n = max(1, len(suffixe))
    gap = 0.2 if n > 1 else 0.0
    cw = (W - 2 * MX - gap * (n - 1)) / n
    for i, suf in enumerate(suffixe or [""]):
        get = (lambda k: s.get(k + suf)) if suf else (lambda k: s.get(k))
        label = (get("label") or (s.get("title") if not suf else f"Kennzahl {suf}"))
        status = (get("status") or (s.get("status") if not suf else None))
        sfarbe = _status_farbe(status) if status else NAVY
        kachel(sl, MX + i * (cw + gap), 1.35, cw, 2.35, label,
               get("zahl") or "", get("einheit") or "",
               get("erklaerung") or "", get("einordnung") or "", sfarbe,
               status=status)
    rest = s.get("bullets") or []
    if rest:
        _zeilen_karten(sl, rest, y=4.0, unten=6.85)


def _ring_folie(sl, s, pct):
    kopf(sl, s.get("kicker"), s.get("title"))
    cd = CategoryChartData()
    cd.categories = ["Wert", "Rest"]
    cd.add_series("Anteil", (pct, max(0.0, 100.0 - pct)))
    size = 2.4                                   # ~128px-Kachel-Massstab bei 96 dpi x1.8
    gf = sl.shapes.add_chart(XL_CHART_TYPE.DOUGHNUT, Inches(MX + 0.1), Inches(1.5),
                             Inches(size), Inches(size), cd)
    ch = gf.chart
    ch.has_legend = False
    ch.has_title = False
    pts = list(ch.plots[0].series[0].points)
    for pt, farbe in zip(pts, (GOLD, NAVY)):
        pt.format.fill.solid()
        pt.format.fill.fore_color.rgb = farbe
        pt.format.line.color.rgb = WEISS
        pt.format.line.width = Pt(1.5)
    cx = MX + 0.1 + size / 2
    _text(sl, cx - 0.9, 1.5 + size / 2 - 0.28, 1.8, 0.58, f"{pct:g} %", 30, NAVY,
          bold=True, align=PP_ALIGN.CENTER)
    # Label UNTER dem Ring (b28: Ring-Kachel mit Label unter der Grafik)
    _text(sl, cx - 1.2, 1.5 + size + 0.12, 2.4, 0.28,
          (s.get("label") or "Fortschritt").upper(), 10.5, GRAU, bold=True,
          align=PP_ALIGN.CENTER)
    # Infokarte rechts: Label, Erklaerung, Einordnung
    x = MX + 0.1 + size + 0.45
    w = W - MX - x
    kachel(sl, x, 1.5, w, 2.35, s.get("label") or "Fortschritt",
           "", "", s.get("erklaerung") or "", s.get("einordnung") or "", GOLD)
    rest = s.get("bullets") or []
    if rest:
        _zeilen_karten(sl, rest, y=4.55, unten=6.85)


def _statement_folie(sl, s):
    kopf(sl, s.get("kicker"), s.get("title"))
    _text(sl, MX + 0.28, 1.45, 1.2, 1.2, "\u201e", 88, GOLD, bold=True)
    _rect(sl, MX, 2.35, 0.09, 2.3, GOLD)
    _text(sl, MX + 0.5, 2.35, W - 2 * MX - 0.6, 2.3, s.get("botschaft") or "", 30, NAVY,
          bold=True)
    if s.get("zusatz"):
        _text(sl, MX + 0.5, 5.05, W - 2 * MX - 0.6, 0.6, s["zusatz"], 14, GRAU2)


def _pill_ueber_tabelle(sl, tbl, rows):
    """Status-Zellen ('Grün','Gelb','Rot','Am Limit', ...) als abgerundete
    Pills MIT farbigem Fill + weissem Text UEBER der Zelle zeichnen
    (b28-Look); Zelltext wird geleert, Geometrie aus Row/Col-Massen."""
    try:
        x0, y0 = tbl._graphic_frame.left / 914400, tbl._graphic_frame.top / 914400
    except Exception:
        return
    for r, row in enumerate(rows):
        if r == 0:
            continue
        for c, val in enumerate(row):
            farbe = _status_farbe(val)
            if farbe is None:
                continue
            try:
                cx = x0 + sum(tbl.columns[i].width for i in range(c)) / 914400
                cy = y0 + sum(tbl.rows[i].height for i in range(r)) / 914400
                cw = tbl.columns[c].width / 914400
                ch = tbl.rows[r].height / 914400
            except Exception:
                continue
            tbl.cell(r, c).text = ""
            pw = min(max(0.95, len(str(val)) * 0.094 + 0.4), cw - 0.14)
            _pill(sl, cx + (cw - pw) / 2, cy + (ch - 0.30) / 2, pw, 0.30,
                  val, farbe, size=10.5)


def _tabellen_folie(sl, s):
    kopf(sl, s.get("kicker"), s.get("title"))
    rows = s.get("table") or []
    if not rows:
        return
    ncols = max(len(r) for r in rows)
    nrows = len(rows)
    tw = W - 2 * MX
    row_h = min(0.62, max(0.40, 5.4 / nrows))
    th = row_h * nrows
    gf = sl.shapes.add_table(nrows, ncols, Inches(MX), Inches(1.35), Inches(tw), Inches(th))
    tbl = gf.table
    tbl.first_row = False
    tbl.horz_banding = False
    for r in range(nrows):
        tbl.rows[r].height = Inches(row_h)
    for r, row in enumerate(rows):
        for c in range(ncols):
            cell = tbl.cell(r, c)
            cell.text = str(row[c]) if c < len(row) else ""
            cell.margin_left = Inches(0.1)
            cell.margin_top = Inches(0.03)
            cell.margin_bottom = Inches(0.03)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            pill = None if r == 0 else _status_farbe(cell.text)
            fill = cell.fill
            fill.solid()
            if r == 0:
                fill.fore_color.rgb = NAVY
            elif pill is not None:
                fill.fore_color.rgb = pill
            else:
                fill.fore_color.rgb = HELL if r % 2 else WEISS
            for p in cell.text_frame.paragraphs:
                for run in p.runs:
                    run.font.size = Pt(11.5 if r == 0 else 11)
                    run.font.bold = r == 0 or pill is not None
                    run.font.name = FONT
                    run.font.color.rgb = WEISS if (r == 0 or pill is not None) else SCHW
    _pill_ueber_tabelle(sl, tbl, rows)


# ---------------------------------------------------------------- Bruecke
def _parse_datum(v):
    """'2026-12-31' / '31.12.2026' / '31.12.26' -> date (oder None)."""
    s = str(v).strip()
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d.%m.%y", "%Y-%m", "%m.%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def _datum_kurz(d):
    return f"{d.day:02d}.{d.month:02d}.{str(d.year)[2:]}"


def _zeitstrahl_punkt(datum, label, status="offen"):
    """('2026-12-31','M0','kritisch') -> (date, label, status); ungueltig -> None."""
    d = _parse_datum(datum)
    if d is None:
        return None
    return (d, str(label or ""), str(status or "offen").strip().lower())


def _bruecke(sl, x, y, w, meilensteine, heute=None, farben=None):
    """BRIDGE28-Bruecken-Zeitstrahl (Referenz ref28-03):
    goldener Spannbogen (quadratische Bezier als Freeform), 2 NAVY-Pylonen,
    Meilenstein-Punkte AUF dem Bogen (x proportional zum Datum, y=Bogenformel),
    Datum-/Label-Faehnchen, gestrichelter HEUTE-Marker, Countdown-Chip (gold),
    Quartals-Achse unter dem Deck.
    farben=(BOGEN, PYLONEN, PILLTEXT) fuer alternatives Farbschema (vorlage)."""
    BOG, PYL, PILLTXT = (GOLD, NAVY, NAVY) if farben is None else farben
    raw = []
    for m in (meilensteine or []):
        if isinstance(m, str) and "|" in m:
            teile = [t.strip() for t in m.split("|")]
            while len(teile) < 3:
                teile.append("")
            raw.append(_zeitstrahl_punkt(*teile[:3]))
        elif isinstance(m, (list, tuple)) and len(m) >= 2:
            raw.append(_zeitstrahl_punkt(m[0], m[1], m[2] if len(m) > 2 else "offen"))
        elif isinstance(m, dict):
            raw.append(_zeitstrahl_punkt(m.get("datum"), m.get("label"),
                                         m.get("status", "offen")))
    punkte = [p for p in raw if p]
    if len(punkte) < 2:
        return
    punkte.sort(key=lambda p: p[0])
    d0, d1 = punkte[0][0], punkte[-1][0]
    x0, x1 = x + 0.15, x + w - 0.15
    deck_y = y + 3.0
    hoehe = 1.85
    ctrl_y = deck_y - 2 * hoehe                 # Scheitel = deck_y - hoehe

    def bogen(t):                               # quadratische Bezier P0-C-P1
        return ((1 - t) ** 2 * x0 + 2 * (1 - t) * t * ((x0 + x1) / 2)
                + t ** 2 * x1,
                (1 - t) ** 2 * deck_y + 2 * (1 - t) * t * ctrl_y + t ** 2 * deck_y)

    def tx(d):
        span = max(1, (d1 - d0).days)
        return min(1.0, max(0.0, (d - d0).days / span))

    # Deck (Fahrbahn) + 2 Pylonen, die ueber den Bogen ragen
    _rect(sl, x0 - 0.05, deck_y, (x1 - x0) + 0.1, 0.05, PYL)
    pyl_top = deck_y - hoehe - 0.5
    for px in (x0 + 0.12, x1 - 0.24):
        _rect(sl, px, pyl_top, 0.12, deck_y - pyl_top + 0.05, PYL)
        _rect(sl, px - 0.05, pyl_top, 0.22, 0.06, BOG)

    # Goldener Spannbogen als Freeform-Polyline
    pts = [bogen(i / 48) for i in range(49)]
    ff = sl.shapes.build_freeform(Inches(pts[0][0]), Inches(pts[0][1]), scale=1.0)
    ff.add_line_segments([(Inches(px), Inches(py)) for px, py in pts[1:]], close=False)
    bogen_sh = ff.convert_to_shape()
    bogen_sh.fill.background()
    bogen_sh.line.color.rgb = BOG
    bogen_sh.line.width = Pt(2.75)
    bogen_sh.shadow.inherit = False

    # Meilenstein-Punkte AUF dem Bogen + Faehnchen (Datum bold, Label darunter,
    # bei engen Abstaenden alternierend versetzt, damit Labels nicht kollidieren;
    # Rand-Faehnchen bleiben im Deck (Studio-Critic: nichts am Pfosten abschneiden)
    flaggen = []
    letzter_fx = -9.9
    for i, (d, label, status) in enumerate(punkte):
        px, py = bogen(tx(d))
        sf = _status_farbe(status) or PYL
        dot = sl.shapes.add_shape(MSO_SHAPE.OVAL, Inches(px - 0.095), Inches(py - 0.095),
                                  Inches(0.19), Inches(0.19))
        dot.fill.solid()
        dot.fill.fore_color.rgb = WEISS
        dot.line.color.rgb = sf
        dot.line.width = Pt(2.25)
        dot.shadow.inherit = False
        dy = 0.14 if i % 2 == 0 else 0.52
        fx = min(max(px - 0.62, x0 - 0.35), x1 - 1.24 + 0.35)
        if abs(fx - letzter_fx) < 1.30:            # horizontale Naehe -> ueber Kurve
            dy = -0.68
        letzter_fx = fx
        _text(sl, fx, py + dy, 1.24, 0.24, _datum_kurz(d), 10, PYL,
              bold=True, align=PP_ALIGN.CENTER)
        if label:
            _text(sl, fx, py + dy + 0.24, 1.24, 0.42, label, 9, GRAU,
                  align=PP_ALIGN.CENTER)
        flaggen.append((fx, py + dy))

    # HEUTE-Marker: gestrichelte rote Vertikale bis zum Deck + Label
    if heute is None:
        heute = date.today()
    elif not isinstance(heute, date):
        heute = _parse_datum(heute) or date.today()
    heute = min(d1, max(d0, heute))        # clamp: Marker bleibt im Spannweiten-Bereich
    if d0 <= heute <= d1:
        hx, hy = bogen(tx(heute))
        cy = hy + 0.32
        while cy < deck_y - 0.02:
            _rect(sl, hx - 0.017, cy, 0.034, min(0.14, deck_y - cy), ROT)
            cy += 0.20
        # HEUTE-Label weicht Flaggen aus (Studio-Critic: keine Kollision links)
        lx = min(max(hx - 0.55, x0 - 0.10), x1 - 1.0)
        ly = hy - 0.38
        for _versuch in range(4):
            kollision = any(abs(lx - fx) < 1.2 and abs(ly - fy) < 0.75
                            for fx, fy in flaggen)
            if not kollision:
                break
            ly = hy - 0.38 - 0.40 * (_versuch + 1)     # hoeher ueber den Bogen
        _text(sl, lx, ly, 1.1, 0.26, "HEUTE", 9.5, ROT, bold=True,
              align=PP_ALIGN.CENTER)

    # Countdown-Chip (gold, NAVY-Schrift): Tage bis zum letzten Meilenstein
    tage = (d1 - heute).days
    if tage > 0:
        _pill(sl, x1 - 2.9, y - 0.02, 2.75, 0.34,
              f"NOCH {tage} TAGE \u00b7 {punkte[-1][1] or _datum_kurz(d1)}", BOG,
              size=9.5, textfarbe=PILLTXT)

    # Quartals-Achse unter dem Deck
    achse_y = deck_y + 0.34
    _rect(sl, x0, achse_y, x1 - x0, 0.016, LINE)
    q = date(d0.year, (d0.month - 1) // 3 * 3 + 1, 1)
    while q <= d1:
        if q > d0:
            qx = x0 + tx(q) * (x1 - x0)
            ql = f"Q{(q.month - 1) // 3 + 1} {str(q.year)[2:]}"
            koll = any(abs(qx - (fx + 0.62)) < 0.95 and fy + 0.70 > achse_y
                       for fx, fy in flaggen)
            if not koll:               # Achsenlabel nur ohne Flaggen-Kollision
                _rect(sl, qx - 0.02, achse_y - 0.07, 0.04, 0.15, GRAU2)
                _text(sl, qx - 0.5, achse_y + 0.12, 1.0, 0.24, ql, 9, GRAU,
                      bold=True, align=PP_ALIGN.CENTER)
        q = date(q.year + (q.month + 2) // 12, (q.month + 2) % 12 + 1, 1)


def _zeitstrahl_folie(sl, s):
    kopf(sl, s.get("kicker"), s.get("title"))
    _bruecke(sl, MX, 1.6, W - 2 * MX, s.get("zeitstrahl") or [], s.get("heute"))


# ---------------------------------------------------------------- Bau
def _ring_wert(s):
    """'ring: 75' / '75 %' / '62,5' -> 0..100 oder None."""
    if s.get("ring") is None:
        return None
    m = re.search(r"\d+(?:[.,]\d+)?", str(s["ring"]))
    if m is None:
        return None
    return max(0.0, min(100.0, float(m.group(0).replace(",", "."))))


def render_slide_body(sl, s):
    """Eine Folie nach Art/Inhalt statisch rendern (ohne Footer/Notes).
    Wiederverwendet vom KI-Design (ai_design) als Fallback fuer Einzel-Folien.
    Gibt (dunkel, ist_titel) zurueck - Footer-Aufrufer entscheidet fuss/fuss_titel."""
    kind = s.get("kind", "content")
    ring = _ring_wert(s) if s.get("ring") is not None else None
    if kind == "title":
        _titel_folie(sl, s)
        return False, True
    if kind == "section":
        _kapitel_folie(sl, s)
        return True, False
    if s.get("zeitstrahl"):
        _zeitstrahl_folie(sl, s)
        return False, False
    if ring is not None:
        _ring_folie(sl, s, ring)
        return False, False
    if _zahl_suffixe(s):
        _kpi_folie(sl, s)
        return False, False
    if s.get("botschaft"):
        _statement_folie(sl, s)
        return False, False
    if s.get("table"):
        _tabellen_folie(sl, s)
        return False, False
    _content_folie(sl, s)
    return False, False


def build_profile(slides, out_path):
    """BRIDGE28-Design-Profil: handdesignte Folien im Stil des b28-Exports."""
    prs = Presentation()
    prs.slide_width = Inches(W)
    prs.slide_height = Inches(H)
    gesamt = max(1, len(slides))
    for nr, s in enumerate(slides, 1):
        sl = _slide_bg(prs.slides.add_slide(prs.slide_layouts[6]))
        dunkel, ist_titel = render_slide_body(sl, s)
        if ist_titel:
            _fuss_titel(sl, nr, gesamt)   # Footer ueber dem unteren NAVY-Band
        else:
            fuss(sl, nr, gesamt, dunkel=dunkel)
        if s.get("notes"):
            sl.notes_slide.notes_text_frame.text = str(s["notes"])
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(out_path))
    return []


def _fuss_titel(sl, nr, gesamt):
    kw = time.strftime("KW %V", time.gmtime())
    lw = _logo(sl, LOGO_MINI, MX, H - 0.53, 0.165)
    _text(sl, MX + lw + 0.1, H - 0.515, 6, 0.28, f"BRIDGE28 \u00b7 {kw}", 9, GRAU2)
    _text(sl, W - 2.55, H - 0.515, 2.0, 0.28, f"Folie {nr} / {gesamt}", 9, GRAU2,
          align=PP_ALIGN.RIGHT)


# ================================================================ Vorlage-Profil
"""Vorstandsvorlagen-Design (fmt=vorpptx): heller Vorstands-Look wie
BRIDGE_Vorstandstermin/NGN_Bremen_Vorstandsvorlage (Vermessung 18.11.2026):
Links-Sidebar 'INHALT' auf Teil-/Titelfolien, schwebender Kicker + grosser
Titel + petrol Lead auf Content-Folien, Karten in F4F5F6 (KPI-Variante mit
40pt petrol Zahl + LINE + Sub-Werten, Punkt-Variante mit nummeriertem Quadrat),
Tabellen mit petrol Kopf, Statement-Karte mit rotem Akzent. Deterministisch,
keine KI."""
V_KARTE = RGBColor(0xF4, 0xF5, 0xF6)
V_PETROL = RGBColor(0x39, 0x75, 0x6F)
V_DUNKEL = RGBColor(0x39, 0x42, 0x4A)
V_GRAU = RGBColor(0x62, 0x6D, 0x76)
V_TEXT = RGBColor(0x3A, 0x3A, 0x3A)
V_LINE = RGBColor(0xDC, 0xE0, 0xE4)
V_INAKT_N = RGBColor(0xB5, 0xBC, 0xC3)
V_INAKT_T = RGBColor(0x9A, 0xA3, 0xAB)
V_TINT_GOLD = RGBColor(0xFB, 0xF0, 0xDC)
V_SB_W = 5.17          # Sidebar-Breite (Referenz 0..5.17)
V_BRAND = "Vorstandsvorlage"


def _v_dp_logo(sl, klein=False):
    """Dataport-Schriftzug oben rechts (aus der Vorlage-PPTX, Layout 1/3):
    Titel-/Teil-Folien 2.46x0.85 @10.09/0.40, Content 1.45x0.50 @11.22/0.41."""
    if not LOGO_DP.is_file():
        return
    if klein:
        sl.shapes.add_picture(str(LOGO_DP), Inches(11.22), Inches(0.41),
                              width=Inches(1.45))
    else:
        sl.shapes.add_picture(str(LOGO_DP), Inches(10.09), Inches(0.40),
                              width=Inches(2.46))


def _v_hline(sl, x, y, w):
    ln = sl.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x), Inches(y),
                                 Inches(x + w), Inches(y))
    ln.line.color.rgb = V_LINE
    ln.line.width = Pt(1.2)
    ln.shadow.inherit = False
    return ln


def _v_short(t, n=30):
    """Sidebar-Label: Teil vor ':' wenn lang, sonst kuerzen."""
    t = re.sub(r"\s+", " ", str(t or "")).strip()
    left = t.split(":", 1)[0].strip()
    if len(left) >= 4:
        t = left
    return (t[:n - 1] + "\u2026") if len(t) > n else t


def _v_teile(slides):
    """teile aus 'teile'-Key ( '|'-Zeilen) oder automatisch aus section-Folien.
    Gibt (teile, part_of): teile=[(nr, titel, [(nr, label), ..])],
    part_of={slide-idx: teil-idx}."""
    expl = None
    for s in slides:
        if s.get("teile"):
            expl = list(s["teile"])
            break
    secs = [i for i, s in enumerate(slides) if s.get("kind") == "section"]
    if not secs:
        return [], {}
    teile, part_of = [], {}
    for pi, si in enumerate(secs):
        end = secs[pi + 1] if pi + 1 < len(secs) else len(slides)
        nr, titel = f"{si + 1:02d}", f"Teil {pi + 1} \u00b7 {slides[si].get('title') or ''}"
        if expl and pi < len(expl):
            e_nr, _, e_t = str(expl[pi]).partition("|")
            nr = e_nr.strip() or nr
            titel = e_t.strip() or titel
        subs = [(f"{i + 1:02d}", _v_short(slides[i].get("title")))
                for i in range(si + 1, end) if slides[i].get("kind") == "content"]
        teile.append((nr, titel, subs))
        for i in range(si, end):
            part_of[i] = pi
    return teile, part_of


def _v_sidebar(sl, teile, aktiv=None):
    """Linke INHALT-Sidebar (F4F5F6, volle Hoehe): 'INHALT' rot, je Teil
    rote Nummer 14pt + Titel 13pt; AKTIVER Teil bold mit Sub-Foliennummern."""
    _rect(sl, 0, 0, V_SB_W, H, V_KARTE)
    _text(sl, 0.73, 0.75, 3.9, 0.30, "INHALT", 11, ROT, bold=True)
    y = 1.25
    for i, (nr, titel, subs) in enumerate(teile):
        ist = i == aktiv
        _text(sl, 0.73, y, 0.55, 0.40, nr, 14,
              ROT if ist or aktiv is None else V_INAKT_N, bold=True)
        _text(sl, 1.35, y + 0.02, 3.6, 0.40, titel, 13,
              V_DUNKEL if ist or aktiv is None else V_INAKT_T, bold=ist)
        y += 0.5
        if ist and subs:
            for snr, lab in subs:
                _text(sl, 1.35, y, 0.45, 0.30, snr, 11, ROT, bold=True)
                _text(sl, 1.85, y, 3.1, 0.30, lab, 11, V_TEXT)
                y += 0.34
            y += 0.16          # Abstand nach Sub-Block (Referenz 3.41 -> 3.57)


def _v_rechts(sl, titel, untertitel, meta):
    """Titelblock rechts der Sidebar: Titel 40pt, Untertitel 20pt, Meta 14pt."""
    _text(sl, 5.97, 1.63, 6.59, 2.43, titel or "", 40, V_DUNKEL)
    if untertitel:
        _text(sl, 5.97, 4.43, 6.59, 1.81, untertitel, 20, V_GRAU)
    if meta:
        _text(sl, 5.97, 6.63, 6.59, 0.47, meta, 14, V_GRAU)


def _v_kopf(sl, s, kicker):
    """Content-Kopf OHNE Band: kleiner grauer Kicker (0.77,0.15), Titel 28pt
    (0.76,0.48), petrol Lead-Zeile (0.67,1.33) - alles schwebend auf Weiss."""
    if kicker:
        _text(sl, 0.77, 0.13, 8.5, 0.24, str(kicker), 10, V_GRAU)
    _text(sl, 0.76, 0.48, 10.24, 0.87, s.get("title") or "", 28, V_DUNKEL)
    if s.get("lead"):
        _text(sl, 0.67, 1.33, 12.0, 0.40, str(s["lead"]), 14.5, V_PETROL)


def _v_num_quadrat(sl, x, y, nr, farbe, q=0.44):
    sh = _rect(sl, x, y, q, q, farbe)
    tf = sh.text_frame
    tf.word_wrap = False
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run()
    r.text = str(nr)
    r.font.size = Pt(13)
    r.font.bold = True
    r.font.color.rgb = WEISS
    r.font.name = FONT
    return sh


def _v_kpi_karte(sl, x, y, w, h, big, label, subs):
    """Variante A (Referenz Folie 3 links): F4F5F6-Karte, 40pt petrol Zahl,
    16pt Label, LINE, darunter Sub-Wertepaare (22pt petrol + 10.5pt grau).
    Sub-Abstand skaliert mit der Kartenhoehe, damit bei der 3er-KPI-Reihe
    (h=2.95) nichts aus der Karte laeuft (Studio-Critic-Befund)."""
    _rect(sl, x, y, w, h, V_KARTE)
    bsize = 40 if len(str(big)) <= 6 else (34 if len(str(big)) <= 8 else 28)
    _text(sl, x + 0.30, y + 0.25, w - 0.60, 0.90, str(big or ""), bsize,
          V_PETROL, bold=True)
    if label:
        lsize = 16 if len(str(label)) <= 24 else 13.5
        if h >= 3.5:                   # grosse Karte: 3-Zeilen-Label zulassen
            _text(sl, x + 0.30, y + 1.15, w - 0.60, 0.95, str(label), lsize,
                  V_DUNKEL, bold=True)
            ober = y + 1.15 + 0.95
        else:
            _text(sl, x + 0.30, y + 1.15, w - 0.60, 0.62, str(label), lsize,
                  V_DUNKEL, bold=True)
            ober = y + 1.15 + 0.60
    else:
        ober = y + 0.25 + 0.90
    subs = list(subs or [])[:3]
    platz = (y + h - 0.15) - (ober + 0.10)
    if subs and platz >= 0.50 * len(subs):
        step = min(1.10, max(0.50, platz / len(subs)))
        ly = min(y + 2.00, y + h - 0.15 - step * len(subs))
        _v_hline(sl, x + 0.30, ly, w - 0.60)
        sy = ly + 0.16
        for wert, bez in subs:
            wsize = 22 if len(wert) <= 5 else (16 if len(wert) <= 7 else 13.5)
            _text(sl, x + 0.30, sy + (0.08 if wsize < 22 else 0), 1.22, 0.50,
                  wert, wsize, V_PETROL, bold=True)
            _text(sl, x + 1.40, sy + 0.04, w - 1.73, 0.90, bez, 10.5, V_GRAU)
            sy += step


def _v_punkt_karte(sl, x, y, w, h, nr, titel, text):
    """Variante B: F4F5F6-Karte mit nummeriertem Quadrat (1=rot, Rest petrol),
    Titel 14pt bold, Text 11pt; **fett** im Text -> 16pt petrol Highlight."""
    _rect(sl, x, y, w, h, V_KARTE)
    farbe = ROT if nr == 1 else V_PETROL
    if h >= 2.0:                      # grosse Karte (2-Spalten-Raster): Quadrat oben links
        _v_num_quadrat(sl, x + 0.30, y + 0.30, nr, farbe)
        tx, tty = x + 0.98, y + 0.33
        by, bx = y + 0.92, x + 0.30
    else:                             # Zeilen-Karte: Quadrat mittig links, Titel oben
        _v_num_quadrat(sl, x + 0.25, y + h / 2 - 0.22, nr, farbe)
        tx, tty = x + 0.98, y + 0.20
        by, bx = y + 0.58, x + 0.98
    if titel:
        _text(sl, tx, tty, w - (tx - x) - 0.25, 0.35, titel, 14, V_DUNKEL, bold=True)
    if not titel and h < 2.0:                  # keine Headline -> Text oben, ohne Luft
        by = y + 0.20
    if text:
        voll_bold = text.startswith("**") and text.rstrip().endswith("**") \
            and text.count("**") == 2
        if voll_bold:                 # Highlight-Zeile: 16pt bold petrol (Referenz Folie 3)
            _text(sl, bx, by - 0.06, w - (bx - x) - 0.25, 0.60,
                  text.strip("*"), 16, V_PETROL, bold=True)
        else:
            size = 11 if h >= 1.2 else 10.5
            _runs_textbox(sl, bx, by, w - (bx - x) - 0.25, max(0.3, y + h - by - 0.15),
                          text, size, base_color=V_TEXT, bold_color=V_PETROL)


def _v_bullet_split(t):
    """'Titel: Text' -> (titel, text); '**...**' erkennt Highlight."""
    t = str(t).strip()
    m = re.match(r"^([^:]{3,60}):\s+(.+)$", t, re.S)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return "", t


def _v_zeilen_h(t, chars_pro_zeile):
    """Geschaetzte Kartenhohe nach Textmenge (gegen leere Riesen-Karten und
    gegen Text, der aus der Zeilen-Karte laeuft: Titel 0.58 + Zeilen 0.26)."""
    zeilen = max(1, -(-len(str(t)) // chars_pro_zeile))
    return min(2.26, max(0.98, zeilen * 0.26 + 0.72))


def _v_punkt_raster(sl, items, x, y, unten):
    """Punkt-Karten: <=3 Zeilen ueber volle Breite, 4-6 im 2-Spalten-Raster.
    Kartenhoehe adaptiv nach Textmenge (Studio-Critic: keine leeren Karten)."""
    n = len(items)
    if not n:
        return
    if n <= 3:
        karten = [(i, *_v_bullet_split(t)) for i, (lvl, t) in enumerate(items) if not lvl]
        if not karten:
            return
        bedarf = max(_v_zeilen_h(tx_, 90) for _, _, tx_ in karten)
        # Karten bis max 1.48 strecken, wenn sonst Luft unten bliebe
        # (Studio-Critic: "untere Haelfte leer") - nie ueber Textbedarf+0.5
        streck = min(1.48, (unten - y - 0.16 * (len(karten) - 1)) / len(karten))
        hoehe = min(max(bedarf, streck), bedarf + 0.5)
        for i, ti, tx_ in karten:
            _v_punkt_karte(sl, x, y + i * (hoehe + 0.16), 12.0, hoehe,
                           i + 1, ti, tx_)
        return
    cols, rows = 2, (n + 1) // 2
    cw = 5.92
    karten = [(i, *_v_bullet_split(t)) for i, (lvl, t) in enumerate(items) if not lvl]
    if not karten:
        return
    bedarf = max(_v_zeilen_h(tx_, 45) for _, _, tx_ in karten)
    # auch im 2-Spalten-Raster bis Unterkante strecken, wenn Luft bliebe
    # (Studio-Critic: "Leerraum zwischen Karten und Hinweis")
    streck = min(2.26, (unten - y - 0.15 * (rows - 1)) / rows)
    hoehe = min(max(bedarf, streck), bedarf + 0.35)
    for i, ti, tx_ in karten:
        r_, c_ = divmod(i, 2)
        _v_punkt_karte(sl, x + c_ * (cw + 0.16), y + r_ * (hoehe + 0.15), cw,
                       hoehe, i + 1, ti, tx_)


def _v_hinweis(sl, s):
    """Hinweis-Band unten (gold Tint) mit bold Prefix."""
    hz = s.get("hinweis")
    if not hz:
        return
    _rect(sl, 0.67, 6.22, 12.0, 0.55, V_TINT_GOLD)
    m = re.match(r"^(\w[\w \-]*?):\s+(.+)$", str(hz), re.S)
    kopf, rest = (m.group(1), m.group(2)) if m else ("Hinweis", str(hz))
    tb = sl.shapes.add_textbox(Inches(0.92), Inches(6.30), Inches(11.5), Inches(0.40))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    r1 = p.add_run()
    r1.text = kopf + ":  "
    r1.font.size = Pt(11)
    r1.font.bold = True
    r1.font.color.rgb = V_DUNKEL
    r1.font.name = FONT
    r2 = p.add_run()
    r2.text = str(rest)
    r2.font.size = Pt(11)
    r2.font.color.rgb = V_TEXT
    r2.font.name = FONT


def _v_statement_folie(sl, s, kicker):
    _v_kopf(sl, s, kicker)
    # Kartenhoehe adaptiv nach Textmenge (Studio-Critic: keine leere Riesenkarte)
    txt = str(s.get("botschaft") or "")
    zeilen = max(1, -(-len(txt) // 55))
    kh = min(3.4, max(1.7, zeilen * 0.52 + 0.95))
    ky = 1.95 + (3.6 - kh) / 2
    _rect(sl, 0.67, ky, 12.0, kh, V_KARTE)
    _rect(sl, 0.67, ky, 0.09, kh, ROT)
    tb = _text(sl, 1.15, ky + 0.3, 11.1, kh - 0.6, txt, 26,
               V_DUNKEL, bold=True)
    tb.text_frame.vertical_anchor = MSO_ANCHOR.MIDDLE   # Balance statt Top-Presste
    if s.get("zusatz"):
        _text(sl, 0.67, ky + kh + 0.30, 12.0, 0.5, str(s["zusatz"]), 12, V_GRAU)


def _v_tabellen_folie(sl, s, kicker):
    _v_kopf(sl, s, kicker)
    rows = s.get("table") or []
    if not rows:
        return
    ncols = max(len(r) for r in rows)
    nrows = len(rows)
    verfuegbar = (6.05 if s.get("hinweis") else 6.75) - 1.95
    # Flaeche bis Footer bzw. bis Hinweis-Band (6.22) verteilen - sonst
    # ueberlappt die Tabelle den Hinweis-Kasten (Studio-Critic-Befund)
    row_h = min(0.85, max(0.40, verfuegbar / nrows))
    gf = sl.shapes.add_table(nrows, ncols, Inches(0.67), Inches(1.95),
                             Inches(12.0), Inches(row_h * nrows))
    tbl = gf.table
    tbl.first_row = False
    tbl.horz_banding = False
    if ncols == 2:                    # Risikomuster: Textspalte breit, Status schmal
        tbl.columns[0].width = Inches(8.5)
        tbl.columns[1].width = Inches(3.5)
    for r in range(nrows):
        tbl.rows[r].height = Inches(row_h)
    for r, row in enumerate(rows):
        for c in range(ncols):
            cell = tbl.cell(r, c)
            cell.text = str(row[c]) if c < len(row) else ""
            cell.margin_left = Inches(0.1)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            pill = None if r == 0 else _status_farbe(cell.text)
            fill = cell.fill
            fill.solid()
            if r == 0:
                fill.fore_color.rgb = V_PETROL
            elif pill is not None:
                fill.fore_color.rgb = V_KARTE      # dezent: Pill gengt, keine Vollflaeche
            else:
                fill.fore_color.rgb = V_KARTE if r % 2 else WEISS
            for p in cell.text_frame.paragraphs:
                for run in p.runs:
                    run.font.size = Pt(11.5 if r == 0 else 11)
                    run.font.bold = r == 0 or pill is not None
                    run.font.name = FONT
                    run.font.color.rgb = WEISS if (r == 0 or pill is not None) else V_TEXT
    _pill_ueber_tabelle(sl, tbl, rows)


def _v_kpi_folie(sl, s, kicker):
    """zahl-KV -> Variante A. Eine Zahl: KPI links + Punkt-Karten rechts
    (Referenz Folie 3/6). Mehrere (bis 3): KPI-Reihe 3.84 breit + Karten darunter."""
    _v_kopf(sl, s, kicker)
    unten = 6.05 if s.get("hinweis") else 6.75
    suffixe = _zahl_suffixe(s)[:3] or [""]
    bullets = s.get("bullets") or []
    subs, karten = [], []
    for lvl, t in bullets:
        if not lvl and "|" in t and len(suffixe) == 1:
            wert, _, bez = t.partition("|")
            subs.append((wert.strip(), bez.strip()))
        elif not lvl:
            karten.append((lvl, t))
    if len(suffixe) == 1:
        get = (lambda k: s.get(k + suffixe[0])) if suffixe[0] else (lambda k: s.get(k))
        _v_kpi_karte(sl, 0.67, 1.95, 3.2, unten - 1.95, get("zahl"),
                     get("label") or s.get("title"), subs)
        n = len(karten)
        if n:
            # Zeilen-Karten bis Unterkante strecken, wenn sonst Luft bliebe
            # (Studio-Critic: "rechte Spalte endet auf halber Hoehe")
            cap = 1.70 if n >= 2 else 2.40
            ch = min(cap, (unten - 1.95 - 0.16 * (n - 1)) / n)
            ch = max(ch, 1.0)
            for i, (lvl, t) in enumerate(karten[:4]):
                ti, tx = _v_bullet_split(t)
                _v_punkt_karte(sl, 4.12, 1.95 + i * (ch + 0.16), 8.55, ch,
                               i + 1, ti, tx)
    else:
        cw, gap = 3.84, 0.24
        for i, suf in enumerate(suffixe):
            get = (lambda k: s.get(k + suf)) if suf else (lambda k: s.get(k))
            my_subs = subs if i == 0 else []
            _v_kpi_karte(sl, 0.67 + i * (cw + gap), 1.95, cw, 2.95, get("zahl"),
                         get("label") or f"Kennzahl {suf}", my_subs)
        if karten:
            y2 = 5.10
            n = len(karten)
            ch = min(1.48, (unten - y2 - 0.16 * (n - 1)) / n)
            for i, (lvl, t) in enumerate(karten[:3]):
                ti, tx = _v_bullet_split(t)
                _v_punkt_karte(sl, 0.67, y2 + i * (ch + 0.16), 12.0, ch, i + 1, ti, tx)


def _v_zeitstrahl_folie(sl, s, kicker):
    _v_kopf(sl, s, kicker)
    _bruecke(sl, 0.55, 2.15, W - 1.1, s.get("zeitstrahl") or [], s.get("heute"),
             farben=(V_PETROL, V_DUNKEL, WEISS))


def _v_content_folie(sl, s, kicker):
    _v_kopf(sl, s, kicker)
    img = s.get("image")
    if img and Path(img).is_file():
        unten = 6.05 if s.get("hinweis") else 6.75
        w_text = W - 2 * 0.67 - 4.1          # Bullets links, Infografik rechts
        _v_punkt_raster(sl, s.get("bullets") or [], 0.67, 1.95, unten)
        sl.shapes.add_picture(str(img), Inches(W - 0.67 - 3.6),
                              Inches(2.15), width=Inches(3.6))
    else:
        unten = 6.05 if s.get("hinweis") else 6.75
        _v_punkt_raster(sl, s.get("bullets") or [], 0.67, 1.95, unten)


def _v_fuss(sl, nr, gesamt, brand):
    _v_hline(sl, 0.67, 7.06, 12.0)
    _text(sl, 0.67, 7.12, 8.0, 0.24, f"{brand} \u00b7 {V_BRAND}", 8, V_INAKT_T)
    _text(sl, 10.67, 7.12, 2.0, 0.24, f"Folie {nr} / {gesamt}", 8, V_INAKT_T,
          align=PP_ALIGN.RIGHT)


def build_vorlage(slides, out_path):
    """Vorstandsvorlagen-Design-Profil (fmt=vorpptx): heller Look mit
    INHALT-Sidebar, KPI-/Punkt-Karten, petrol Tabellenkopf - deterministisch."""
    prs = Presentation()
    prs.slide_width = Inches(W)
    prs.slide_height = Inches(H)
    teile, part_of = _v_teile(slides)
    brand = (slides[0].get("title") or "Pr\u00e4sentation").split(":")[0].strip()
    gesamt = max(1, len(slides))
    for nr, s in enumerate(slides, 1):
        sl = _slide_bg(prs.slides.add_slide(prs.slide_layouts[6]))
        kind = s.get("kind", "content")
        pi = part_of.get(nr - 1)
        if kind == "title":
            _v_sidebar(sl, teile, aktiv=None)
            meta = s.get("meta") or time.strftime("Stand %d.%m.%Y \u00b7 f\u00fcr Vorstand",
                                                  time.gmtime())
            _v_rechts(sl, s.get("title"), s.get("subtitle"), meta)
            _v_dp_logo(sl)
        elif kind == "section":
            _v_sidebar(sl, teile, aktiv=pi)
            end = len(slides)
            for j in range(nr, len(slides)):
                if part_of.get(j) != pi:
                    end = j
                    break
            subs = [i for i in range(nr, end) if slides[i].get("kind") == "content"]
            meta = s.get("meta") or (
                f"Teil {(pi or 0) + 1} \u00b7 Folien {subs[0] + 1}\u2013{end}"
                if subs else f"Teil {(pi or 0) + 1}")
            _v_rechts(sl, s.get("title"), s.get("subtitle"), meta)
            _v_dp_logo(sl)
        else:
            if pi is not None and pi < len(teile):
                pname = teile[pi][1].split("\u00b7", 1)[-1].strip()
                pname = pname.split(" und ")[0].strip()
                kicker = s.get("kicker") or f"{brand} \u00b7 Teil {pi + 1}  {pname}"
            else:
                kicker = s.get("kicker")
            if s.get("zeitstrahl"):
                _v_zeitstrahl_folie(sl, s, kicker)
            elif s.get("table"):
                _v_tabellen_folie(sl, s, kicker)
            elif s.get("botschaft"):
                _v_statement_folie(sl, s, kicker)
            elif _zahl_suffixe(s):
                _v_kpi_folie(sl, s, kicker)
            else:
                _v_content_folie(sl, s, kicker)
            _v_hinweis(sl, s)
            _v_dp_logo(sl, klein=True)
            _v_fuss(sl, nr, gesamt, brand)
        if s.get("notes"):
            sl.notes_slide.notes_text_frame.text = str(s["notes"])
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(out_path))
    return []
