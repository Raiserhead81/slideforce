"""SlideForce Smoke-Test: python3 tests/test_smoke.py (venv aktiviert)."""
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

from slideforce.readers import read_content  # noqa: E402
from slideforce.builder import build  # noqa: E402
from slideforce.html_export import build_html  # noqa: E402

MASTER = BASE / "web" / "uploads" / "default_master.pptx"


def main():
    slides = read_content(BASE / "examples" / "demo.md")
    assert len(slides) >= 7, f"zu wenige Folien: {len(slides)}"
    assert slides[0]["kind"] == "title", "erste Folie ist keine Titelfolie"
    warn = build(MASTER, slides, BASE / "output" / "test.pptx")
    assert not warn, f"Builder-Warnungen: {warn}"
    from pptx import Presentation
    prs = Presentation(str(BASE / "output" / "test.pptx"))
    assert len(prs.slides) == len(slides), "Folienzahl im Output falsch"
    n = build_html(slides, "Test", BASE / "output" / "test.html", MASTER)
    assert n == len(slides), "HTML-Folienzahl falsch"
    assert (BASE / "output" / "test.html").stat().st_size > 1000, "HTML zu klein"
    print(f"SMOKE OK: {len(slides)} Folien, PPTX + HTML gebaut")


if __name__ == "__main__":
    main()
