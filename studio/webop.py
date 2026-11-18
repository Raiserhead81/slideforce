"""Studio: Website Operator - baut native PPTX via SlideForce DIREKT im venv
(import slideforce.profiles.build_vorlage, kein HTTP, keine manuellen XML-
Attribute - PowerPoint-Corruption-Lektion!).

Operator = deterministisch: Er normalisiert das Art-Design in das
build_vorlage-Slide-Dict-Vokabular, faellt je Folie auf das Storyboard
zurueck, wenn das KI-Design unbrauchbar ist, baut und validiert die PPTX.
"""
import re
import subprocess
import zipfile
from pathlib import Path

from slideforce.profiles import build_vorlage

# Erlaubte Slide-Dict-Keys (genau das, was build_vorlage versteht)
_KEYS = {"kind", "title", "subtitle", "meta", "kicker", "lead", "bullets",
         "table", "zeitstrahl", "heute", "botschaft", "zusatz", "hinweis",
         "notes", "teile", "image"}
_KV = re.compile(r"^(zahl|label|einheit|erklaerung|status)\d*$")
_CJK = re.compile(r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]+")
                                                                 # GLM-Glitches

MAX_BULLETS = 6
MAX_TABLE_ROWS = 9          # inkl. Kopfzeile
_MAXLEN = {"title": 100, "subtitle": 100, "meta": 90, "kicker": 40,
           "lead": 80, "botschaft": 320, "zusatz": 140, "hinweis": 110}
# Deterministische Klemmen gegen Critic-Befunde (Ueberlappungen/Ab schnitte):
_TITEL_MIT_LEAD = 48       # 1 Zeile 28pt, sonst kollidiert die Lead-Zeile
_TITEL_DECK = 48           # Titel-Folie: max 2 Zeilen 40pt
_ZAHL = 12                 # 40pt-Zahl darf nicht umbrechen
_LABEL = 32                 # KPI-Label: max 2 Zeilen in der Karte
_ZELLE = 34                # Tabellenzelle: kurze Werte, Wortgrenze
_ZS_LABEL = 14             # Zeitstrahl-Faehnchen


def _strip_md(t):
    """**fett**-Marker entfernen - erlaubt NUR in Karten-texten (bullets)."""
    return str(t).replace("**", "")


def _s(v, maxlen=None):
    t = _CJK.sub(" ", str(v or ""))         # chinesische Glitches raus
    t = re.sub(r"\s+", " ", t).strip()
    if t.lower() in ("none", "null", "-"):
        return ""
    t = re.sub(r"^[-\u2013\u2022]\s+", "", t)      # fuehrende Listenzeichen weg
    return t[:maxlen] if maxlen else t


def _zelle(v, n=_ZELLE):
    """Tabellenzelle: kompakt, an Satzende/Wortgrenze - nie mitten im Satz."""
    t = _s(v)
    if len(t) <= n:
        return t
    cut = t[:n]
    idx = max(cut.rfind("."), cut.rfind("!"), cut.rfind("?"))
    if idx >= 12:
        return t[:idx + 1]
    if " " in cut:
        cut = cut[:cut.rfind(" ")]
    return cut.rstrip(" ,;:")


def _sub_ok(txt):
    """hoechstens 2 'wert|bez'-Subs zulaessig (Renderer-Breite); weitere
    werden vom Aufrufer in Punkt-Karten-Text umgewandelt."""
    _sub_ok.n = getattr(_sub_ok, "n", 0) + 1
    return _sub_ok.n <= 2


def _bullets_norm(raw):
    _sub_ok.n = 0
    out = []
    if not isinstance(raw, list):
        return out
    for b in raw[:MAX_BULLETS]:
        if isinstance(b, (list, tuple)) and len(b) >= 2:
            try:
                lvl = 1 if int(float(b[0])) > 0 else 0
            except (TypeError, ValueError):
                lvl = 0
            txt = _satz_kapp(b[1], 150)
        elif isinstance(b, str):
            lvl, txt = 0, _satz_kapp(b, 150)
        else:
            continue
        if txt:
            if lvl == 0 and "|" in txt:          # KPI-Subwert: wert|bezeichnung
                wert, _, bez = txt.partition("|")
                wert, bez = wert.strip()[:12], _kapp(bez, 36)
                if wert and bez and _sub_ok(txt):
                    txt = f"{wert}|{bez}"
                elif bez or wert:                # zu viele subs -> normale Karte
                    txt = _kapp(f"{bez or wert}: {wert if bez else ''}".strip(": "), 160)
                else:
                    continue
            out.append([lvl, txt])
    return out


