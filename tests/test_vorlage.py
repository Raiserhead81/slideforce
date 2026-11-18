"""Vorlage-Profil-Smoke: python3 tests/test_vorlage.py (venv aktiviert)."""
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

from slideforce.readers import read_content                    # noqa: E402
from slideforce.profiles import build_vorlage                  # noqa: E402


def main():
    slides = read_content(BASE / "examples" / "vorlage-demo.md")
    kinds = [s.get("kind") for s in slides]
    assert kinds.count("section") == 2, f"Sections: {kinds}"
    out = BASE / "output" / "test-vorlage.pptx"
    warn = build_vorlage(slides, out)
    assert not warn, f"Warnungen: {warn}"
    from pptx import Presentation
    prs = Presentation(str(out))
    assert len(prs.slides) == len(slides), "Folienzahl falsch"

    def texts(i):
        return [r.text for sh in prs.slides[i].shapes if sh.has_text_frame
                for p in sh.text_frame.paragraphs for r in p.runs]

    # Titel- und Teil-Folie: Sidebar 'INHALT' + Teile-Nummern rot
    assert "INHALT" in texts(0), "Sidebar INHALT fehlt auf Titelfolie"
    assert "02" in texts(0) and "08" in texts(0), "Teile-Nummern fehlen"
    assert "Folien 3" in " ".join(texts(1)), f"Teil-Meta fehlt: {texts(1)[:8]}"
    # Content-Folie 3: KPI-Karte (479 / 515) + nummerierte Karten
    t3 = " ".join(texts(2))
    assert "479 / 515" in t3 and "93 %" in t3, "KPI-Karte fehlt"
    # KPI-Grid (zahl2) auf Folie 4, Tabelle auf 5, Zeitstrahl auf 6, Statement auf 7
    assert "2,49 Mio €" in " ".join(texts(3)), "KPI-Grid fehlt"
    assert any(sh.has_table for sh in prs.slides[4].shapes), "Tabelle fehlt"
    assert "TAGE" in " ".join(texts(5)), "Zeitstrahl fehlt"
    assert "Kein Standort" in " ".join(texts(6)), "Statement fehlt"
    # Footer + Karten-Farbe F4F5F6 pruefen
    fills = []
    for sh in prs.slides[2].shapes:
        try:
            if sh.fill.type is not None and "SOLID" in str(sh.fill.type):
                fills.append(str(sh.fill.fore_color.rgb))
        except Exception:
            pass
    assert "F4F5F6" in fills, f"Karten-Farbe fehlt: {set(fills)}"
    print(f"VORLAGE OK: {len(prs.slides)} Folien, Sidebar/KPI/Tabelle/Zeitstrahl/Statement geprueft")


if __name__ == "__main__":
    main()
