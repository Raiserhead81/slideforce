"""SlideForce: HTML-Export. Folien-Dicts -> standalone HTML-Praesentation."""
import base64
import html
import re
from pathlib import Path
from .html_theme import extract_theme
from .masterprofil import lade_profil, rolle_zu_layout, layout_profil


def _md(text):
    s = html.escape(str(text))
    s = __import__("re").sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = __import__("re").sub(r"`(.+?)`", r"<code>\1</code>", s)
    s = __import__("re").sub(r"(?<!\*)\*([^*]+?)\*(?!\*)", r"<em>\1</em>", s)
    return s


def _b64(path):
    p = Path(path)
    if not p.is_file():
        return ""
    mime = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
            ".gif": "image/gif", ".webp": "image/webp", ".svg": "image/svg+xml"}
    m = mime.get(p.suffix.lower(), "image/png")
    return f"data:{m};base64," + base64.b64encode(p.read_bytes()).decode()


from .masterprofil import lade_profil, rolle_zu_layout, layout_profil

KIND_ROLLE = {"title": "titel", "section": "section", "statement": "statement",
              "botschaft": "statement", "zahl": "kpi", "kpi": "kpi",
              "agenda": "agenda", "summary": "agenda", "zusammenfassung": "agenda",
              "table": "table", "picture": "picture", "two": "two",
              "three": "three", "roadmap": "roadmap", "risiko": "risiko",
              "closing": "closing", "vier": "three", "content": "content"}

DUNKEL_ROLLEN = {"titel", "section", "statement", "closing"}

ASSETS = Path(__file__).resolve().parent / "assets"
_LOGO_B64 = None


def _dp_logo():
    """Base64-Anteil des Dataport-Logos (lazy gecacht, '' falls Datei fehlt)."""
    global _LOGO_B64
    if _LOGO_B64 is None:
        uri = _b64(ASSETS / "vorlage_dataport.png")
        _LOGO_B64 = uri.split("base64,", 1)[1] if uri else ""
    return _LOGO_B64



def _box(lay, typ, body=False):
    """Größte Box eines Typs aus Layout-Profil -> (x,y,w,h) oder None."""
    if not lay:
        return None
    kands = [p for p in lay["phs"] if p["type"] == typ]
    if body:
        kands = [p for p in kands if p["y"] < 90 and p["h"] > 2]
    if not kands:
        return None
    if typ == "title" and not body:
        return kands[0]
    return max(kands, key=lambda p: p["w"] * p["h"])


def _content_box(lay, t):
    """Groesste Nicht-Titel-Box unterhalb der Titelzone (Fusszeile ausgeschlossen)."""
    if not lay:
        return None
    grenze = (t["y"] + t["h"] * 0.6) if t else 10.0
    kands = [p for p in lay["phs"]
             if p["type"] != "title" and p["y"] >= grenze
             and p["h"] > 3 and p["y"] < 90]
    if not kands:
        return None
    return max(kands, key=lambda p: p["w"] * p["h"])


def _lay_css(genutzte, profil):
    """Positionier-CSS fuer alle genutzten Layout-Klassen."""
    teile = []
    for idx in sorted(genutzte):
        lay = layout_profil(profil, idx)
        if not lay:
            continue
        t = _box(lay, "title")
        b = _content_box(lay, t)
        teile.append(f".lay-{idx}{{padding:0}}")
        if t:
            teile.append(f".lay-{idx} .tbox{{position:absolute;left:{t['x']}%;top:{t['y']}%;"
                         f"width:{t['w']}%;display:flex;flex-direction:column;justify-content:center}}")
            teile.append(f".lay-{idx} h2{{left:{t['x']}%;top:{t['y']}%;"
                         f"width:{t['w']}%;position:absolute;margin:0;text-align:left}}")
        if b:
            teile.append(f".lay-{idx} .bwrap{{position:absolute;left:{b['x']}%;top:{b['y']}%;"
                         f"width:{b['w']}%;height:{b['h']}%;display:flex;flex-direction:column;"
                         f"justify-content:center}}")
    return "\n".join(teile)


