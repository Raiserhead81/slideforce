"""dataport Editorial-Design-System fuer Studio Weg B.

Handgebaute Folien-Templates (Agentur-Niveau, konstant):
GLM liefert nur INHALTE (Storyboard/Design-Dicts), das Layout ist fix.
Folie: 1600x900, Brand: Petrol #39756F / Rot #9E292B / Karten #F4F5F6.
"""

BASIS_CSS = """
*{margin:0;padding:0;box-sizing:border-box}
body{width:1600px;height:900px;overflow:hidden;position:relative;
  font-family:Arial,Helvetica,sans-serif;background:#fff;color:#39424A}
.kicker{font-size:20px;font-weight:700;letter-spacing:.28em;text-transform:uppercase;
  color:#39756F;margin-bottom:18px}
.h1{font-size:52px;line-height:1.15;font-weight:700;color:#243038;letter-spacing:-.01em}
.h2{font-size:34px;line-height:1.2;font-weight:700;color:#243038}
.sub{font-size:24px;color:#54616E;line-height:1.4}
.karte{background:#F4F5F6;border-radius:16px;padding:32px 36px}
.hairline{height:1px;background:#D8DEE2}
.zahl{font-weight:700;color:#39756F;letter-spacing:-.02em;line-height:1}
.accent{width:64px;height:6px;background:#9E292B;border-radius:3px}
.petaline{width:64px;height:6px;background:#39756F;border-radius:3px}
.foot{position:absolute;bottom:34px;left:90px;right:90px;display:flex;
  justify-content:space-between;font-size:17px;color:#8A93A3}
.logo{position:absolute;top:44px;right:90px;height:52px;width:auto}
.icon{width:52px;height:52px;flex:0 0 52px}
.icon svg{width:100%;height:100%;stroke:#39756F;fill:none;
  stroke-width:2;stroke-linecap:round;stroke-linejoin:round}
"""


def _logo_img(pos="top-right"):
    """Logo-Markup (Position per CSS-Klasse .logo im body)."""
    from pathlib import Path
    import base64
    p = Path(__file__).resolve().parent.parent / "slideforce" / "assets" / "vorlage_dataport.png"
    uri = "data:image/png;base64," + base64.b64encode(p.read_bytes()).decode()
    return f'<img class="logo" src="{uri}">'


def _fuss(nr, gesamt, brand="dataport"):
    return (f'<div class="foot"><span>{brand}</span>'
            f'<span>Folie {nr} / {gesamt}</span></div>')


def seite(html_body, nr, gesamt, extra_css=""):
    return (f"<!doctype html><html><head><meta charset='utf-8'>"
            f"<style>{BASIS_CSS}{extra_css}</style></head><body>"
            f"{html_body}{_logo_img()}{_fuss(nr, gesamt)}</body></html>")


# Stroke-Icon-Bibliothek (einheitlicher Stil, Petrol via .icon svg)
ICONS = {
    "pin": '<svg viewBox="0 0 24 24"><path d="M12 21s-7-6.2-7-11a7 7 0 0 1 14 0c0 4.8-7 11-7 11z"/><circle cx="12" cy="10" r="2.6"/></svg>',
    "uhr": '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3.5 2.5"/></svg>',
    "check": '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><path d="M8 12.5l2.6 2.6L16 9.5"/></svg>',
    "pfeil": '<svg viewBox="0 0 24 24"><path d="M4 12h14"/><path d="M13 6l6 6-6 6"/></svg>',
    "anker": '<svg viewBox="0 0 24 24"><circle cx="12" cy="5" r="2.4"/><path d="M12 7.4V21"/><path d="M5 13a7 7 0 0 0 14 0"/><path d="M8 10H4m16 0h-4"/></svg>',
    "flagge": '<svg viewBox="0 0 24 24"><path d="M6 21V4"/><path d="M6 4h12l-2.5 4L18 12H6"/></svg>',
    "ziel": '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1.4"/></svg>',
    "geld": '<svg viewBox="0 0 24 24"><rect x="3" y="7" width="18" height="11" rx="2"/><circle cx="12" cy="12.5" r="2.8"/><path d="M6 7V5h12v2"/></svg>',
    "gabel": '<svg viewBox="0 0 24 24"><path d="M12 3v18"/><path d="M5 8l7-5 7 5"/><path d="M5 8v5h5V8M14 8v5h5V8"/></svg>',
    "liste": '<svg viewBox="0 0 24 24"><path d="M8 6h12M8 12h12M8 18h12"/><circle cx="4" cy="6" r="1"/><circle cx="4" cy="12" r="1"/><circle cx="4" cy="18" r="1"/></svg>',
    "warn": '<svg viewBox="0 0 24 24"><path d="M12 3L2.5 20h19L12 3z"/><path d="M12 9.5v5"/><circle cx="12" cy="17.2" r=".4"/></svg>',
    "sync": '<svg viewBox="0 0 24 24"><path d="M20 12a8 8 0 1 1-2.3-5.6"/><path d="M20 3v4h-4"/></svg>',
}