def _table_norm(raw):
    if not isinstance(raw, list):
        return None
    rows = [[_zelle(c) for c in r] if isinstance(r, (list, tuple)) else [_zelle(r)]
            for r in raw[:MAX_TABLE_ROWS]]
    rows = [r for r in rows if any(r)]
    if len(rows) < 2:
        return None
    ncols = max(len(r) for r in rows)
    return [r + [""] * (ncols - len(r)) for r in rows]


def _zeitstrahl_norm(raw):
    if not isinstance(raw, list):
        return None
    out = []
    for m in raw[:7]:
        if isinstance(m, (list, tuple)) and len(m) >= 2:
            eintrag = [str(m[0]), str(m[1]), str(m[2] if len(m) > 2 else "offen")]
        elif isinstance(m, str) and "|" in m:
            teile = [t.strip() for t in m.split("|")] + ["", "", ""]
            eintrag = teile[:3]
        else:
            continue
        if re.match(r"^\d{4}-\d{2}-\d{2}$|^\d{2}\.\d{2}\.\d{2,4}$", eintrag[0]):
            out.append([eintrag[0], _s(eintrag[1], _ZS_LABEL), eintrag[2]])
    return out if len(out) >= 2 else None


def _norm_slide(d, allow_teile=False):
    """Art-Design-Folie -> sauberes build_vorlage-Dict oder None."""
    if not isinstance(d, dict):
        return None
    kind = str(d.get("kind") or d.get("rolle") or "content").lower()
    if kind in ("title", "titel"):
        kind = "title"
    elif kind in ("section", "teil"):
        kind = "section"
    else:
        kind = "content"
    out = {"kind": kind, "layout": kind}
    for f in ("title", "subtitle", "meta", "kicker", "lead", "botschaft",
              "zusatz", "hinweis"):
        grenze = _MAXLEN.get(f)
        if f == "lead":
            v = _lead_ok(_strip_md(d.get(f)), grenze or 80)
        elif f in ("botschaft", "hinweis", "zusatz"):
            v = _satz_kapp(_strip_md(d.get(f)), grenze or 160, mindest=60)
        else:
            v = _kapp(_strip_md(d.get(f)), grenze)   # Wortgrenze, nie mid-word
        if v:
            out[f] = v
    # Klemmen gegen Ueberlappungen: kurzer Titel, wenn lead gesetzt;
    # Deck-Titel begrenzen (40pt, 2 Zeilen max)
    if out.get("title"):
        if kind == "title":
            out["title"] = _kapp(out["title"], _TITEL_DECK)
        elif out.get("lead") and len(out["title"]) > _TITEL_MIT_LEAD:
            out.pop("lead")   # Titel VOLLSTAENDIG behalten statt abzuhacken
    bl = _bullets_norm(d.get("bullets"))
    if bl:
        out["bullets"] = bl
    for k, v in d.items():
        if _KV.match(str(k)) and v is not None and v != "":
            if isinstance(v, (str, int, float)):
                wert = _s(_strip_md(v), _ZAHL if str(k).startswith("zahl")
                          else _LABEL)
                if wert:
                    out[str(k)] = _kapp(wert, _ZAHL if str(k).startswith("zahl")
                                        else _LABEL)
    tbl = _table_norm(d.get("table") or d.get("zeilen") and
                      [d.get("kopf")] + list(d.get("zeilen") or []))
    if tbl:
        out["table"] = tbl
    zs = _zeitstrahl_norm(d.get("zeitstrahl") or d.get("meilensteine"))
    if zs:
        out["zeitstrahl"] = zs
        hd = _s(d.get("heute"), 10)
        if re.match(r"^\d{4}-\d{2}-\d{2}$", hd):
            out["heute"] = hd
    if isinstance(d.get("image"), str) and d.get("image"):
        out["image"] = d["image"]          # Weg C: Infografik-PNG (existenz prueft Builder)
    if isinstance(d.get("notes"), (str, int, float)) and _s(d.get("notes")):
        out["notes"] = _s(d.get("notes"), 500)
    if allow_teile and isinstance(d.get("teile"), list):
        teile = [_s(t, 40) for t in d.get("teile") if _s(t)][:4]
        if teile:
            out["teile"] = teile
    hat_inhalt = (kind in ("title", "section") or out.get("bullets")
                  or out.get("table") or out.get("zeitstrahl")
                  or out.get("botschaft") or any(k.startswith("zahl") for k in out))
    if not hat_inhalt or (kind == "title" and not out.get("title")):
        return None
    # Nur whitelistete Keys durchlassen (ungewolltes KI-Feld rauswerfen)
    return {k: v for k, v in out.items() if k in _KEYS or _KV.match(k)}