def _render_slide_raw(s, profil=None):
    kind = s.get("kind", "content")

    title = _md(s.get("title") or "")
    rolle = KIND_ROLLE.get(kind, "content")
    lay_idx = rolle_zu_layout(profil, rolle) if profil else None
    lkl = f" lay-{lay_idx}" if lay_idx is not None else ""
    hell = " hell" if profil and rolle not in DUNKEL_ROLLEN else ""
    if kind == "title":
        sub = _md(s.get("subtitle") or "")
        band = (f'<div class="brandband"><div class="goldlinie"></div>'
                f'<h1>{title}</h1><p class="subtitle">{sub}</p></div>')
        if lay_idx is not None:
            return (f'<section class="slide s-title{hell}{lkl}"><div class="tbox">'
                    f'<div class="kicker"></div></div>{band}</section>')
        return (f'<section class="slide s-title"><div class="kicker"></div>'
                f'{band}</section>')
    if kind == "section":
        if lay_idx is not None:
            return (f'<section class="slide s-section{hell}{lkl}">'
                    f'<div class="tbox"><h1>{title}</h1></div></section>')
        return f'<section class="slide s-section"><h1>{title}</h1></section>'
    if s.get("botschaft"):
        zusatz = _md(s.get("zusatz") or "")
        kern = (f'<p class="msg">{_md(s["botschaft"])}</p>'
                f'<p class="zside">{zusatz}</p>')
        if lay_idx is not None:
            return (f'<section class="slide s-statement{hell}{lkl}">'
                    f'<div class="bwrap">{kern}</div></section>')
        return f'<section class="slide s-statement">{kern}</section>'
    if s.get("zahl"):
        einheit = _md(s.get("einheit") or "")
        erk = _md(s.get("erklaerung") or "")
        einord = _md(s.get("einordnung") or "")
        kern = (f'<h2>{title}</h2><div class="kpi">'
                f'<span class="num">{_md(s["zahl"])}</span>'
                f'<span class="unit">{einheit}</span></div>'
                f'<p class="erk">{erk}</p><p class="einord">{einord}</p>')
        if lay_idx is not None:
            return (f'<section class="slide s-kpi{hell}{lkl}">'
                    f'<div class="bwrap">{kern}</div></section>')
        return f'<section class="slide s-kpi">{kern}</section>'
    parts = [f'<section class="slide s-content{hell}{lkl}">']
    if title:
        parts.append(f"<h2>{title}</h2>")
    if s.get("table"):
        rows = s["table"]
        head = "".join(f"<th>{_md(c)}</th>" for c in rows[0])
        body = "".join("<tr>" + "".join(f"<td>{_md(c)}</td>" for c in r) + "</tr>"
                       for r in rows[1:])
        parts.append(f'<table class="data"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>')
    if s.get("image"):
        src = _b64(s["image"])
        if src:
            parts.append(f'<img class="pic" src="{src}" alt="">')
    if s.get("bullets"):
        items = "".join(_bullet(level, text) for level, text in s["bullets"])
        parts.append(f"<ul>{items}</ul>")
    if s.get("notes"):
        parts.append(f"<!-- notes: {html.escape(str(s['notes']))} -->")
    if lay_idx is not None and len(parts) > 1:
        koerper = parts[1:]
        parts = [parts[0]] + ['<div class="bwrap">'] + koerper + ["</div>"]
    parts.append("</section>")
    return "".join(parts)


def _render_slide(s, profil=None):
    out = _render_slide_raw(s, profil)
    logo = _dp_logo()
    if logo:
        out = out.replace(
            ">",
            f"><img src='data:image/png;base64,{logo}' class='dplogo' alt='dataport'>",
            1)
    return out


def _bullet(level, text):

    inner = _md(text)
    if level:
        return f"<li class='l2'>{inner}</li>"
    return f"<li>{inner}</li>"


