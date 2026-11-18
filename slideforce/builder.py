"""SlideForce: Deck-Builder. Content-Dicts + Folienmaster -> fertiges PPTX."""
import re
from pathlib import Path
from pptx import Presentation
from pptx.util import Emu, Pt
from pptx.oxml.ns import qn
from pptx.enum.text import PP_ALIGN
from .layoutmap import LayoutMap, norm

RESERVED = {"layout", "title", "subtitle", "bullets", "table", "image", "notes", "kind"}


def _inline_runs(paragraph, text):
    """'**fett**', '*kursiv*', '`code`' -> Runs mit Font-Flags."""
    for part in re.split(r"(\*\*.+?\*\*|\*.+?\*|`.+?`)", text):
        if not part:
            continue
        run = paragraph.add_run()
        if part.startswith("**") and part.endswith("**"):
            run.text = part[2:-2]
            run.font.bold = True
        elif part.startswith("`") and part.endswith("`"):
            run.text = part[1:-1]
            run.font.name = "Consolas"
        elif part.startswith("*") and part.endswith("*"):
            run.text = part[1:-1]
            run.font.italic = True
        else:
            run.text = part


def _strip_example_slides(prs):
    """Alle schon vorhandenen Folien des Masters entfernen (Layouts bleiben)."""
    lst = prs.slides._sldIdLst
    for sldId in list(lst):
        rId = sldId.get(qn("r:id"))
        prs.part.drop_rel(rId)
        lst.remove(sldId)


def _ph_area(ph):
    w = ph.width or 0
    h = ph.height or 0
    return w * h


def _biggest_body(lay, used):
    """Groesster freier BODY-Platzhalter (Inhaltsbereich) im Layout."""
    best, best_area = None, 0
    for ph in lay.placeholders:
        pf = ph.placeholder_format
        if pf.idx in (0, 1, 11, 12) or ph.placeholder_format.idx in used:
            continue
        if pf.type in (2, 7):  # BODY oder OBJECT mit Textfeld
            area = _ph_area(ph)
            if area > best_area:
                best, best_area = ph, area
    return best


def _all_ph_by_name(lay):
    """Platzhalter-Indizes (ausser 0/1) gruppiert nach normiertem Namen (vom Layout)."""
    groups = {}
    for ph in lay.placeholders:
        pf = ph.placeholder_format
        if pf.idx in (0, 1):
            continue
        groups.setdefault(norm(ph.name), []).append(pf.idx)
    return groups


def _fill_table(slide, lay, rows, warn, size):
    used = set()
    obj = next((ph for ph in slide.placeholders
                if ph.placeholder_format.type == 7 and ph.placeholder_format.idx >= 10), None)
    ncols = max(len(r) for r in rows)
    nrows = len(rows)
    if obj is not None:
        left, top, width, height = obj.left, obj.top, obj.width, obj.height
        obj._element.getparent().remove(obj._element)
        gf = slide.shapes.add_table(nrows, ncols, left, top, width, height)
        used.add(-100)
    else:
        sw, sh = size
        gf = slide.shapes.add_table(nrows, ncols, Emu(int(sw*0.07)), Emu(int(sh*0.22)),
                                    Emu(int(sw*0.86)), Emu(int(sh*0.6)))
    for r, row in enumerate(rows):
        for c in range(ncols):
            cell = gf.table.cell(r, c)
            cell.text = str(row[c]) if c < len(row) else ""
            if r == 0:
                for p in cell.text_frame.paragraphs:
                    for run in p.runs:
                        run.font.bold = True
    return used


def _fill_image(slide, lay, img_path, warn, size):
    p = Path(img_path)
    if not p.is_file():
        warn.append(f"Bild nicht gefunden: {img_path}")
        return set()
    pic = next((ph for ph in slide.placeholders
                if ph.placeholder_format.type == 18), None)
    if pic is not None:
        pic.insert_picture(str(p))
        return {pic.placeholder_format.idx}
    sw, sh = size
    w = Emu(int(sw * 0.42))
    slide.shapes.add_picture(str(p), Emu(int(sw * 0.52)), Emu(int(sh * 0.22)), width=w)
    return set()


