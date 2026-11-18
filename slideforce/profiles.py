"""SlideForce: BRIDGE28-Design-Profil. Folien von Hand designt (b28-Export-Stil).

Farben/Maße aus bridge28-handbuch/b28-pptx-edit.js: NAVY 002846, GOLD C9A961,
weiße Flaeche, Header-Band mit gold Kicker + weissem Titel, Footer mit KW/Folie.
"""
import time
from pathlib import Path
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE

NAVY = RGBColor(0x00, 0x28, 0x46)
GOLD = RGBColor(0xC9, 0xA9, 0x61)
ROT = RGBColor(0x9E, 0x29, 0x2B)
GRAU = RGBColor(0x54, 0x61, 0x6E)
GRAU2 = RGBColor(0x8A, 0x93, 0xA3)
LINE = RGBColor(0xD0, 0xD7, 0xE2)
HELL = RGBColor(0xF7, 0xF9, 0xFC)
WEISS = RGBColor(0xFF, 0xFF, 0xFF)
SCHW = RGBColor(0x1A, 0x22, 0x2B)
W, H, MX = 13.333, 7.5, 0.55
FONT = "Arial"
BRIDGE = "Dataport"


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
    """spacing (CharSpacing) wird ignoriert: python-pptx bietet dafuer keine API."""
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


def _header(sl, kicker, titel):
    """NAVY-Band oben: gold Kicker + weisser Titel + Dataport rechts."""
    _rect(sl, 0, 0, W, 0.95, NAVY)
    _rect(sl, 0, 0.95, W, 0.035, GOLD)
    _text(sl, MX, 0.10, 9.5, 0.3, (kicker or "BRIDGE28").upper(), 10, GOLD, bold=True, spacing=2)
    _text(sl, MX, 0.36, 10.4, 0.55, titel or "", 23, WEISS, bold=True)
    _text(sl, W - 1.9, 0.38, 1.4, 0.34, BRIDGE, 10.5, WEISS, align=PP_ALIGN.RIGHT)


def _footer(sl, nr, gesamt):
    kw = time.strftime("KW %V", time.gmtime())
    _text(sl, MX, H - 0.4, 6, 0.28, f"BRIDGE28 \u00b7 {kw}", 9, GRAU2)
    _text(sl, W - 2.6, H - 0.4, 2.1, 0.28, f"Folie {nr} / {gesamt}", 9, GRAU2, align=PP_ALIGN.RIGHT)


def _bullets(sl, items, x=MX, y=1.55, w=W - 2 * MX, size=14):
    """Bullets im b28-Stil: gold Strich-Marker, navy-Text, Unterpunkte eingerueckt."""
    tb = sl.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(H - y - 0.7))
    tf = tb.text_frame
    tf.word_wrap = True
    first = True
    for level, text in items:
        p = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        p.space_after = Pt(10)
        if level:
            p.level = 1
        m = p.add_run()
        m.text = "\u2014  " if not level else "\u2013  "
        m.font.size = Pt(size if not level else size - 1)
        m.font.color.rgb = GOLD
        m.font.bold = True
        m.font.name = FONT
        for part in _inline(text):
            r = p.add_run()
            r.text = part[0]
            r.font.size = Pt(size if not level else size - 1)
            r.font.bold = part[1]
            r.font.color.rgb = SCHW if not part[1] else NAVY
            r.font.name = FONT


def _inline(text):
    """**fett** -> (text, True/False)-Runs."""
    import re
    out = []
    for part in re.split(r"(\*\*.+?\*\*)", text):
        if not part:
            continue
        if part.startswith("**") and part.endswith("**"):
            out.append((part[2:-2], True))
        else:
            out.append((part, False))
    return out or [("", False)]


def _slide(prs):
    sl = prs.slides.add_slide(prs.slide_layouts[6])
    sl.background.fill.solid()
    sl.background.fill.fore_color.rgb = WEISS
    return sl


def build_profile(slides, out_path):
    """BRIDGE28-Design-Profil: handdesignte Folien im Stil des b28-Exports."""
    prs = Presentation()
    prs.slide_width = Inches(W)
    prs.slide_height = Inches(H)
    gesamt = max(1, len(slides))
    for nr, s in enumerate(slides, 1):
        kind = s.get("kind", "content")
        sl = _slide(prs)
        if kind == "title":
            _title_slide(sl, s)
        elif kind == "section":
            _section_slide(sl, s)
        elif s.get("zahl"):
            _kpi_slide(sl, s)
        elif s.get("botschaft"):
            _statement_slide(sl, s)
        elif s.get("table"):
            _table_slide(sl, s)
        else:
            _content_slide(sl, s)
        _footer(sl, nr, gesamt)
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(out_path))
    return []


