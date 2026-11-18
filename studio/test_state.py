"""Studio-Tests: RunState-Persistenz + 429-Haertung (keine echten GLM-Calls)."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from studio.state import RunState                       # noqa: E402


def test_create_save_open_rundlauf(tmp_path):
    s = RunState.create(str(tmp_path), "Test Vorstand", "q.md", 8, 12, "A")
    assert s.data["min"] == 8 and s.data["weg"] == "A"
    s.set_schritt("director", "ok", {"plan": {"folienzahl": 9}}, dauer_s=1.23)
    assert s.fertig("director") and not s.fertig("story")
    s2 = RunState.open(str(tmp_path), s.data["id"])
    assert s2.schritt("director").get("plan", {}).get("folienzahl") == 9
    assert s2.schritt("director").get("dauer_s") == 1.2
    assert s2.artefakt("deck.pptx").parent == s2.dir
    assert (tmp_path / s.data["id"] / "state.json").is_file()


def test_open_fehlt(tmp_path):
    with pytest.raises(FileNotFoundError):
        RunState.open(str(tmp_path), "gibt-es-nicht")


def test_fehler_schritt():
    s = RunState.create("/tmp/studio-test-runs", "X", "q", 1, 2, "A")
    s.set_schritt("story", "error", {"fehler": "kein JSON"})
    assert not s.fertig("story")
    assert s.schritt("story").get("fehler") == "kein JSON"


def test_glm_429_wirft_runtimeerror(monkeypatch):
    """Nach 3x 429 muss _post RuntimeError werfen, nicht None liefern."""
    import urllib.error
    from studio import glm

    def fa(_args, _t):
        raise urllib.error.HTTPError(
            "https://bridge.example/zai", 429, "rate limited", {}, None)

    monkeypatch.setattr(glm, "_RETRIES", 2)
    aufrufe = []

    def zae(_req, timeout):
        aufrufe.append(1)
        fa(None, None)

    monkeypatch.setattr(glm.urllib.request, "urlopen", zae)
    with pytest.raises(RuntimeError, match="429"):
        glm._post([{"role": "user", "content": "x"}], 100)
    assert len(aufrufe) == 2


def test_svg_dupe_attrs_raus():
    from studio.render import _svg_dupe_attrs_raus
    kaputt = ("<svg xmlns='x' width='10' width='20'>"
              "<line x1='1' y1='2' x2='3' x1='9'/></svg>")
    fix = _svg_dupe_attrs_raus(kaputt)
    assert fix.count("x1=") == 1 and fix.count("width=") == 1
    assert fix.startswith("<svg") and fix.endswith("</svg>")


def test_svg_zu_png_repariert_kaputtes():
    from studio.render import svg_zu_png
    kaputt = ("<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'"
              " width='10' width='20'><rect width='100' height='100'"
              " fill='#39756F' fill='#fff'/></svg>")
    p = svg_zu_png(kaputt, "/tmp/test-svg-repariert.png")
    assert p and Path(p).stat().st_size > 500


def test_hybrid_svg_regex_fallback(monkeypatch):
    """chat_json-Pfad kaputt -> Regex-Fallback zieht <svg> aus rohem Text."""
    from studio import glm, roles

    roh = "Hier ist deine Grafik:\n<svg xmlns='http://www.w3.org/2000/svg'>\
<rect x='1' y='2' width='3' height='4'/></svg> fertig."
    monkeypatch.setattr(glm, "chat", lambda *a, **k: roh)
    svg = roles.hybrid_svg("Test-Briefing", {"title": "Folie"}, {}, 4)
    assert svg and svg.startswith("<svg") and svg.endswith("</svg>")
