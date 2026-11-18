"""SlideForce Web: pptx.gemivo.de/slideforce.gemivo.de - Master + Content -> Deck."""
import math
import re
import sys
import time
import uuid
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

from flask import Flask, request, send_file, jsonify, render_template, abort, session, redirect, Response  # noqa: E402
from pptx import Presentation  # noqa: E402
from slideforce.readers import read_content  # noqa: E402
from slideforce.builder import build  # noqa: E402
from slideforce.html_export import build_html  # noqa: E402
from slideforce.masterprofil import lade_profil, speichere_profil  # noqa: E402
from slideforce.profiles import build_profile, build_vorlage  # noqa: E402
from slideforce.ai_design import build_ai_deck, load_ai_config  # noqa: E402
from slideforce.layoutmap import LayoutMap  # noqa: E402
from slideforce.linter import pruefe_deck  # noqa: E402


UPLOAD = Path(__file__).resolve().parent / "uploads"
OUT = Path(__file__).resolve().parent / "output"
UPLOAD.mkdir(exist_ok=True)
OUT.mkdir(exist_ok=True)
DEFAULT_MASTER = UPLOAD / "default_master.pptx"
BASIC_MASTER = BASE / "examples" / "basic_master.pptx"
ALLOWED_CONTENT = {".md", ".markdown", ".txt", ".docx", ".xlsx", ".xlsm", ".csv"}


def _default_master():
    return DEFAULT_MASTER if DEFAULT_MASTER.is_file() else BASIC_MASTER

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 64 * 1024 * 1024

TOKEN_FILE = BASE / "token.txt"
TOKEN = TOKEN_FILE.read_text().strip() if TOKEN_FILE.is_file() else uuid.uuid4().hex
if not TOKEN_FILE.is_file():
    TOKEN_FILE.write_text(TOKEN)
    print(f"ZUGANGS-TOKEN (in {TOKEN_FILE}): {TOKEN}")
app.secret_key = "slideforce-" + TOKEN

LOGIN_HTML = """<!DOCTYPE html><html lang=de><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1"><title>SlideForce - Zugang</title>
<meta name=robots content="noindex,nofollow"><style>
body{background:#1a222a;color:#eef2f5;font-family:-apple-system,Arial,sans-serif;display:flex;min-height:100vh;align-items:center;justify-content:center;margin:0}
.c{background:#222c36;border:1px solid #313e4a;border-radius:14px;padding:34px;width:320px;text-align:center}
h1{font-size:1.4rem}h1 b{color:#9e292b}p{color:#9aa8b3;font-size:.9rem;margin:10px 0 18px}
input{width:100%;padding:12px;border-radius:9px;border:1px solid #46586a;background:#1b242d;color:#eef2f5;font-size:1rem;box-sizing:border-box}
button{width:100%;padding:12px;margin-top:12px;border:0;border-radius:9px;background:#9e292b;color:#fff;font-weight:700;font-size:1rem;cursor:pointer}
</style></head><body><div class=c><h1><b>Slide</b>Force</h1><p>Zugang nur mit Token.</p>
<form method=post action=/login><input name=token type=password placeholder=Token autofocus>
<button>oeffnen</button></form></div></body></html>"""


@app.before_request
def token_gate():
    if request.path == "/robots.txt":
        return app.response_class(
            "User-agent: *\nDisallow: /\n", mimetype="text/plain")
    if request.args.get("token") == TOKEN:
        session["ok"] = True
        if request.path == "/":
            return redirect("/", code=302)
        return None  # Datei-/API-Links mit ?token= direkt ausliefern
    if not session.get("ok"):
        return Response(LOGIN_HTML, status=401, mimetype="text/html",
                        headers={"X-Robots-Tag": "noindex, nofollow"})
    return None


@app.route("/files/<name>")
def files(name):
    from flask import send_from_directory
    return send_from_directory(OUT, Path(name).name)


@app.route("/login", methods=["POST"])
def login():
    if request.form.get("token", "").strip() == TOKEN:
        session["ok"] = True
        return redirect("/")
    return Response(LOGIN_HTML, status=401, mimetype="text/html")


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/layouts")
def layouts():
    mp = _default_master()
    try:
        profil = lade_profil(mp)
        return jsonify([{"i": l["i"], "name": l["name"], "role": l["role"]}
                        for l in profil["layouts"]])
    except Exception:
        prs = Presentation(str(mp))
        return jsonify([{"i": i, "name": lay.name} for i, lay in enumerate(prs.slide_layouts)])


