"""Studio RunState: Persistenz in runs/<id>/state.json, fortsetzbar."""
import json
import re
import time
import unicodedata
from pathlib import Path

BASE = Path(__file__).resolve().parent


def _slug(t, n=40):
    t = unicodedata.normalize("NFKD", str(t)).encode("ascii", "ignore").decode()
    t = re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")
    return t[:n].strip("-") or "run"


class RunState:
    def __init__(self, runs_dir, d):
        self.runs = Path(runs_dir)
        self.data = d
        self.dir = self.runs / d["id"]
        self.dir.mkdir(parents=True, exist_ok=True)

    @classmethod
    def create(cls, runs_dir, briefing, quelle, minf, maxf, weg,
               max_fixrunden=3):
        rid = f"{time.strftime('%Y%m%d-%H%M%S')}-{_slug(briefing)}"
        d = {"id": rid,
             "erstellt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
             "briefing": briefing, "quelle": str(quelle), "min": minf,
             "max": maxf, "weg": weg, "max_fixrunden": max_fixrunden,
             "schritte": {}, "letzte_aktivitaet": None}
        st = cls(runs_dir, d)
        st.save()
        return st

    @classmethod
    def open(cls, runs_dir, run_id):
        p = Path(runs_dir) / run_id / "state.json"
        if not p.exists():
            raise FileNotFoundError(f"kein state.json: {p}")
        return cls(runs_dir, json.loads(p.read_text(encoding="utf-8")))

    @property
    def ordner(self):
        return self.dir

    @property
    def path(self):
        return self.dir / "state.json"

    def save(self):
        self.data["letzte_aktivitaet"] = time.strftime(
            "%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        self.dir.mkdir(parents=True, exist_ok=True)
        (self.dir / "state.json").write_text(
            json.dumps(self.data, ensure_ascii=False, indent=1),
            encoding="utf-8")

    def schritt(self, name):
        return self.data.get("schritte", {}).get(name) or {}

    def set_schritt(self, name, status, payload=None, dauer_s=None):
        e = {"status": status,
             "zeit": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        if dauer_s is not None:
            e["dauer_s"] = round(dauer_s, 1)
        if payload:
            e.update(payload)
        self.data.setdefault("schritte", {})[name] = e
        self.save()

    def fertig(self, name):
        return self.schritt(name).get("status") == "ok"

    def artefakt(self, name):
        return self.dir / name