TEMPLATE = """<!DOCTYPE html>
<html lang=de><head><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<title>__TITLE__</title><style>
:root{--bg:__BG__;--fg:__FG__;--paper:__PAPER__;--a1:__A1__;--a1h:__A1H__;--a2:__A2__;--major:__MAJOR__;--minor:__MINOR__;}
*{margin:0;box-sizing:border-box}body{background:#111;font-family:var(--minor),sans-serif;overflow:hidden}
.slide{position:absolute;inset:0;background:var(--bg);color:var(--fg);display:none;flex-direction:column;justify-content:center;padding:7vh 9vw}
.slide.active{display:flex}
.slide.hell{background:var(--paper);color:#232b34}
.slide.hell h2{color:var(--a1h)}
.slide.hell li:before{background:var(--a1h)}
.slide.hell table.data th{background:var(--a1h)}
.slide.hell .kicker{background:var(--a1h)}
__LAYCSS__
.s-title h1,.s-section h1{font-family:var(--major),sans-serif;font-size:clamp(2.2rem,6vw,4.5rem);line-height:1.1}
.s-title{display:flex;flex-direction:column;justify-content:space-between;background:var(--paper)}
.s-title .kicker{width:110px;height:10px;background:var(--a1);margin:9vh 0 0 6vw}
.s-title .brandband{background:var(--a2);padding:5.5vh 6vw 6.5vh;margin-top:auto}
.s-title .brandband .goldlinie{width:130px;height:7px;background:var(--a1);margin-bottom:2.6vh}
.s-title .brandband h1{color:#fff;font-size:clamp(2.4rem,5.2vw,4.2rem)}
.s-title .brandband .subtitle{color:rgba(255,255,255,.86);opacity:1;font-size:clamp(1.15rem,2.1vw,1.5rem);margin-top:1.4vh}
.s-section h1{color:var(--a2)}
.s-content h2,.s-kpi h2{font-family:var(--major),sans-serif;font-size:clamp(1.6rem,3.6vw,2.6rem);color:var(--a2);margin-bottom:3.5vh}
.s-content ul{list-style:none;font-size:clamp(1.05rem,2.1vw,1.5rem);line-height:1.55}
.s-content li{padding-left:1.6em;position:relative;margin-bottom:1.1vh}
.s-content li:before{content:"";position:absolute;left:0;top:.52em;width:.6em;height:.6em;background:var(--a1)}
.s-content li.l2:before{width:.35em;height:.35em;background:var(--a2);margin-top:.1em}
.s-content li.l2{padding-left:3em;font-size:.92em;opacity:.85}
table.data{border-collapse:collapse;width:100%;font-size:clamp(.95rem,1.9vw,1.35rem)}
table.data th{background:var(--a1);color:#fff;text-align:left;padding:.55em .8em}
table.data td{padding:.5em .8em;border-bottom:1px solid rgba(128,128,128,.35)}
img.pic{max-width:46%;max-height:58vh;position:absolute;right:5vw;top:22vh;border-radius:6px}
.s-content p,.s-kpi p{font-size:clamp(1rem,2vw,1.4rem);margin-top:1vh;opacity:.85}
.s-statement .msg{font-family:var(--major),sans-serif;font-size:clamp(2rem,5.2vw,3.8rem);line-height:1.15;color:var(--fg)}
.s-statement .zside{margin-top:4vh;font-size:clamp(1rem,2vw,1.4rem);opacity:.7}
.s-kpi .kpi{display:flex;align-items:baseline;gap:.3em}
.s-kpi .num{font-family:var(--major),sans-serif;font-size:clamp(4rem,13vw,10rem);font-weight:700;color:var(--a1)}
.s-kpi .unit{font-size:clamp(1.6rem,4vw,3rem);opacity:.8}
.s-kpi .erk{font-size:clamp(1.2rem,2.6vw,1.9rem)}
.s-kpi .einord{opacity:.6;font-size:clamp(1rem,2vw,1.3rem)}
.dplogo{position:absolute;top:14px;right:22px;width:150px;z-index:5;pointer-events:none}
.s-title .dplogo{width:230px}
#bar{position:fixed;left:0;bottom:0;height:5px;background:var(--a1);width:0;transition:width .25s;z-index:9}
#cnt{position:fixed;right:16px;bottom:12px;color:#888;font-size:13px;z-index:9;font-family:monospace}
#dots{position:fixed;left:50%;transform:translateX(-50%);bottom:12px;display:flex;gap:6px;z-index:9}
#dots i{width:8px;height:8px;border-radius:50%;background:#555;cursor:pointer}
#dots i.on{background:var(--a1)}
</style></head><body>
__SLIDES__
<div id=bar></div><div id=cnt></div><div id=dots></div>
<script>
var sl=[].slice.call(document.querySelectorAll('.slide')),i=0,d=document.getElementById('dots');
function go(n){i=Math.max(0,Math.min(sl.length-1,n));sl.forEach(function(s,j){s.classList.toggle('active',j==i)});
document.getElementById('bar').style.width=((i+1)/sl.length*100)+'%';
document.getElementById('cnt').textContent=(i+1)+' / '+sl.length;
d.innerHTML='';sl.forEach(function(_,j){var b=document.createElement('i');b.className=j==i?'on':'';b.onclick=function(){go(j)};d.appendChild(b)});
history.replaceState(null,'','#'+(i+1))}
document.addEventListener('keydown',function(e){
if(['ArrowRight','ArrowDown','PageDown',' '].includes(e.key)){e.preventDefault();go(i+1)}
if(['ArrowLeft','ArrowUp','PageUp'].includes(e.key)){e.preventDefault();go(i-1)}
if(e.key=='Home')go(0);if(e.key=='End')go(sl.length-1);
if(e.key=='f')document.documentElement.requestFullscreen&&document.documentElement.requestFullscreen()});
document.addEventListener('click',function(e){go(i+(e.clientX>innerWidth/2?1:-1))});
var tx=null;document.addEventListener('touchstart',function(e){tx=e.touches[0].clientX});
document.addEventListener('touchend',function(e){if(tx==null)return;var dx=e.changedTouches[0].clientX-tx;if(Math.abs(dx)>50)go(i+(dx<0?1:-1));tx=null});
var h=parseInt(location.hash.slice(1));go(isNaN(h)?0:h-1);
</script></body></html>"""