def _kapp(t, n):
    """An Wortgrenze kappen - niemals mitten im Wort (Critic-Befund)."""
    t = _s(t)
    if len(t) <= n:
        return t
    cut = t[:n]
    if " " in cut:
        cut = cut[:cut.rfind(" ")]
    return cut.rstrip(" ,;:-")


def _satz_kapp(t, n, mindest=40):
    """An letztem Satzende (.!?) innerhalb n kappen, sonst Wortgrenze.
    Verhindert abgehackte Halbsaetze (Studio-Critic-Befund)."""
    t = _s(t)
    if len(t) <= n:
        return t
    cut = t[:n]
    idx = max(cut.rfind("."), cut.rfind("!"), cut.rfind("?"))
    if idx >= mindest:
        return t[:idx + 1].strip()
    if " " in cut:
        cut = cut[:cut.rfind(" ")]
    return cut.rstrip(" ,;:-")


def _lead_ok(t, n=80):
    """Lead-Zeile: NUR vollstaendig endende Saetze - sonst leer (Feld weg).
    Ein mitten im Satz gekappter Lead ist ein sicherer Critic-Makel."""
    t = _s(t)
    if len(t) <= n:
        return t if t.endswith((".", "!", "?", ":", "-")) else t
    cut = t[:n]
    idx = max(cut.rfind("."), cut.rfind("!"), cut.rfind("?"))
    return t[:idx + 1].strip() if idx >= 30 else ""


# ---------------------------------------------------------- Storyboard-Fallback
def _aus_storyboard(f, deck):
    """Deterministische Umwandlung einer Storyboard-Folie in ein Slide-Dict."""
    rolle = str(f.get("rolle", "content")).lower()
    if rolle == "titel":
        rolle = "title"
    if rolle == "teil":
        rolle = "section"
    out = {"kind": rolle if rolle in ("title", "section") else "content",
           "layout": ""}
    out["layout"] = out["kind"]
    out["title"] = _kapp(_strip_md(f.get("titel") or deck.get("deck_titel")),
                       _TITEL_MIT_LEAD if f.get("lead") else _MAXLEN["title"])
    if rolle == "title":
        out["title"] = _kapp(_strip_md(deck.get("deck_titel")), _TITEL_DECK)
        if deck.get("untertitel"):
            out["subtitle"] = _s(deck["untertitel"], _MAXLEN["subtitle"])
        out["meta"] = _s(f.get("meta") or deck.get("meta"), _MAXLEN["meta"])
        teile = [t for t in (deck.get("teile") or []) if t][:4]
        if teile:
            out["teile"] = [f"0{i+1}|{_s(t, 34)}" for i, t in enumerate(teile)]
        return out
    for feld in ("kicker", "lead"):
        if feld == "lead":
            v = _lead_ok(_strip_md(f.get(feld)), _MAXLEN["lead"])
        else:
            v = _kapp(_strip_md(f.get(feld)), _MAXLEN[feld])
        if v:
            out[feld] = v.upper() if feld == "kicker" else v
    bl = []
    for sub in (f.get("subs") or [])[:3]:
        if isinstance(sub, (list, tuple)) and len(sub) >= 2:
            wert, bez = _s(sub[0], 12), _kapp(sub[1], 36)
            if wert and bez and len([b for b in bl if "|" in b[1]]) < 2:
                bl.append([0, f"{wert}|{bez}"])
            elif bez:
                bl.append([0, _kapp(f"{bez}: {wert}", 160)])
    for p in (f.get("punkte") or []):
        if len(bl) >= MAX_BULLETS:
            break
        bl.append([0, _s(p, 200)])
    if rolle == "kpi":
        if _s(f.get("zahl")):
            out["zahl"] = _s(_strip_md(f.get("zahl")), _ZAHL)
        if _s(f.get("label")):
            out["label"] = _s(f.get("label"), _LABEL)
    if rolle == "statement":
        if _s(f.get("botschaft")):
            out["botschaft"] = _s(f.get("botschaft"), _MAXLEN["botschaft"])
        if _s(f.get("zusatz")):
            out["zusatz"] = _s(f.get("zusatz"), _MAXLEN["zusatz"])
    if rolle == "tabelle":
        kopf = [_zelle(c) for c in (f.get("kopf") or [])][:6]
        zeilen = [[_zelle(c) for c in z][:len(kopf) or 6]
                  for z in (f.get("zeilen") or [])][:MAX_TABLE_ROWS - 1]
        if kopf and zeilen:
            breite = max(len(kopf), max(len(z) for z in zeilen))
            out["table"] = [kopf + [""] * (breite - len(kopf))]
            out["table"] += [z + [""] * (breite - len(z)) for z in zeilen]
    if rolle == "zeitstrahl":
        zs = _zeitstrahl_norm(f.get("meilensteine"))
        if zs:
            out["zeitstrahl"] = zs
            hd = _s(f.get("heute"), 10)
            if re.match(r"^\d{4}-\d{2}-\d{2}$", hd):
                out["heute"] = hd
    if bl:
        out["bullets"] = bl
    ann = f.get("annahmen")
    if isinstance(ann, list) and ann:
        out["notes"] = _s("annahmen: " + "; ".join(str(a) for a in ann), 500)
    return out if out.get("title") else None