def _s(v, max_=None):
    import re
    t = re.sub(r"\*\*(.+?)\*\*", r"\1", str(v or "")).strip()
    return (t[:max_] + "...") if max_ and len(t) > max_ else t


def _zahlfelder(sl):
    out = []
    i = 1
    while True:
        z = sl.get("zahl" if i == 1 else f"zahl{i}")
        if z is None or i > 4:
            break
        out.append({"zahl": _s(z, 8), "label": _s(sl.get(f"label{i}" if i > 1 else "label"), 42),
                    "erklaerung": _s(sl.get(f"erklaerung{i}" if i > 1 else "erklaerung"), 90)})
        i += 1
    return out


def f_titel(sl, nr, gesamt):
    body = f"""<div style="position:absolute;left:110px;top:200px;width:1080px">
<div class="kicker">{_s(sl.get('kicker'), 40) or 'VORSTANDS-PRÄSENTATION'}</div>
<div class="h1">{_s(sl.get('title'), 120)}</div>
<div style="margin:34px 0 0"><div class="accent"></div></div>
<div class="sub" style="margin-top:34px;max-width:900px">{_s(sl.get('subtitle'), 160)}</div>
</div>"""
    return seite(body, nr, gesamt)


def f_teil(sl, nr, gesamt):
    teile = sl.get("teile") or []
    punkte = "".join(f'<div style="display:flex;align-items:center;gap:16px;margin:14px 0">'
                     f'<span style="width:10px;height:10px;border-radius:50%;background:#39756F"></span>'
                     f'<span style="font-size:24px;color:#54616E">{_s(t, 50)}</span></div>' for t in teile)
    num = str(sl.get("nr") or nr)
    body = f"""<div style="position:absolute;left:110px;top:170px;width:640px">
<div class="kicker">TEIL {num}</div>
<div class="h1">{_s(sl.get('title'), 80)}</div>
<div style="margin:30px 0 0"><div class="petaline"></div></div>
<div class="sub" style="margin-top:30px">{_s(sl.get('subtitle'), 140)}</div>
<div style="margin-top:44px">{punkte}</div></div>"""
    return seite(body, nr, gesamt)


def f_kpi(sl, nr, gesamt):
    felder = _zahlfelder(sl)
    icons = ["pin", "uhr", "check", "geld"]
    n = max(1, len(felder))
    cards = ""
    for i, f in enumerate(felder):
        ic = ICONS[icons[i % len(icons)]]
        cards += f"""<div class="karte" style="flex:1;display:flex;flex-direction:column;overflow:hidden">
<div style="display:flex;align-items:center;gap:18px;margin-bottom:20px">
<div class="icon">{ic}</div><div class="kicker" style="margin:0">{_s(f['label'], 30)}</div></div>
<div class="zahl" style="font-size:76px">{_s(f['zahl'], 8)}</div>
<div class="sub" style="margin-top:14px;font-size:19px">{f['erklaerung']}</div></div>"""
    body = f"""<div style="position:absolute;left:90px;top:110px;right:320px">
<div class="kicker">{_s(sl.get('kicker'), 40)}</div>
<div class="h2">{_s(sl.get('title'), 110)}</div></div>
<div style="position:absolute;left:90px;right:90px;top:300px;bottom:110px;display:flex;gap:28px;align-items:stretch">{cards}</div>"""
    return seite(body, nr, gesamt)


