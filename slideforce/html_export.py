"""SlideForce: HTML-Export. Folien-Dicts -> standalone HTML-Praesentation."""
import base64
import html
from pathlib import Path
from .html_theme import extract_theme


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


def _render_slide(s):
    kind = s.get("kind", "content")
    title = _md(s.get("title") or "")
    if kind == "title":
        sub = _md(s.get("subtitle") or "")
        return f'<section class="slide s-title"><div class="kicker"></div>' \
               f'<h1>{title}</h1><p class="subtitle">{sub}</p></section>'
    if kind == "section":
        return f'<section class="slide s-section"><h1>{title}</h1></section>'
    if s.get("botschaft"):
        zusatz = _md(s.get("zusatz") or "")
        return f'<section class="slide s-statement"><p class="msg">{_md(s["botschaft"])}</p>' \
               f'<p class="zside">{zusatz}</p></section>'
    if s.get("zahl"):
        einheit = _md(s.get("einheit") or "")
        erk = _md(s.get("erklaerung") or "")
        einord = _md(s.get("einordnung") or "")
        return f'<section class="slide s-kpi"><h2>{title}</h2><div class="kpi">' \
               f'<span class="num">{_md(s["zahl"])}</span><span class="unit">{einheit}</span></div>' \
               f'<p class="erk">{erk}</p><p class="einord">{einord}</p></section>'
    parts = [f'<section class="slide s-content">']
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
    parts.append("</section>")
    return "".join(parts)


def _bullet(level, text):
    inner = _md(text)
    if level:
        return f"<li class='l2'>{inner}</li>"
    return f"<li>{inner}</li>"


TEMPLATE = """<!DOCTYPE html>
<html lang=de><head><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<title>__TITLE__</title><style>
:root{--bg:__BG__;--fg:__FG__;--a1:__A1__;--a2:__A2__;--major:__MAJOR__;--minor:__MINOR__;}
*{margin:0;box-sizing:border-box}body{background:#111;font-family:var(--minor),sans-serif;overflow:hidden}
.slide{position:absolute;inset:0;background:var(--bg);color:var(--fg);display:none;flex-direction:column;justify-content:center;padding:7vh 9vw}
.slide.active{display:flex}
.s-title h1,.s-section h1{font-family:var(--major),sans-serif;font-size:clamp(2.2rem,6vw,4.5rem);line-height:1.1}
.s-title .kicker{width:70px;height:8px;background:var(--a1);margin-bottom:3vh}
.s-title .subtitle{font-size:clamp(1.1rem,2.4vw,1.7rem);opacity:.75;margin-top:2vh}
.s-section h1{color:var(--a1)}
.s-content h2,.s-kpi h2{font-family:var(--major),sans-serif;font-size:clamp(1.6rem,3.6vw,2.6rem);color:var(--a1);margin-bottom:3.5vh}
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
    theme = extract_theme(master_path) if master_path else None
    c = (theme or {}).get("colors", {})
    f = (theme or {}).get("fonts", {})
    cands = [x for x in (c.get("accent3"), c.get("lt2"), c.get("dk2")) if x]
    bg = min(cands, key=_luma) if cands else "#1c2733"
    if _luma(bg) > 100:
        bg = "#1c2733"
    fg = c.get("lt1", "#ffffff") if _luma(bg) <= 100 else c.get("dk1", "#222222")
    body = "\n".join(_render_slide(s) for s in slides)
    doc = (TEMPLATE.replace("__TITLE__", html.escape(str(title)))
           .replace("__SLIDES__", body)
           .replace("__BG__", bg).replace("__FG__", fg)
           .replace("__A1__", c.get("accent1", "#2e74b5"))
           .replace("__A2__", c.get("accent2", "#ed7d31"))
           .replace("__MAJOR__", f.get("major", "Georgia"))
           .replace("__MINOR__", f.get("minor", "Arial")))
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(doc, encoding="utf-8")
    return len(slides)