def _title_slide(sl, s):
    _rect(sl, 0, 0, W, 0.16, NAVY)
    _rect(sl, 0, H - 0.16, W, 0.16, NAVY)
    _text(sl, MX, 2.5, W - 2 * MX, 0.4, (s.get("kicker") or "BRIDGE28").upper(), 13, GOLD,
          bold=True, align=PP_ALIGN.CENTER, spacing=4)
    _text(sl, MX, 2.95, W - 2 * MX, 1.0, s.get("title") or "", 32, NAVY, bold=True, align=PP_ALIGN.CENTER)
    if s.get("subtitle"):
        _text(sl, MX, 4.05, W - 2 * MX, 0.5, s["subtitle"], 15, GRAU, align=PP_ALIGN.CENTER)
    _rect(sl, W / 2 - 0.5, 4.75, 1.0, 0.045, GOLD)


def _section_slide(sl, s):
    _rect(sl, 0, 0, W, H, NAVY)
    _text(sl, MX, 2.7, W - 2 * MX, 0.4, "KAPITEL", 13, GOLD, bold=True, spacing=4)
    _text(sl, MX, 3.15, W - 2 * MX, 1.1, s.get("title") or "", 36, WEISS, bold=True)
    _rect(sl, MX, 4.35, 1.4, 0.05, GOLD)


def _content_slide(sl, s):
    _header(sl, s.get("kicker"), s.get("title"))
    _bullets(sl, s.get("bullets") or [(0, "")])


def _kpi_slide(sl, s):
    _header(sl, s.get("kicker"), s.get("title"))
    rest = s.get("bullets") or []
    if rest:
        cw = (W - 2 * MX - 0.4) / 2
    else:
        cw = W - 2 * MX
    _kachel(sl, MX, 1.7, cw, 2.2, s.get("kicker") or "Kennzahl", s.get("zahl") or "",
            s.get("einheit") or "", s.get("erklaerung") or "", s.get("einordnung") or "", NAVY)
    if rest:
        _bullets(sl, rest, x=MX + cw + 0.4, y=1.8, w=cw, size=12.5)


def _statement_slide(sl, s):
    _header(sl, s.get("kicker"), s.get("title"))
    _rect(sl, MX, 2.0, 0.09, 2.6, GOLD)
    _text(sl, MX + 0.45, 2.0, W - 2 * MX - 0.5, 2.4, s.get("botschaft") or "", 30, NAVY, bold=True)
    if s.get("zusatz"):
        _text(sl, MX + 0.45, 4.9, W - 2 * MX - 0.5, 0.6, s["zusatz"], 14, GRAU2)


def _table_slide(sl, s):
    _header(sl, s.get("kicker"), s.get("title"))
    rows = s.get("table") or []
    if not rows:
        return
    ncols = max(len(r) for r in rows)
    nrows = len(rows)
    tw = W - 2 * MX
    th = min(4.6, 0.42 * nrows + 0.1)
    gf = sl.shapes.add_table(nrows, ncols, Inches(MX), Inches(1.6), Inches(tw), Inches(th))
    tbl = gf.table
    for r, row in enumerate(rows):
        for c in range(ncols):
            cell = tbl.cell(r, c)
            cell.text = str(row[c]) if c < len(row) else ""
            cell.margin_left = Inches(0.08)
            cell.margin_top = Inches(0.04)
            fill = cell.fill
            fill.solid()
            if r == 0:
                fill.fore_color.rgb = NAVY
            else:
                fill.fore_color.rgb = WEISS if r % 2 else HELL
            for p in cell.text_frame.paragraphs:
                for run in p.runs:
                    run.font.size = Pt(11 if r else 11.5)
                    run.font.bold = r == 0
                    run.font.name = FONT
                    run.font.color.rgb = WEISS if r == 0 else SCHW


def _kachel(sl, x, y, w, h, label, gross, unit, unter, kontext, farbe):
    """Kachel wie b28-pptx-edit.js: weisse Karte, Farbbalken oben, NAVY-Zahl."""
    _rect(sl, x, y, w, h, WEISS, line=LINE)
    _rect(sl, x, y, w, 0.07, farbe)
    pad = 0.16
    _text(sl, x + pad, y + 0.15, w - 2 * pad, 0.28, (label or "").upper(), 10.5, GRAU, bold=True, spacing=1)
    tb = sl.shapes.add_textbox(Inches(x + pad), Inches(y + 0.44), Inches(w - 2 * pad), Inches(0.75))
    p = tb.text_frame.paragraphs[0]
    r = p.add_run(); r.text = gross or ""
    r.font.size = Pt(30); r.font.bold = True; r.font.color.rgb = NAVY; r.font.name = FONT
    if unit:
        r2 = p.add_run(); r2.text = " " + unit
        r2.font.size = Pt(12.5); r2.font.color.rgb = GRAU; r2.font.name = FONT
    if unter:
        _text(sl, x + pad, y + 1.22, w - 2 * pad, 0.28, unter, 10.5, GRAU, bold=True)
    if kontext:
        _text(sl, x + pad, y + 1.52, w - 2 * pad, max(0.3, h - 1.66), kontext, 9.5, GRAU2)
