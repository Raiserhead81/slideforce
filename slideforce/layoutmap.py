"""SlideForce: Layout-Auswahl im Folienmaster."""
import re


def norm(s):
    """Namen normalisieren: lower, Umlaute aufpassen, nur Buchstaben/Zahlen."""
    s = s.lower().strip()
    s = s.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
    return re.sub(r"[^a-z0-9]", "", s)


class LayoutMap:
    """Index ueber alle Layouts eines Masters + typbasierte Auswahl."""

    def __init__(self, prs):
        self.prs = prs
        self.by_norm = {}
        for i, lay in enumerate(prs.slide_layouts):
            n = norm(lay.name)
            self.by_norm[n] = lay
            # Nummer-Praefix im Namen ('15 Titel und Inhalt') ebenfalls indexierbar
            m = re.match(r"^(\d{1,2})\s", lay.name.strip())
            if m:
                self.by_norm.setdefault("layout" + m.group(1), lay)
        # Platzhalternamen je Layout: norm(name) -> placeholder (erstes Vorkommen)
        self.ph_names = {}
        for lay in prs.slide_layouts:
            mapping = {}
            for ph in lay.placeholders:
                pf = ph.placeholder_format
                if pf.type in (1, 3, 4, 2, 7, 18, 6, 15) or pf.idx >= 10:
                    mapping.setdefault(norm(ph.name), ph)
            self.ph_names[lay.name] = mapping

    def by_number_or_name(self, spec):
        """'20', 'layout20', 'groesse zahl', '14 Tabelle' -> Layout oder None."""
        s = str(spec).strip()
        m = re.match(r"^(\d{1,2})$", s)
        if m:
            return self.by_norm.get("layout" + m.group(1))
        return self.by_norm.get(norm(s))

    def _first_with(self, name_contains, need_types):
        cands = [l for l in self.prs.slide_layouts
                 if name_contains in norm(l.name)]
        return cands[0] if cands else None

    def pick(self, kind):
        """Automatische Wahl: title/section/content/table/picture/closing/two/three."""
        if kind in ("title",):
            lay = self._first_with("titelfolie", None)
            if lay is None:
                lay = next((l for l in self.prs.slide_layouts
                            if any(ph.placeholder_format.type == 3
                                   for ph in l.placeholders)), None)
            return lay or self.prs.slide_layouts[0]
        if kind == "section":
            lay = self._first_with("kapiteltrenner", None)
            return lay or self.pick("content")
        if kind in ("statement", "botschaft"):
            lay = self._first_with("statement", None)
            return lay or self.pick("content")
        if kind in ("zahl", "kpi"):
            lay = self._first_with("grossezahl", None) or self._first_with("kennzahl", None)
            return lay or self.pick("content")
        if kind == "agenda":
            lay = self._first_with("agenda", None)
            return lay or self.pick("content")
        if kind in ("summary", "zusammenfassung"):
            lay = self._first_with("zusammenfassung", None) or self._first_with("summary", None)
            return lay or self.pick("content")
        if kind == "roadmap":
            lay = self._first_with("roadmap", None) or self._first_with("phasen", None) \
                or self._first_with("meilenstein", None)
            return lay or self.pick("content")
        if kind == "risiko":
            lay = self._first_with("risiko", None)
            return lay or self.pick("content")
        if kind == "vier":
            lay = self._first_with("vier", None)
            return lay or self.pick("three")
        if kind == "closing":
            lay = self._first_with("abschluss", None)
            return lay or self.pick("content")
        if kind == "table":
            lay = self._first_with("14tabelle", None) or self._first_with("tabelle", None)
            return lay or self.pick("content")
        if kind == "picture":
            lay = self._first_with("bildrandabfallendundtext", None)
            if lay is None:
                lay = next((l for l in self.prs.slide_layouts
                            if any(ph.placeholder_format.type == 18
                                   for ph in l.placeholders)), None)
            return lay or self.pick("content")
        if kind == "two":
            lay = self._first_with("zweispalten", None)
            return lay or self.pick("content")
        if kind == "three":
            lay = self._first_with("dreispalten", None)
            return lay or self.pick("content")
        # content: Layout mit Titel + Inhaltsplatzhalter, bevorzugt 'Titel und Inhalt'
        lay = self._first_with("titelundinhalt", None)
        if lay is None:
            lay = next((l for l in self.prs.slide_layouts
                        if any(ph.placeholder_format.idx == 0 for ph in l.placeholders)
                        and any(ph.placeholder_format.type == 2 and ph.placeholder_format.idx >= 10
                                for ph in l.placeholders)), None)
        if lay is None:
            lay = next((l for l in self.prs.slide_layouts
                        if any(ph.placeholder_format.idx == 0 for ph in l.placeholders)), None)
        return lay or self.prs.slide_layouts[0]
