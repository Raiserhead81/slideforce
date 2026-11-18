"""SlideForce: Office-Reader. Word (.docx), Excel (.xlsx), CSV -> Folien."""
import csv as csvmod
from pathlib import Path
from .readers_text import _split_long, MAX_BULLETS, _chunk, _normalize

MAX_TABLE_ROWS = 16
MAX_TABLE_COLS = 10


def _mk(layout, title="", **kw):
    d = {"layout": layout, "title": title, "bullets": []}
    d.update(kw)
    return d


def read_docx(path):
    from docx import Document
    doc = Document(str(path))
    slides = []
    cur = None
    title_used = False
    for block in doc.iter_inner_content():
        if block.__class__.__name__ == "Table":
            rows = _table_rows(block)
            slides.append(_mk("content", cur["title"] if cur else "Tabelle",
                              table=rows, bullets=[]))
            continue
        text = block.text.strip()
        if not text:
            continue
        style = (block.style.name or "").lower()
        if style.startswith("title"):
            if not title_used:
                slides.append(_mk("title", text))
                title_used = True
                cur = slides[-1]
            else:
                cur = _mk("section", text)
                slides.append(cur)
        elif style.startswith("heading 1"):
            cur = _mk("content", text)
            slides.append(cur)
        elif style.startswith("heading"):
            cur = _mk("content", text)
            slides.append(cur)
        else:
            if cur is None or cur.get("layout") in ("title", "section"):
                cur = _mk("content", "")
                slides.append(cur)
            for piece in _split_long(text):
                cur["bullets"].append((0, piece))
    return _normalize(slides, Path(path).stem, True)


def _table_rows(tbl):
    rows = []
    for r in tbl.rows:
        cells = [c.text.strip() for c in r.cells][:MAX_TABLE_COLS]
        rows.append(cells)
    if len(rows) > MAX_TABLE_ROWS:
        rows = rows[:MAX_TABLE_ROWS - 1] + [["...", "..."]]
    return rows


def read_xlsx(path):
    import openpyxl
    wb = openpyxl.load_workbook(str(path), read_only=True, data_only=True)
    slides = []
    for ws in wb.worksheets:
        rows = []
        for row in ws.iter_rows(values_only=True):
            cells = ["" if v is None else str(v) for v in row][:MAX_TABLE_COLS]
            if any(c.strip() for c in cells):
                rows.append(cells)
            if len(rows) >= MAX_TABLE_ROWS:
                break
        if rows and len(rows[0]) >= 2:
            slides.append(_mk("content", ws.title or "Daten", table=rows))
        elif rows:
            slides.append(_mk("content", ws.title or "Daten",
                              bullets=[(0, c) for r in rows for c in r if c.strip()]))
    wb.close()
    return _normalize(slides, Path(path).stem, False)


def read_csv(path):
    rows = []
    raw = Path(path).read_text(encoding="utf-8-sig", errors="replace")
    delim = ";" if raw.count(";") >= raw.count(",") else ","
    for row in csvmod.reader(raw.splitlines(), delimiter=delim):
        if row:
            rows.append([c.strip() for c in row][:MAX_TABLE_COLS])
        if len(rows) >= MAX_TABLE_ROWS:
            break
    slides = []
    if rows:
        slides.append(_mk("content", Path(path).stem, table=rows))
    return _normalize(slides, Path(path).stem, False)