def slides_aus_design(design, storyboard):
    """Art-Design + Storyboard -> finale Slide-Dict-Liste (je Folie das
    bessere von beiden; Design kaputt -> deterministischer Fallback)."""
    sb_folien = storyboard.get("folien") or []
    ad_folien = []
    if isinstance(design, dict) and isinstance(design.get("folien"), list):
        ad_folien = design["folien"]
    slides, warn = [], []
    for i, sf in enumerate(sb_folien):
        ad = _norm_slide(ad_folien[i] if i < len(ad_folien) else None,
                         allow_teile=(i == 0))
        if ad is not None and (i > 0 or ad["kind"] == "title"):
            slides.append(ad)
        else:
            fb = _aus_storyboard(sf, storyboard)
            if fb is None:
                continue
            slides.append(fb)
            warn.append(f"Folie {i + 1}: Art-Design unbrauchbar -> Storyboard-Fallback")
    if not slides:
        slides = [fb for fb in (_aus_storyboard(f, storyboard) for f in sb_folien)
                  if fb]
        warn.append("komplettes Design unbrauchbar -> Storyboard-Fallback")
    # Erste Folie MUSS title sein (build_vorlage erwartet Cover/Sidebar-Struktur)
    if slides and slides[0]["kind"] != "title":
        t = _aus_storyboard({"rolle": "title"}, storyboard) or {
            "kind": "title", "layout": "title", "title": storyboard.get("deck_titel", "Praesentation")}
        slides[0] = t
    return slides, warn


def build_pptx(slides, out_path):
    """PPTX bauen + validieren (unzip-Test + python-pptx Reopen).
    Gibt (out_path, warnungen) zurueck; wirft bei hartem Fehler."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    warn = build_vorlage(slides, str(out_path))
    prs_ok = unzip_ok(out_path)
    if not prs_ok:
        raise RuntimeError(f"PPTX defekt (unzip-Test fehlgeschlagen): {out_path}")
    from pptx import Presentation as _P
    prs = _P(str(out_path))                       # Reopen-Test
    if len(prs.slides) != len(slides):
        raise RuntimeError(f"Folienzahl {len(prs.slides)} != {len(slides)} nach Reopen")
    return str(out_path), list(warn or [])


def unzip_ok(path):
    try:
        with zipfile.ZipFile(str(path)) as z:
            return z.testzip() is None
    except Exception:
        return False


def pptx_folienzahl(path):
    from pptx import Presentation as _P
    return len(_P(str(path)).slides)