def _luma(hexcol):
    h = (hexcol or "ffffff").lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return 0.299 * r + 0.587 * g + 0.114 * b


def build_html(slides, title, out_path, master_path=None):
    profil = lade_profil(master_path) if master_path else None
    theme = (profil or {}).get("theme")
    if theme is None and master_path:
        theme = extract_theme(master_path)
    c = (theme or {}).get("colors", {})
    f = (theme or {}).get("fonts", {})
    cands = [x for x in (c.get("accent3"), c.get("lt2"), c.get("dk2")) if x]
    bg = min(cands, key=_luma) if cands else "#1c2733"
    if _luma(bg) > 100:
        bg = "#1c2733"
    fg = c.get("lt1", "#ffffff") if _luma(bg) <= 100 else c.get("dk1", "#222222")
    # Papierfarbe + kräftiger Akzent fuer helle Folien aus dem Theme lernen
    paper_cands = [x for x in (c.get("dk2"), c.get("lt1"), c.get("accent3")) if x]
    paper = min(paper_cands, key=_luma) if paper_cands else "#f4f6f8"
    if _luma(paper) < 150:
        paper = "#f4f6f8"
    akzent_cands = [x for x in (c.get("lt2"), c.get("accent1"), c.get("accent2"),
                                c.get("dk2")) if x and _luma(x) < 170]
    a1h = akzent_cands[0] if akzent_cands else c.get("accent1", "#2e74b5")
    body = "\n".join(_render_slide(s, profil) for s in slides)
    laycss = ""
    if profil:
        genutzt = {int(m) for m in re.findall(r"lay-(\d+)", body)}
        laycss = _lay_css(genutzt, profil)
    doc = (TEMPLATE.replace("__TITLE__", html.escape(str(title)))
           .replace("__SLIDES__", body)
           .replace("__LAYCSS__", laycss)
           .replace("__BG__", bg).replace("__FG__", fg)
           .replace("__PAPER__", paper).replace("__A1H__", a1h)
           .replace("__A1__", c.get("accent1", a1h))
           .replace("__A2__", c.get("accent2", "#ed7d31"))
           .replace("__MAJOR__", f.get("major", "Georgia"))
           .replace("__MINOR__", f.get("minor", "Arial")))
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(doc, encoding="utf-8")
    return len(slides)
