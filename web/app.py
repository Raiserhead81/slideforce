"""SlideForce Web: pptx.gemivo.de/slideforce.gemivo.de - Master + Content -> Deck."""
import sys
import uuid
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

from flask import Flask, request, send_file, jsonify, render_template, abort  # noqa: E402
from pptx import Presentation  # noqa: E402
from slideforce.readers import read_content  # noqa: E402
from slideforce.builder import build  # noqa: E402
from slideforce.html_export import build_html  # noqa: E402
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


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/layouts")
def layouts():
    prs = Presentation(str(_default_master()))
    return jsonify([{"i": i, "name": lay.name} for i, lay in enumerate(prs.slide_layouts)])


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
            build(mp, slides, out)
        mime = "text/html" if fmt == "html" else "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        resp = send_file(out, as_attachment=True, download_name=f"slideforce-deck-{uid}.{fmt}", mimetype=mime)
        resp.headers["X-Deck-Folien"] = str(len(slides))
        return resp
    finally:
        for p in tmp:
            p.unlink(missing_ok=True)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8821, debug=False)
