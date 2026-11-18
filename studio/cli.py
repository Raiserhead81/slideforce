#!/usr/bin/env python3
"""GLM Presentation Studio - CLI (Etappe 1: Weg A, native PPTX).

Neu:
  python studio/cli.py "<briefing>" --quelle <datei> --min 8 --max 12 --weg A
Fortsetzen:
  python studio/cli.py --resume <run-id>

Ablauf: Director-Plan -> Story -> Art -> Build (SlideForce-Builder im venv)
-> Render (soffice/pdftoppm) -> Visual Critic je Folie -> max 3 Fix-Runden
-> report.md. State: studio/runs/<id>/state.json (nach jedem Schritt).
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:            # studio/ als Skript gestartet
    sys.path.insert(0, str(ROOT))

from studio.pipeline import run                   # noqa: E402
from studio.state import RunState                 # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="studio", description="GLM Presentation Studio (Etappe 1, Weg A)")
    ap.add_argument("briefing", nargs="?", help="Projekt-Briefing (z.B. Titel)")
    ap.add_argument("--quelle", help="Quelldatei (md/txt/docx/xlsx/csv)")
    ap.add_argument("--min", type=int, default=8, help="min. Folienzahl (default 8)")
    ap.add_argument("--max", type=int, default=12, help="max. Folienzahl (default 12)")
    ap.add_argument("--weg", default="A", choices=["A", "a"],
                    help="Produktionsweg (Etappe 1: nur A = native PPTX)")
    ap.add_argument("--resume", metavar="RUN-ID", help="abgebrochenen Run fortsetzen")
    ap.add_argument("--runs-dir", default=str(ROOT / "studio" / "runs"))
    ap.add_argument("--max-fixrunden", type=int, default=3)
    args = ap.parse_args(argv)

    if args.resume:
        state = RunState.open(args.runs_dir, args.resume)
        print(f"RESUME run {state.data['id']} (weg {state.data.get('weg')})")
    else:
        if not args.briefing:
            ap.error("briefing oder --resume noetig")
        if not args.quelle:
            ap.error("--quelle noetig (md/txt/docx/xlsx/csv)")
        q = Path(args.quelle)
        if not q.is_file():
            ap.error(f"Quelldatei fehlt: {q}")
        state = RunState.create(args.runs_dir, args.briefing, q.resolve(),
                                args.min, args.max, args.weg.upper(),
                                max_fixrunden=args.max_fixrunden)
        print(f"RUN {state.data['id']} · briefing: {args.briefing}")

    try:
        report = run(state, log=lambda m: print(m, flush=True))
    except KeyboardInterrupt:
        print("\nABBRUCH - fortsetzen mit: "
              f"python studio/cli.py --resume {state.data['id']}")
        return 130
    except Exception as e:
        print(f"FEHLER: {e}\nfortsetzen mit: "
              f"python studio/cli.py --resume {state.data['id']}")
        return 1
    final = (state.schritt("critic").get("runden") or [{}])[-1].get("scores") or []
    scores = ", ".join(f"{s['nr']}:{s['score']}" for s in final)
    print(f"\nFERTIG · PPTX: {state.schritt('build').get('pptx')}")
    print(f"Scores: {scores}")
    print(f"Report: {report}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
