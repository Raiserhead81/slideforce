# SlideForce

**Master + Inhalt = fertiges Deck.** SlideForce baut perfekte PowerPoint-Dateien direkt aus deinem
Folienmaster (.pptx) - Farben, Fonts, Layouts und Platzhalter bleiben 1:1 erhalten. Zusätzlich
exportiert es moderne **HTML-Präsentationen** (self-contained, Pfeiltasten-Navigation) im selben Design.

- **Web-App:** Master hochladen (oder BRIDGE28-Standard), Inhalt als Transcript / Word / Text / Excel
  / Markdown rein, Deck als `.pptx` oder `.html` runterladen.
- **Engine:** python-pptx, python-docx, openpyxl - alles lokal, keine Cloud, keine Daten leaves.

## Inhalt-Formate

| Format | Erkannt | Verhalten |
|---|---|---|
| `.md` / `.txt` / Transcript | `#` Titelfolie, `##` Folientitel, `- ` Bullets (2 Leerzeichen = Unterpunkt), `\| a \| b \|` Tabelle, `![](bild.png)` Bild, `key: wert` Master-Platzhalter | Lange Absätze werden automatisch an Satzenden in Bullets gesplittet, >7 Bullets pro Folie wird gesplittet |
| `.docx` | Word-Headings werden Folien, Listen werden Bullets, Tabellen werden Folientabellen | |
| `.xlsx` / `.csv` | Jedes Sheet/CSV = Tabellenfolie (max 16x10) | |

### Content-Beispiel (demo.md)

```markdown
# Projekt Phoenix          <- Titelfolie (Layout "01 Titelfolie")
Projekt Phoenix            <- 1. Absatz unter # = Untertitel

## Kapitel 1               <- Abschnittsfolie (Kapiteltrenner)

### Agenda                 <- Content-Folie (Standard: "Titel und Inhalt")
- Punkt eins
  - Unterpunkt             <- eingerueckt = Ebene 2
- **fett**, *kursiv*, `code`

layout: 14 Tabelle         <- explizites Layout (Nummer oder Name aus dem Master)
title: Projektstatus
| Bereich | Status |
| Build   | Gelb   |

layout: 12 Große Zahl      <- alle Platzhalter-Namen des Layouts sind Keys
title: Umsatz Q4
zahl: 4,2 Mio
einheit: EUR
erklaerung: plus 12% ggü. Vorjahr

notes: Sprechernotiz       <- landet in den Notizen der Folie
```

## Engine (Python)

```python
from slideforce.readers import read_content
from slideforce.builder import build
from slideforce.html_export import build_html

slides = read_content("inhalt.md")            # oder .docx / .xlsx / .csv
build("master.pptx", slides, "deck.pptx")     # -> Warnungsliste
build_html(slides, "Decktitel", "deck.html", "master.pptx")
```

Layout-Wahl: automatisch passend zum Folientyp (Titel/Kapitel/Content/Tabelle/Bild) oder
explizit per `layout: <Nummer|Name>` - Namen und Nummern kommen aus dem Master.
Jeder Platzhalter-Name eines Master-Layouts ist im Content direkt als Key nutzbar
(Gross-/Kleinschreibung egal, Teilstring reicht: `zahl:` trifft "Große Zahl").

## Web-App

```bash
pip install -r requirements.txt
cd web && python app.py        # http://127.0.0.1:8821
```

- `web/uploads/default_master.pptx` ist der Standard-Master (aktuell: BRIDGE28).
- `POST /api/build` (multipart): `master` (.pptx, optional), `content` (Datei) oder `text`,
  `fmt=pptx|html` - Antwort ist der fertige Download, Header `X-Deck-Folien` = Folienzahl.
- `GET /api/layouts` - Layoutliste des Standard-Masters.

## Live

- https://slideforce.gemivo.de (gemivo-Server, systemd + nginx + certbot)

Lizenz: MIT