SAVED = Path(__file__).resolve().parent / "uploads" / "saved"
SAVED.mkdir(parents=True, exist_ok=True)


def _saved_path(name):
    return SAVED / Path(name).name


@app.route("/api/save", methods=["POST"])
def save_text():
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    if not text:
        abort(400, "kein Text")
    label = text.splitlines()[0][:48].strip() or "Transkript"
    ts = time.strftime("%Y-%m-%d_%H%M")
    sid = f"{ts}_{uuid.uuid4().hex[:4]}"
    _saved_path(sid + ".md").write_text(text, encoding="utf-8")
    return jsonify({"id": sid, "label": label})


@app.route("/api/saved")
def saved_list():
    items = []
    for p in sorted(SAVED.glob("*.md"), reverse=True):
        first = p.read_text(encoding="utf-8", errors="replace").splitlines()
        label = (first[0][:48] if first and first[0].strip() else p.stem)
        items.append({"id": p.stem, "label": label})
    return jsonify(items[:50])


@app.route("/api/saved/<name>")
def saved_get(name):
    p = _saved_path(name + ".md")
    if not p.is_file():
        abort(404, "unbekannt")
    return p.read_text(encoding="utf-8")


def _save_upload(fileobj, prefix):
    suf = Path(fileobj.filename).suffix.lower()
    p = UPLOAD / f"{prefix}{uuid.uuid4().hex[:10]}{suf}"
    fileobj.save(p)
    return p


def _int_grenze(name):
    """Form-Feld minfolien/maxfolien -> int in 1..200 oder None (leer/ungueltig)."""
    raw = (request.form.get(name) or "").strip()
    if not raw:
        return None
    try:
        v = int(float(raw))
    except ValueError:
        return None
    return v if 1 <= v <= 200 else None


