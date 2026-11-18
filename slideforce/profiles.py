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
from pathlib import Path

from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE
from pptx.enum.shapes import MSO_SHAPE
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
    """NAVY-Band 0.95h: gold Kicker 10pt bold + weisser Titel 23pt + Marke rechts (b28 1:1)."""
    _rect(sl, 0, 0, W, 0.95, NAVY)
    _text(sl, MX, 0.09, 9, 0.28, (kicker or "BRIDGE28").upper(), 10, GOLD, bold=True)
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


def kachel(sl, x, y, w, h, label, gross, unit, unter, kontext, farbe=None):
    """KPI-Kachel wie b28-pptx-edit.js kachel(): weisse Karte, LINE-Border,
    Farbbalken 0.07 oben, Label uppercase 10.5 GRAU, Zahl 30pt NAVY bold +
    Unit 12.5 GRAU, Unterzeile 10.5 bold, Kontext 9.5 GRAU2."""
    balken = farbe if farbe is not None else NAVY
    pad = 0.16
    _rect(sl, x, y, w, h, WEISS, line=LINE)
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
    if kontext:
        _text(sl, x + pad, y + 1.54, w - 2 * pad, max(0.24, h - 1.68), kontext, 9.5, GRAU2)


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
    """Grün/Gelb/Rot-Status einer Zelle -> Pill-Farbe (Wortanfang, kein Substring-Match)."""
    t = str(value).strip().lower()
    if re.match(r"^(gr\u00fcn|gruen|green|fertig|ok)\b", t):
        return GRUEN
    if re.match(r"^(gelb|amber|warnung)\b", t):
        return AMB
    if re.match(r"^(rot|red|kritisch)\b", t):
        return ROT
    return None


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
    _text(sl, 2, 5.25, W - 4, 0.3, "BRIDGE28 \u00b7 Projektbericht", 10.5, GRAU2,
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
    """zahl, zahl2, zahl3 ... in Reihenfolge (max. 3 Kacheln)."""
    keys = [k for k in s if re.fullmatch(r"zahl\d*", str(k))]
    keys.sort(key=lambda k: (k != "zahl", len(k), k))
    return [k[4:] for k in keys[:3]]


def _kpi_folie(sl, s):
    kopf(sl, s.get("kicker"), s.get("title"))
    suffixe = _zahl_suffixe(s)
    n = max(1, len(suffixe))
    gap = 0.2 if n > 1 else 0.0
    cw = (W - 2 * MX - gap * (n - 1)) / n
    for i, suf in enumerate(suffixe or [""]):
        get = (lambda k: s.get(k + suf)) if suf else (lambda k: s.get(k))
        label = (get("label") or (s.get("title") if not suf else f"Kennzahl {suf}"))
        kachel(sl, MX + i * (cw + gap), 1.35, cw, 2.35, label,
               get("zahl") or "", get("einheit") or "",
               get("erklaerung") or "", get("einordnung") or "", NAVY)
    rest = s.get("bullets") or []
    if rest:
        _zeilen_karten(sl, rest, y=4.0, unten=6.85)


def _ring_folie(sl, s, pct):
    kopf(sl, s.get("kicker"), s.get("title"))
    cd = CategoryChartData()
    cd.categories = ["Wert", "Rest"]
    cd.add_series("Anteil", (pct, max(0.0, 100.0 - pct)))
    size = 3.0
    gf = sl.shapes.add_chart(XL_CHART_TYPE.DOUGHNUT, Inches(MX + 0.1), Inches(1.45),
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
    _text(sl, cx - 0.85, 1.45 + size / 2 - 0.30, 1.7, 0.6, f"{pct:g} %", 28, NAVY,
          bold=True, align=PP_ALIGN.CENTER)
    # Mini-Legende unter dem Ring: gold = erreicht, navy = offen
    lx, ly = MX + 0.3, 1.45 + size + 0.16
    _rect(sl, lx, ly + 0.04, 0.16, 0.16, GOLD)
    _text(sl, lx + 0.22, ly - 0.01, 1.3, 0.28, "erreicht", 10.5, GRAU, bold=True)
    _rect(sl, lx + 1.45, ly + 0.04, 0.16, 0.16, NAVY)
    _text(sl, lx + 1.67, ly - 0.01, 1.3, 0.28, "offen", 10.5, GRAU, bold=True)
    # Infokarte rechts: Label, Erklaerung, Einordnung
    x = MX + 0.1 + size + 0.35
    w = W - MX - x
    kachel(sl, x, 1.45, w, 2.35, s.get("label") or "Fortschritt",
           "", "", s.get("erklaerung") or "", s.get("einordnung") or "", GOLD)
    rest = s.get("bullets") or []
    if rest:
        _zeilen_karten(sl, rest, y=4.95, unten=6.85)


def _statement_folie(sl, s):
    kopf(sl, s.get("kicker"), s.get("title"))
    _text(sl, MX + 0.28, 1.45, 1.2, 1.2, "\u201e", 88, GOLD, bold=True)
    _rect(sl, MX, 2.35, 0.09, 2.3, GOLD)
    _text(sl, MX + 0.5, 2.35, W - 2 * MX - 0.6, 2.3, s.get("botschaft") or "", 30, NAVY,
          bold=True)
    if s.get("zusatz"):
        _text(sl, MX + 0.5, 5.05, W - 2 * MX - 0.6, 0.6, s["zusatz"], 14, GRAU2)


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
