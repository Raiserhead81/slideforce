"""SlideForce: Text/Markdown-Reader. Wandelt Transcript, Text oder MD in Folien."""
import re

MAX_BULLETS = 6          # b28-Zeilen-Karten: max 6 pro Folie, Rest -> Fortsetzungsfolie
MAX_BULLET_CHARS = 220   # laengere Absaetze werden an Saetzen gesplittet


def _chunk(items, n=MAX_BULLETS):
    return [items[i:i + n] for i in range(0, len(items), n)]


def _split_long(text):
    """Lange Absaetze an Satzenden in handliche Bullets splitten."""
    if len(text) <= MAX_BULLET_CHARS:
        return [text]
    parts = re.split(r"(?<=[.!?])\s+", text)
    out, buf = [], ""
    for p in parts:
        if buf and len(buf) + len(p) + 1 > MAX_BULLET_CHARS:
            out.append(buf.strip())
            buf = p
        else:
            buf = (buf + " " + p).strip()
    if buf:
        out.append(buf.strip())
    return out


def _new_slide(slides, cur_ref, layout="content", title="", **kw):
    cur = {"layout": layout, "title": title, "bullets": []}
    cur.update(kw)
    slides.append(cur)
    return cur


def read_text(text, source_title="Präsentation"):
    """Markdown oder nackter Text -> Liste von Folien-Dicts.

    Format: '# ' Titelfolie (erste) / Abschnitt, '## ' Folientitel,
    '- ' Bullets (2 Spaces = Unterpunkt), '---' Folientrenner,
    '![](bild.png)' Bild, '| a | b |' Tabelle.
    """
    slides = []
    cur = None
    first_h1 = True
    had_heading = False
    for raw in text.splitlines():
        line = raw.rstrip()
        s = line.strip()
        if not s:
            continue
        if s in ("---", "***", "___"):
            cur = None
            continue
        m = re.match(r"^(#{1,6})\s+(.*)$", s)
        if m:
            had_heading = True
            lvl, t = len(m.group(1)), m.group(2).strip()
            if lvl == 1 and first_h1:
                cur = _new_slide(slides, cur, "title", t)
                first_h1 = False
            elif lvl == 1:
                cur = _new_slide(slides, cur, "section", t)
            else:
                cur = _new_slide(slides, cur, "content", t)
            continue
        bm = re.match(r"^(\s*)(?:[-*+]|\d+[.)])\s+(.*)$", raw)
        if bm:
            if cur is None or cur.get("layout") in ("title", "section"):
                cur = _new_slide(slides, cur, "content", "")
            level = 1 if len(bm.group(1)) >= 2 else 0
            for piece in _split_long(bm.group(2).strip()):
                cur["bullets"].append((level, piece))
            continue
        img = re.match(r"^!\[[^\]]*\]\(([^)]+)\)\s*$", s)
        if img:
            if cur is None or cur.get("layout") in ("title", "section"):
                cur = _new_slide(slides, cur, "content", "")
            cur["image"] = img.group(1)
            continue
        if s.startswith("|") and s.endswith("|"):
            cells = [c.strip() for c in s.strip("|").split("|")]
            if cur is None or cur.get("layout") in ("title", "section"):
                cur = _new_slide(slides, cur, "content", "")
            cur.setdefault("table", []).append(cells)
            continue
        # key: wert am Folienanfang -> Master-Platzhalter (z.B. botschaft:, zahl:)
        kv = re.match(r"^([A-Za-z\xc4\xd6\xdc\xe4\xf6\xfc\xdf][\w\xe4\xf6\xfc\xdf -]{0,24}):\s+(.+)$", s)
        if kv:
            key = kv.group(1).strip().lower()
            if cur is None or cur.get("bullets") or cur.get("table") or cur.get("image"):
                cur = _new_slide(slides, cur, "content", "")
            if key == "title" and not cur.get("title"):
                cur["title"] = kv.group(2).strip()
            elif key in ("layout", "kind", "subtitle", "notes"):
                cur[key if key != "kind" else "layout"] = kv.group(2).strip()
            else:
                cur[key] = kv.group(2).strip()
            continue
        # nackter Absatztext (Transcript) -> Bullets
        if cur is None or cur.get("layout") in ("title", "section"):
            if cur is not None and cur["layout"] == "title" and not cur.get("subtitle"):
                cur["subtitle"] = s
                continue
            cur = _new_slide(slides, cur, "content", "")
        for piece in _split_long(s):
            cur["bullets"].append((0, piece))
    META = {"layout", "kind", "title", "subtitle", "bullets", "table", "image", "notes"}
    slides = [sl for sl in slides
              if sl.get("bullets") or sl.get("table") or sl.get("image")
              or any(k not in META for k in sl)
              or sl["layout"] in ("title", "section")]
    return _normalize(slides, source_title, had_heading)


def _normalize(slides, source_title, had_heading):
    """Titelfolie ergaenzen, lange Folien splitten, kind-Felder setzen."""
    if not any(sl["layout"] == "title" for sl in slides):
        first = next((sl for sl in slides), None)
        title, subtitle = source_title, ""
        if first and first.get("bullets") and first["bullets"][0][1]:
            title = first["bullets"][0][1][:80]
            first["bullets"] = first["bullets"][1:]
        slides.insert(0, {"layout": "title", "title": title, "subtitle": subtitle, "bullets": []})
    out = []
    for sl in slides:
        kind = {"title": "title", "section": "section"}.get(sl["layout"], "content")
        sl["kind"] = kind
        out.append(sl)
        bl = sl.get("bullets") or []
        if len(bl) > MAX_BULLETS and sl["layout"] == "content":
            for part in _chunk(bl[MAX_BULLETS:]):
                out.append({"layout": "content", "kind": "content",
                            "title": (sl.get("title") or "") + " (Fortsetzung)",
                            "bullets": part})
            sl["bullets"] = bl[:MAX_BULLETS]
    return out