def _verteile_folien(slides, maxfolien):
    """Segmentbasierte Verteilung: jede section wird zu einer Folie und zieht
    die bullets der direkt folgenden titellosen content-Folien. Leere sections
    bleiben erhalten (bei Platznot benachbarte leere sections auf einer Folie,
    Titel 'A & B'). Danach ggf. komprimieren bzw. ueberladene Folien splitten.
    Nicht unterbringbare Inhalte werden nie still verworfen, sondern geloggt."""
    _STD = {"layout", "title", "bullets", "subtitle", "kind", "table", "image", "notes"}

    def _inhalt(s):
        """bullets + bisher ignorierte textuelle Zusatzfelder (z.B. passwort-richtlinie)."""
        bl = [[int(l), str(t)] for l, t in (s.get("bullets") or []) if str(t).strip()]
        for k, v in s.items():
            if k not in _STD and isinstance(v, str) and v.strip():
                bl.append([1, v.strip()])
        return bl

    rest = list(slides)
    titel = None
    if rest and rest[0].get("kind") == "title":
        titel, rest = rest[0], rest[1:]

    fest = [s for s in rest if s.get("table") or s.get("image")]
    rest = [s for s in rest if not (s.get("table") or s.get("image"))]

    # --- Segmente: section + direkt folgende titellose content-Folien ---
    segs = []          # [titel, bullets]
    offen_t, offen_b = "", []
    for s in rest:
        if s.get("kind") == "section":
            if offen_b or offen_t:
                segs.append([offen_t, offen_b])
            offen_t = (s.get("title") or "").strip() or offen_t
            offen_b = _inhalt(s)
        else:
            t_neu = (s.get("title") or "").strip()
            if offen_t and t_neu and t_neu != offen_t:
                # titeltragende content-Folie oeffnet eigenes Segment
                if offen_b or offen_t:
                    segs.append([offen_t, offen_b])
                offen_t, offen_b = t_neu, _inhalt(s)
            else:
                if not offen_t:
                    offen_t = t_neu
                offen_b.extend(_inhalt(s))
    if offen_b or offen_t:
        segs.append([offen_t, offen_b])

    # --- Leere Nachbar-Sections bei Platznot zusammenlegen ('A & B') ---
    platz = maxfolien - (1 if titel else 0) - len(fest)
    if platz <= 0:
        weg = sum(len(b) for _, b in segs)
        out = ([titel] if titel else []) + fest
        out = out[:maxfolien]
        print(f"[statik] Folien hart gekappt auf {len(out)} (max {maxfolien}), "
              f"{weg} Bullets weg", flush=True)
        return out

    while len(segs) > platz:
        leer = [i for i, (t, b) in enumerate(segs) if not b]
        if leer:
            i = leer[-1]
            # mit einem leeren Nachbar (bevorzugt vorheriger) mergen
            if i > 0:
                segs[i - 1][0] = (segs[i - 1][0] + " & " + segs[i][0])[:100].strip(" &")
            elif i < len(segs) - 1:
                segs[i + 1][0] = (segs[i][0] + " & " + segs[i + 1][0])[:100].strip(" &")
                segs[i + 1][1] = segs[i][1] + segs[i + 1][1]
            del segs[i]
            continue
        # keine leeren sections mehr: Bullets des kleinsten Segments in den Nachbarn
        if len(segs) < 2:
            break
        klein = min(range(len(segs)), key=lambda j: len(segs[j][1]))
        ziel = klein - 1 if klein > 0 else klein + 1
        segs[ziel][1].extend(segs[klein][1])
        del segs[klein]

    out = ([titel] if titel else []) + fest
    for t, bl in segs:
        out.append({"kind": "content", "layout": "content",
                    "title": (t or "").strip()[:100] or "Inhalt",
                    "bullets": [[int(l), str(x)] for l, x in bl]})

    # --- Splitting: unterdeckte Praesentation, ueberladene Folien splitten ---
    def _ueberladen(s):
        if s.get("kind") != "content" or s.get("table") or s.get("image"):
            return False
        bl = s.get("bullets") or []
        return len(bl) > 6 or sum(len(str(b[1])) for b in bl) > 350

    def _marker(b):
        txt = str(b[1]).strip()
        return bool(txt) and txt.isupper() and len(txt) < 60

    gesplittet = 0
    while len(out) < maxfolien:
        kandidaten = [s for s in out if _ueberladen(s)]
        if not kandidaten:
            break
        folie = max(kandidaten,
                    key=lambda s: (len(s.get("bullets") or []),
                                   sum(len(str(b[1])) for b in s.get("bullets") or [])))
        bl = folie["bullets"]
        titel_ = (folie.get("title") or "").strip()
        half = max(1, len(bl) // 2)
        marker_idx = next((i for i in range(half, len(bl)) if _marker(bl[i])), None)
        if marker_idx is not None:
            split_idx = marker_idx
            neuer_titel = str(bl[marker_idx][1]).strip()[:100]
        else:
            split_idx = half
            neuer_titel = (titel_[:100] or "Inhalt") + " (Fortsetzung)"
        neue = {"kind": "content", "layout": "content",
                "title": neuer_titel, "bullets": bl[split_idx:]}
        folie["bullets"] = bl[:split_idx]
        out.insert(out.index(folie) + 1, neue)
        gesplittet += 1
    if gesplittet:
        print(f"[statik] Folien aufgeteilt: {gesplittet} ueberladene Folie(n) gesplittet "
              f"(max {maxfolien})", flush=True)

    print(f"[statik] Folien verteilt: {len(slides)} -> {len(out)} (max {maxfolien})",
          flush=True)
    return out


@app.route("/api/build", methods=["POST"])
def build_deck():
    fmt = request.form.get("fmt", "pptx").lower()
    minfolien = _int_grenze("minfolien")
    maxfolien = _int_grenze("maxfolien")
    if minfolien and maxfolien and minfolien > maxfolien:
        abort(400, "min. Folien darf nicht groesser als max. Folien sein")
    master = request.files.get("master")
    content = request.files.get("content")
    text = request.form.get("text", "").strip()
    tmp = []
    try:
        if master and master.filename:
            mp = _save_upload(master, "m")
            if mp.suffix.lower() != ".pptx":
                abort(400, "Master muss eine .pptx-Datei sein")
            tmp.append(mp)
            try:
                speichere_profil(mp)          # Template-Profil cachen
            except Exception:
                pass
        else:
            mp = _default_master()
        if content and content.filename:
            cp = _save_upload(content, "c")
            if cp.suffix.lower() not in ALLOWED_CONTENT:
                abort(400, "Content-Format nicht unterstuetzt (md/txt/docx/xlsx/csv)")
            tmp.append(cp)
        elif text:
            cp = UPLOAD / f"t{uuid.uuid4().hex[:10]}.md"
            cp.write_text(text, encoding="utf-8")
            tmp.append(cp)
        else:
            abort(400, "Kein Inhalt uebergeben (Datei oder Text)")
        slides = read_content(cp, source_title=cp.stem)
        if cp.suffix.lower() in (".md", ".markdown", ".txt"):
            content_text = cp.read_text(encoding="utf-8", errors="replace")
        else:                                     # docx/xlsx/csv: Folien als Text
            from slideforce.ai_design import _slides_as_text
            content_text = _slides_as_text(slides)
        warnung = None
        n_final = len(slides)
        uid = uuid.uuid4().hex[:10]
        if fmt == "html":
            if maxfolien:
                slides = _verteile_folien(slides, maxfolien)
                n_final = len(slides)
            out = OUT / f"deck-{uid}.html"
            build_html(slides, slides[0].get("title", "Deck"), out, mp)
        else:
            out = OUT / f"deck-{uid}.pptx"
            if fmt in ("b28pptx", "vorpptx"):
                if maxfolien:
                    slides = _verteile_folien(slides, maxfolien)
                    n_final = len(slides)
                if minfolien and len(slides) < minfolien:
                    warnung = (f"min {minfolien} Folien nicht erreichbar ohne KI "
                               f"(nur {len(slides)} statisch - Premium nutzen)")
                if fmt == "b28pptx":
                    build_profile(slides, out)
                else:
                    build_vorlage(slides, out)
            elif fmt == "aipptx":
                # Premium: GLM 5.3 designt JEDE Folie einzeln (1 Call pro Folie,
                # max 4 parallel). KI gar nicht erreichbar -> alle Folien im
                # statischen b28-Fallback (== b28pptx), Hinweis via Header.
                def _prog(fertig, gesamt):
                    print(f"[ai] Folie {fertig}/{gesamt} designt", flush=True)

                _, ai_stats = build_ai_deck(slides, out, config=load_ai_config(),
                                             on_progress=_prog,
                                             ziel_min=minfolien, ziel_max=maxfolien,
                                             content_text=content_text,
                                             master_path=str(mp))
                n_final = ai_stats.get("folien", len(slides))
            else:
                build(mp, slides, out)
        mime = "text/html" if fmt == "html" else "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        ext = "pptx" if fmt != "html" else "html"
        resp = send_file(out, as_attachment=True, download_name=f"slideforce-deck-{uid}.{ext}", mimetype=mime)
        linter_report = pruefe_deck(slides)
        print('[linter] Score %s/100 blockierend=%s' % (linter_report['score'], linter_report['blockierend']))
        resp.headers["X-Deck-Folien"] = str(n_final)
        resp.headers["X-Deck-Score"] = str(linter_report["score"])
        resp.headers["X-Deck-Blockierend"] = "1" if linter_report["blockierend"] else "0"
        if warnung:
            resp.headers["X-Warnung"] = warnung
        if fmt == "aipptx":
            resp.headers["X-AI-Folien"] = str(ai_stats.get("ki", 0))
            if ai_stats.get("ki", 0) == 0:
                resp.headers["X-AI-Fallback"] = "1"
        return resp
    finally:
        for p in tmp:
            p.unlink(missing_ok=True)


# ---------------------------------------------------------------- Studio (Etappe 2)
import json as _json  # noqa: E402
import threading  # noqa: E402

STUDIO_RUNS = BASE / "studio" / "runs"
STUDIO_THREADS = {}


def _studio_laeufer(run_id):
    from studio.pipeline import run as _run
    from studio.state import RunState as _RS
    try:
        st = _RS.open(str(STUDIO_RUNS), run_id)
        _run(st, log=lambda m: None)
    except Exception as e:
        try:
            st = _RS.open(str(STUDIO_RUNS), run_id)
            st.set_schritt("report", "error", {"fehler": str(e)})
        except Exception:
            pass
    finally:
        STUDIO_THREADS.pop(run_id, None)


def _studio_status(run_id):
    p = STUDIO_RUNS / run_id / "state.json"
    if not p.is_file():
        return None
    try:
        d = _json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None
    schritte = {k: v.get("status") for k, v in (d.get("schritte") or {}).items()}
    runden = ((d.get("schritte") or {}).get("critic") or {}).get("runden") or []
    scores = (runden[-1].get("scores") or []) if runden else []
    o = STUDIO_RUNS / run_id
    return {"id": run_id, "weg": d.get("weg"), "briefing": d.get("briefing"),
            "schritte": schritte, "scores": scores,
            "laeuft": run_id in STUDIO_THREADS,
            "pptx": (o / "deck.pptx").is_file(),
            "deck_html": (o / "deck.html").is_file(),
            "report": (o / "report.md").is_file()}


def _briefing_aus_quelle(p):
    """Briefing-Default wenn leer: erste aussagekraeftige Zeile (max 80),
    sonst Dateiname. Office-Dateien (docx/xlsx = ZIP-Binaer): IMMER Dateiname."""
    p = Path(p)
    if p.suffix.lower() in (".docx", ".xlsx", ".xlsm", ".pptx"):
        return (p.stem.replace("_", " ")[:80] or "Studio Run").strip()
    try:
        for zeile in p.read_text(encoding="utf-8",
                                 errors="replace").splitlines()[:20]:
            zeile = zeile.lstrip("# -* ").strip()
            if len(zeile) >= 8 and not any(
                    ord(c) < 9 or ord(c) == 127 for c in zeile[:40]):
                return zeile[:80]
    except Exception:
        pass
    return (p.stem.replace("_", " ")[:80] or "Studio Run").strip()


@app.route("/api/studio/start", methods=["POST"])
def studio_start():
    briefing = (request.form.get("briefing") or "").strip()
    quelle = request.files.get("quelle")
    text = (request.form.get("text") or "").strip()
    if not quelle and not text:
        return jsonify({"error": "Quelldatei oder Text noetig"}), 400
    weg = (request.form.get("weg") or "A").upper()
    if weg not in ("A", "B", "C"):
        weg = "A"
    stamp = uuid.uuid4().hex[:8]
    if quelle:
        qpath = UPLOAD / f"studio_{stamp}_{Path(quelle.filename).name}"
        quelle.save(str(qpath))
    else:
        qpath = UPLOAD / f"studio_{stamp}.md"
        qpath.write_text(text, encoding="utf-8")
    if not briefing:
        briefing = _briefing_aus_quelle(qpath)
    try:
        lo = int(request.form.get("min") or 8)
        hi = int(request.form.get("max") or 12)
    except ValueError:
        lo, hi = 8, 12
    from studio.state import RunState
    st = RunState.create(str(STUDIO_RUNS), briefing, str(qpath), lo, hi, weg)
    th = threading.Thread(target=_studio_laeufer, args=(st.data["id"],), daemon=True)
    STUDIO_THREADS[st.data["id"]] = th
    th.start()
    return jsonify({"id": st.data["id"]})


@app.route("/api/studio/status/<run_id>")
def studio_status(run_id):
    s = _studio_status(run_id)
    return (jsonify(s), 200) if s else (jsonify({"error": "unbekannt"}), 404)


@app.route("/api/studio/resume/<run_id>", methods=["POST"])
def studio_resume(run_id):
    if _studio_status(run_id) is None:
        return jsonify({"error": "unbekannt"}), 404
    if run_id in STUDIO_THREADS:
        return jsonify({"error": "laeuft schon"}), 409
    th = threading.Thread(target=_studio_laeufer, args=(run_id,), daemon=True)
    STUDIO_THREADS[run_id] = th
    th.start()
    return jsonify({"ok": True})


@app.route("/api/studio/run/<run_id>", methods=["DELETE"])
def studio_run_delete(run_id):
    """Studio-Run loeschen (Ordner unter studio/runs). Laufende Runs: 409."""
    if not re.fullmatch(r"[A-Za-z0-9_\-]+", run_id):
        abort(400, "ungueltige Run-ID")
    p = STUDIO_RUNS / run_id
    # Wasserdichter Traversal-Schutz: aufgeloester Pfad MUSS direkt in STUDIO_RUNS liegen
    if p.resolve().parent != STUDIO_RUNS.resolve() or p.resolve() == STUDIO_RUNS.resolve():
        abort(400, "ungueltige Run-ID")
    if not p.is_dir():
        return jsonify({"error": "unbekannt"}), 404
    if run_id in STUDIO_THREADS:
        return jsonify({"error": "laeuft schon - erst abwarten"}), 409
    import shutil
    shutil.rmtree(p)
    return jsonify({"ok": True})


@app.route("/api/studio/runs")
def studio_runs():
    if not STUDIO_RUNS.is_dir():
        return jsonify([])
    ids = sorted([p.name for p in STUDIO_RUNS.iterdir() if p.is_dir()],
                 reverse=True)[:12]
    out = [s for s in (_studio_status(i) for i in ids) if s]
    return jsonify(out)


@app.route("/api/studio/file/<run_id>/<name>")
def studio_file(run_id, name):
    if name not in ("deck.pptx", "deck.html", "report.md"):
        abort(404)
    p = STUDIO_RUNS / run_id / name
    if not p.is_file():
        abort(404)
    return send_file(str(p), as_attachment=(name != "deck.html"))

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8821, debug=False)