def f_karten(sl, nr, gesamt):
    bullets = sl.get("bullets") or []
    icons = ["sync", "warn", "gabel", "flagge", "liste", "ziel"]
    n = max(1, len(bullets))
    cols = 2 if n <= 4 else 3
    cards = ""
    for i, b in enumerate(bullets[:6]):
        if isinstance(b, (list, tuple)):
            b = b[-1]
        t = _s(b, 150)
        titel, text = (t_ := t.split(":", 1))[0].strip(), t_[1].strip() if ":" in t else ("", t)
        ic = ICONS[icons[i % len(icons)]]
        cards += f"""<div class="karte" style="display:flex;gap:22px;align-items:flex-start">
<div class="icon">{ic}</div>
<div><div style="font-size:23px;font-weight:700;color:#243038;margin-bottom:10px">{titel or _s(sl.get('title'), 30)}</div>
<div style="font-size:19px;color:#54616E;line-height:1.45">{text or t}</div></div></div>"""
    body = f"""<div style="position:absolute;left:90px;top:80px;right:300px">
<div class="kicker">{_s(sl.get('kicker'), 40)}</div>
<div class="h2">{_s(sl.get('title'), 110)}</div>
<div style="margin:24px 0 0"><div class="hairline" style="width:400px"></div></div></div>
<div style="position:absolute;left:90px;right:90px;top:300px;display:grid;
grid-template-columns:repeat({cols},1fr);gap:26px;align-content:start">{cards}</div>"""
    return seite(body, nr, gesamt)


def f_zeitstrahl(sl, nr, gesamt):
    zs = sl.get("zeitstrahl") or []
    punkte = ""
    w = 1400 / max(1, len(zs))
    for i, m in enumerate(zs):
        if isinstance(m, dict):
            label, text = _s(m.get("label") or m.get("titel"), 30), _s(m.get("text") or m.get("beschreibung"), 70)
        else:
            t = _s(m, 70); label, _, text = t.partition(" ")
        x = 90 + i * w
        punkte += f"""<div style="position:absolute;left:{x:.0f}px;top:0;width:{w-40:.0f}px">
<div style="width:18px;height:18px;border-radius:50%;background:#39756F;margin:18px auto 0"></div>
<div class="karte" style="margin-top:34px;min-height:190px">
<div style="font-size:21px;font-weight:700;color:#39756F">{label}</div>
<div style="font-size:17px;color:#54616E;margin-top:10px;line-height:1.4">{text}</div></div></div>"""
    body = f"""<div style="position:absolute;left:90px;top:80px;right:300px">
<div class="kicker">{_s(sl.get('kicker'), 40) or 'FAHRPLAN'}</div>
<div class="h2">{_s(sl.get('title'), 110)}</div></div>
<div style="position:absolute;left:90px;right:90px;top:360px;height:2px;background:#39756F"></div>
<div style="position:absolute;left:90px;right:90px;top:360px;height:400px">{punkte}</div>"""
    return seite(body, nr, gesamt)


def f_statement(sl, nr, gesamt):
    body = f"""<div style="position:absolute;left:110px;top:250px;width:1280px">
<div class="kicker">{_s(sl.get('kicker'), 40) or 'ENTSCHEDIUNG'}</div>
<div style="font-size:56px;line-height:1.25;font-weight:700;color:#243038">{_s(sl.get('title'), 160)}</div>
<div style="margin:40px 0 0"><div class="accent"></div></div>
<div class="sub" style="margin-top:40px;max-width:1000px">{_s(sl.get('botschaft'), 220)}</div>
</div>"""
    return seite(body, nr, gesamt)


LAYOUT = {"title": f_titel, "section": f_teil}


def folie_html(sl, nr, gesamt):
    """Slide-Dict -> handgebaute dataport-Folie (Agentur-Layout)."""
    kind = str(sl.get("kind") or "").lower()
    if kind in ("title", "titel"):
        return f_titel(sl, nr, gesamt)
    if kind in ("section", "teil"):
        return f_teil(sl, nr, gesamt)
    if sl.get("zeitstrahl"):
        return f_zeitstrahl(sl, nr, gesamt)
    if _zahlfelder(sl) and len(_zahlfelder(sl)) >= 2:
        return f_kpi(sl, nr, gesamt)
    if sl.get("botschaft") and not sl.get("bullets"):
        return f_statement(sl, nr, gesamt)
    return f_karten(sl, nr, gesamt)