def _fill_slide(slide, lay, data, warn, size):
    used = set()
    slide_by_idx = {ph.placeholder_format.idx: ph for ph in slide.placeholders}
    # Titel + Untertitel
    t = next((ph for ph in slide.placeholders if ph.placeholder_format.idx == 0), None)
    if t is not None and data.get("title"):
        t.text_frame.text = str(data["title"])
        used.add(t.placeholder_format.idx)
    sub = next((ph for ph in slide.placeholders if ph.placeholder_format.idx == 1), None)
    if sub is None:
        idxs = _all_ph_by_name(lay).get("untertitel")
        if idxs:
            sub = slide_by_idx.get(idxs[0])
    if sub is not None and data.get("subtitle"):
        sub.text_frame.text = str(data["subtitle"])
        used.add(sub.placeholder_format.idx)
    # Tabelle / Bild
    if data.get("table"):
        used |= _fill_table(slide, lay, data["table"], warn, size)
    if data.get("image"):
        used |= _fill_image(slide, lay, data["image"], warn, size)
    # Bullets in den groessten freien Inhaltsplatzhalter
    if data.get("bullets"):
        body = _biggest_body(slide, used)
        if body is None:
            warn.append(f"Kein Inhaltsplatzhalter fuer Bullets (Folie '{data.get('title','')}')")
        else:
            tf = body.text_frame
            tf.clear()
            first = True
            for level, text in data["bullets"]:
                para = tf.paragraphs[0] if first else tf.add_paragraph()
                first = False
                para.level = min(level, 4)
                _inline_runs(para, text)
            used.add(body.placeholder_format.idx)
    # Restliche Keys -> Platzhalter-Namen im Master
    groups = _all_ph_by_name(lay)
    for key, val in data.items():
        if key in RESERVED:
            continue
        groups_key = None
        if key in groups:
            groups_key = key
        else:
            cands = [n for n in groups if n.endswith(key) or key in n]
            if len(cands) == 1:
                groups_key = cands[0]
        if groups_key is None:
            warn.append(f"Key '{key}' passt zu keinem Platzhalter in '{lay.name}' - ignoriert")
            continue
        val_groups = groups[groups_key]
        vals = val if isinstance(val, list) else [val]
        phs = [slide_by_idx[i] for i in val_groups if i not in used and i in slide_by_idx]
        for ph, v in zip(phs, vals):
            if isinstance(v, list):  # Bullet-Liste in einen Platzhalter
                tf = ph.text_frame
                tf.clear()
                first = True
                for item in v:
                    para = tf.paragraphs[0] if first else tf.add_paragraph()
                    first = False
                    _inline_runs(para, str(item))
            else:
                ph.text_frame.text = str(v)
            used.add(ph.placeholder_format.idx)
    if data.get("notes"):
        slide.notes_slide.notes_text_frame.text = str(data["notes"])


def build(master_path, slides, out_path, remove_examples=True):
    """Master + Folien-Dicts -> PPTX. Gibt Warnungsliste zurueck."""
    prs = Presentation(str(master_path))
    if remove_examples and len(prs.slides):
        _strip_example_slides(prs)
    lm = LayoutMap(prs)
    warn = []
    size = (prs.slide_width, prs.slide_height)
    for data in slides:
        explicit = data.get("layout")
        kind = data.get("kind") or "content"
        AUTO = {"title", "content", "section", "closing", "picture", "table", "two", "three"}
        if explicit and str(explicit).lower() not in AUTO:
            lay = lm.by_number_or_name(explicit)
            if lay is None:
                warn.append(f"Layout '{explicit}' nicht gefunden - Standard genutzt")
                lay = lm.pick(kind)
        else:
            lay = lm.pick(kind)
        slide = prs.slides.add_slide(lay)
        _fill_slide(slide, lay, data, warn, size)
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(out_path))
    return warn
