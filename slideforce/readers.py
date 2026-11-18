"""SlideForce: Content-Dispatcher. Erkennt Dateityp, liefert Folien-Dicts."""
from pathlib import Path
from .readers_text import read_text
from .readers_office import read_docx, read_xlsx, read_csv


def read_content(path, source_title=None):
    """Beliebigen Content (md/txt/docx/xlsx/csv) -> Liste von Folien-Dicts."""
    p = Path(path)
    suf = p.suffix.lower()
    title = source_title or p.stem
    if suf in (".md", ".markdown", ".txt"):
        return read_text(p.read_text(encoding="utf-8", errors="replace"), title)
    if suf == ".docx":
        return read_docx(p)
    if suf in (".xlsx", ".xlsm"):
        return read_xlsx(p)
    if suf == ".csv":
        return read_csv(p)
    raise ValueError(f"Nicht unterstuetztes Format: {suf} (erlaubt: md, txt, docx, xlsx, csv)")
