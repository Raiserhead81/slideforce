"""SlideForce Web: pptx.gemivo.de/slideforce.gemivo.de - Master + Content -> Deck."""
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
from slideforce.profiles import build_profile  # noqa: E402
from slideforce.ai_design import build_ai_deck, load_ai_config  # noqa: E402
from slideforce.layoutmap import LayoutMap  # noqa: E402

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
    prs = Presentation(str(_default_master()))
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


@app.route("/api/build", methods=["POST"])
def build_deck():
    fmt = request.form.get("fmt", "pptx").lower()
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
        uid = uuid.uuid4().hex[:10]
        if fmt == "html":
            out = OUT / f"deck-{uid}.html"
            build_html(slides, slides[0].get("title", "Deck"), out, mp)
        else:
            out = OUT / f"deck-{uid}.pptx"
            if fmt == "b28pptx":
                build_profile(slides, out)
            elif fmt == "aipptx":
                # Premium: GLM 5.3 designt JEDE Folie einzeln (1 Call pro Folie,
                # max 4 parallel). KI gar nicht erreichbar -> alle Folien im
                # statischen b28-Fallback (== b28pptx), Hinweis via Header.
                def _prog(fertig, gesamt):
                    print(f"[ai] Folie {fertig}/{gesamt} designt", flush=True)

                _, ai_stats = build_ai_deck(slides, out, config=load_ai_config(),
                                             on_progress=_prog)
            else:
                build(mp, slides, out)
        mime = "text/html" if fmt == "html" else "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        ext = "pptx" if fmt != "html" else "html"
        resp = send_file(out, as_attachment=True, download_name=f"slideforce-deck-{uid}.{ext}", mimetype=mime)
        resp.headers["X-Deck-Folien"] = str(len(slides))
        if fmt == "aipptx":
            resp.headers["X-AI-Folien"] = str(ai_stats.get("ki", 0))
            if ai_stats.get("ki", 0) == 0:
                resp.headers["X-AI-Fallback"] = "1"
        return resp
    finally:
        for p in tmp:
            p.unlink(missing_ok=True)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8821, debug=False)
