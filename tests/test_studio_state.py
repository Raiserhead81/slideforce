"""Studio-Etappe-1-Tests (pytest): State-Persistenz + gemockte Rolle.

Keine Netzwerk-Calls: studio.glm wird fuer den Rollen-Test gepatcht.
Laufen mit:  .venv/bin/pytest tests/test_studio_state.py -q
"""
import json
import sys
from pathlib import Path
from unittest.mock import patch

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

from studio import pipeline                                   # noqa: E402
from studio.state import RunState                             # noqa: E402


def _tmp_run(tmp_path, quelle_text="# Q\n\n- Punkt eins\n- Punkt zwei\n",
             ziel_min=8, ziel_max=12):
    quelle = tmp_path / "quelle.md"
    quelle.write_text(quelle_text, encoding="utf-8")
    return RunState.create(tmp_path / "runs", "Test-Briefing", quelle,
                           ziel_min, ziel_max, "A")


def test_state_create_save_load_roundtrip(tmp_path):
    st = _tmp_run(tmp_path)
    assert st.fertig("story") is False
    st.set_schritt("director", "ok", {"plan": {"folienzahl": 10}}, dauer_s=1.2)
    # Neu oeffnen (Simuliert: Prozess-Restart / --resume)
    st2 = RunState.open(tmp_path / "runs", st.data["id"])
    assert st2.data["id"] == st.data["id"]
    assert st2.data["briefing"] == "Test-Briefing"
    assert st2.data["min"] == 8 and st2.data["max"] == 12 and st2.data["weg"] == "A"
    assert st2.fertig("director") is True
    assert st2.schritt("director")["plan"]["folienzahl"] == 10
    assert st2.schritt("director")["dauer_s"] == 1.2


def test_state_resume_ueberspringt_fertige_schritte(tmp_path):
    st = _tmp_run(tmp_path)
    for name in ("director", "story"):
        st.set_schritt(name, "ok", {"x": name})
    st2 = RunState.open(tmp_path / "runs", st.data["id"])
    assert st2.fertig("director") and st2.fertig("story")
    assert not st2.fertig("art")
    # error-Schritt gilt als NICHT fertig (wird wiederholt)
    st2.set_schritt("art", "error", {"fehler": "boom"})
    assert not st2.fertig("art")
    assert json.loads(st2.path.read_text(encoding="utf-8"))["schritte"]["art"]["status"] == "error"


_STORYBOARD = {
    "deck_titel": "ITK-Bremen Vorstand 2026: Landesnetz",
    "untertitel": "Bericht an den Vorstand",
    "meta": "Stand 20.01.2026 · Vorstand",
    "annahmen": ["Einsparung 2027 ist Hochrechnung"],
    "folien": [
        {"nr": 1, "rolle": "titel", "titel": "ITK-Bremen Vorstand 2026: Landesnetz",
         "untertitel": "Bericht", "meta": "Stand · Vorstand"},
        {"nr": 2, "rolle": "teil", "titel": "Migration"},
        {"nr": 3, "rolle": "kpi", "titel": "Migration erreicht 93 Prozent",
         "kicker": "MIGRATION", "lead": "Landesnetz", "zahl": "479 / 515",
         "label": "Standorte angemeldet", "subs": [["93 %", "abgeschlossen"]],
         "punkte": ["M2: Kernnetz umgestellt"], "annahmen": ["x ist geschaetzt"]},
        {"nr": 4, "rolle": "content", "titel": "Betrieb stabil",
         "punkte": ["SLA: 14 P1-Stoerungen behoben"]},
    ],
}


def test_story_schritt_mit_gemockter_glm_rolle(tmp_path):
    """Story-Architect als GLM-Rolle gemockt: kein Netz, Ergebnis im State."""
    st = _tmp_run(tmp_path, ziel_min=4, ziel_max=6)
    st.set_schritt("director", "ok", {"plan": {"folienzahl": 4,
                                               "teile": ["A", "B"]}})
    with patch("studio.glm.chat_json", return_value=_STORYBOARD) as mock:
        pipeline.schritt_story(st, log=None)
        assert mock.called
    assert st.fertig("story")
    sb = st.schritt("story")["storyboard"]
    assert len(sb["folien"]) == 4
    assert [f["nr"] for f in sb["folien"]] == [1, 2, 3, 4]  # nr deterministisch
    assert sb["folien"][2]["titel"].startswith("Migration erreicht")


def test_story_validierung_grenzen(tmp_path):
    """Storyboard ausserhalb min/max -> Retry + error-Schritt im State."""
    from studio import roles
    st = _tmp_run(tmp_path)                      # min=8, Storyboard hat 4 Folien
    st.set_schritt("director", "ok", {"plan": {"folienzahl": 10}})
    with patch("studio.glm.chat_json", return_value=_STORYBOARD) as mock:
        raised = False
        try:
            pipeline.schritt_story(st, log=None)
        except RuntimeError:
            raised = True
        assert raised
        assert mock.call_count == 2              # 1 Feedback-Retry
    assert st.schritt("story").get("status") == "error"
    fehler = roles.validiere_storyboard(_STORYBOARD, 8, 12)
    assert any("ausserhalb" in f for f in fehler)


def test_operator_fallback_bei_kaputtem_design(tmp_path):
    """Art-Design unbrauchbar -> deterministischer Storyboard-Fallback."""
    from studio import webop as OP
    slides, warn = OP.slides_aus_design({"folien": [{"quatsch": 1}]}, _STORYBOARD)
    assert len(slides) == 4
    assert slides[0]["kind"] == "title"
    assert slides[2].get("zahl") == "479 / 515"
    assert any("Fallback" in w for w in warn)
