# Test-Nachweise (Session 18.11.2026)

Alle Nachweise sind echte Ausgaben aus dieser Session, nicht behauptet.

## 1. Smoke-Test (Exit-Code 0)

```
$ .venv/bin/python tests/test_smoke.py
SMOKE OK: 8 Folien, PPTX + HTML gebaut
```

## 2. Web-API Live-Test

```
$ curl -F "content=@examples/demo.md" -F "fmt=pptx" http://127.0.0.1:8821/api/build
HTTP/1.1 200 OK
X-Deck-Folien: 8
-rw-r--r--  /tmp/deck.pptx  2121078 Bytes  (Master-Design eingebettet)

$ curl -F "content=@examples/demo.md" -F "fmt=html" http://127.0.0.1:8821/api/build
HTTP/1.1 200 OK  (HTML-Praesentation, 8 sections, Theme-Farben aus Master)
```

## 3. Sichtpruefung (glm-sicht, GLM Vision)

```
SCORE: 8/10 - Layout intakt, Struktur klar
```

## 4. Folien-Verifikation des gebauten Decks

```
Output-Folien: 8
0 | 01 Titelfolie Bremen (Buehne) -> SlideForce Demo | Untertitel: Projekt Phoenix
2 | 15 Titel und Inhalt -> Agenda | Bullets mit Ebene 2
3 | 14 Tabelle -> Projektstatus | 1 echte Tabelle
4 | 12 Grosse Zahl -> Umsatz Q4 | zahl/einheit/erklaerung/einordnung gefuellt
5 | 05 Statement (Buehne) -> Statement | botschaft/zusatz gefuellt
```

## Hinweis Master-Datei

`web/uploads/default_master.pptx` (BRIDGE28, 5 MB) ist bewusst NICHT im Repo
(gitignore: uploads/). Ersatz im Repo: `examples/basic_master.pptx` (11
Standard-Layouts), wird von web/app.py als Fallback genutzt. Der Smoke-Test
braucht einen Master unter web/uploads/ - im Deployment vorhanden.

## Update 18.11. - Transkript-Fenster + Gedaechtnis

## Update 18.11. (2) - Premium-Modus: KI-Design je Folie (fmt=aipptx)

Neu: `slideforce/ai_design.py` - GLM 5.3 (b28-Bridge) designt JEDE Folie einzeln
(1 Call pro Folie, max 4 parallel, je ~2-7s). Strenge JSON-Bauanweisungen aus
8 Primitiven (band/linie/text/kachel/pill/kartenzeile/ring/tabelle), gerendert
mit den bewaehrten profiles.py-Renderern; Header/Footer/Logo zeichnet die Engine.
Fehler/Timeout/ungueltiges JSON -> statischer profiles-Fallback pro Folie.
Config: /opt/slideforce/ai-config.json (Lokal: web/ai-config.json).
KEINE manuellen XML-Manipulationen (nur python-pptx-API).

```
$ .venv/bin/python -c "... build_ai_deck(mini3) ..."
Folien: 3 ['title', 'content', 'content']
  progress 1/3 .. 3/3
Folie 1: KI - WEISS 5 Elemente / Folie 2: KI - WEISS 11 / Folie 3: KI - WEISS 8
STATS: {'folien': 3, 'ki': 3, 'fallback': 0, 'dauer_s': 6.9}

$ unzip -t output/ai-mini3.pptx  -> No errors detected
$ Reopen python-pptx            -> 3 Folien (16/41/31 Shapes)

Fallback (KI-URL unmoeglich): STATS {'folien': 3, 'ki': 0, 'fallback': 3, 'dauer_s': 3.3}, Reopen OK

Web-Endpunkt (echter Server + curl durch Token-Gate):
build: 200 (61064 Bytes)
X-Deck-Folien: 3 / X-AI-Folien: 3
unzip -t -> No errors detected
Server-Log: [ai] Folie 1/3 designt ... 3/3
```

Render-Pruefung auf gemivo (soffice -> pdf -> pdftoppm, 90 dpi) + glm-sicht:

```
Folie 2 (Projektstand, KI): SCORE: 8/10  (GEIL: Klar strukturierte KPI-Kacheln)
Folie 3 (Umsatz Q4, KI):   SCORE: 8/10  (GEIL: Konsistente Typo + Farbschema)
```
Beide >= 7 -> keine Prompt-Nachbesserung noetig. Preisgegebene "Probleme" sind
Inhalts-Nachfragen aus der Quell-md (z.B. 'vollstaendig' steht so in b28-demo.md),
keine Design-Defizite.

UI: 4. Export-Karte 'Premium . KI-Design' (Blitz-Icon) in web/templates/index.html,
Spinner-Text fuer aipptx angepasst, X-AI-Fallback-Hinweis im Status.

WICHTIG Deployment (nginx): proxy_read_timeout fuer SlideForce auf 600s stellen
(KI-Design grosser Decks dauert Minuten); lokale Aenderung an nginx NICHT gemacht.

```
POST /api/save -> {"id":"2026-11-18_1519_a098","label":"Meeting Notes KW47"}
GET /api/saved -> [{"id":"...","label":"Meeting Notes KW47"}]
GET /api/saved/<id> -> kompletter Text zurueck
Live (slideforce.gemivo.de): save/liste identisch getestet, HTTP 200
glm-sicht: SCORE 9/10 - Struktur klar, keine Layout-Probleme
Autosave: localStorage 'sf-text' bleibt ueber Reload
```

## Redesign 18.11. - UI v2 (nach Kays Abnahme-Kritik)

4x gerendert + Vision-geprueft: 4/10 (Login-Fehltest) -> 7/10 -> 8/10 -> 8/10 live ohne echte Bugs.
Neu: Gradient/Glass-Design, SF-Logo, Schritte 01-04, einheitliche SVG-Icons (0 Emoji),
Textarea mit klarer Abgrenzung, Export-Karten mit Check-Status, Glow-Button.
Live e2e: POST text -> HTTP 200, X-Deck-Folien: 8.

## BRIDGE28-Design-Profil (18.11., nach Kay-Feedback "b28-Export ist 1000x geiler")

Design-DNA aus bridge28-handbuch/b28-pptx-edit.js uebernommen (NAVY 002846, GOLD C9A961,
Header-Band + gold Kicker + weisser Titel, Kacheln mit Farbbalken, KW/Folien-Footer).
Render-Check via LibreOffice->PNG + Vision: Titelfolie 8/10, Tabelle 7/10, KPI 7/10,
keine Layout-Bugs. Live: https://slideforce.gemivo.de/files/b28demo.pdf (HTTP 200).
Neues fmt: b28pptx (dritte Export-Karte in der UI).

## PowerPoint-Corruption-Fix (18.11., stark/GLM-5.3)

Ursache: manuelle XML-Attrs (spc via _rPr.set, marL via pPr.set, _pPr-Truth-Test).
stark entfernt alle 3 Low-Level-Zugriffe -> reine python-pptx-API.
Beweise: Build ohne FutureWarning, unzip -t OK, reopen 8 Folien, smoke gruen.

## Download-Endungs-Fix (18.11.)

Bug: a.download='slideforce-deck.'+fmt -> bei fmt=b28pptx hiess die Datei *.b28pptx,
PowerPoint oeffnet unbekannte Endung nicht (Kays Meldung: "datei die keiner oeffnen kann").
Fix: a.download='slideforce-deck.'+(fmt=='html'?'html':'pptx')
Beweis: grep im Deploy bestätigt neue Zeile, UI live HTTP 200, /files/b28demo.pptx liefert
korrekte .pptx-Endung (unzip -t "No errors detected", siehe oben).

---

# BRIDGE28-Profil-Redesign (Session 2, gleiche Nacht)

Kay-Bewertung vorher: "1 von 10 - leer und billig". Ziel: ECHTER b28-Export-Look.

## Was geaendert wurde

| Datei | Aenderung |
|---|---|
| `slideforce/profiles.py` | Komplett-Redesign: kopf()/fuss()/kachel() 1:1 aus `bridge28-handbuch/b28-pptx-edit.js` portiert (NAVY-Band 0.95h, Kicker gold 10pt, Titel 23pt weiss, Zahl 30pt navy, Label uppercase 10.5 grau). NEU: Zeilen-Karten fuer Bullets (HELL-Fill, LINE-Border, 0.55h, gold Marker 0.08, 13pt; Unterpunkte eingerueckt 12pt mit Gold-Strich), KPI-Kachelreihe (zahl/zahl2/zahl3 mit einheitN/erklaerungN/einordnungN), Ring-Folie (kv `ring: 75` -> DOUGHNUT-Chart via python-pptx-Chart-API, gold Wert + navy Rest + Prozent im Zentrum + Legende + Infokachel), Status-Pills in Tabellen (Gruen->GRUEN, Gelb/Amber->AMB, Rot->ROT, weisser Bold-Text, Wortanfang-Match), Statement-Folie mit gold Anfuehrungszeichen, Bild-Unterstuetzung in Content-Folien. Footer mit Mini-Logo auf jeder Folie. Keine manuellen XML-Attrs. |
| `tools/gen_logo.py` | NEU: BRIDGE-Logo 1:1 aus `b28-folien.js` portiert (bridgeMotiv: goldener Spannbogen M 12 40 Q 100 10 188 40, 2 navy Pylonen, 5 Seile, Deckslinie, 2 Wellen + gold Schriftzug; bridgeMini monochrom navy) -> per cairosvg zu PNG gerendert. |
| `slideforce/assets/` | NEU: bridge_logo.svg/.png (Titelfolie, 1.9in), bridge_mini.svg/.png (Footer). |
| `slideforce/readers_text.py` | MAX_BULLETS 7 -> 6 (b28-Zeilen-Karten: max 6 je Folie, Rest -> Fortsetzungsfolie). |
| `examples/b28-demo.md` | NEU: Testdeck mit allen Folienarten (Zeilen-Karten, KPI zahl2, Ring, Status-Pills, Statement). |
| `.venv` | Repariert (kaputter Shebang nach Kopie von masterdeck) + cairosvg installiert. |

## Score-Entwicklung (glm-sicht, strenge Designer-Bewertung, je Folie)

| Runde | F1 Titel | F2 Karten | F3 KPI | F4 Ring | F5 Tabelle | F6 Liste | F7 Statement | O |
|---|---|---|---|---|---|---|---|---|
| 1 | 9 | 8 | 8 | 8 | 9 | 8 | 8 | 8.3 |
| 2 | 8 | 8 | - | 8 | - | - | 9 | 8.3 |
| 3 | 8 | 8 | 8 | 8 | 8 | 8 | 8 | 8.0 |
| 4 (final) | 8 | 8 | 8 | 8 | 8 | 8 | 9 | 8.1 |

Fixes je Runde: R2 Unterpunkt-Einrueckung deutlicher, Ring-Legende, Statement dichter (Anfuehrungszeichen), MD-Typo. R3 Ring-Kachel-Label duplizierte Kopf-Titel -> "Fortschritt", Titel-Abstand. R4 Legende groesser/bold.

Letzte Befunde R4: Restpunkte sind OCR-Fehllesungen bei 70dpi ("Puefprotokolle", "MioEUR" - Abstaende sind real vorhanden) sowie Content-Formulierungen, keine Layout-/Code-Fehler mehr.

## Beweise (finale Runde)

```
$ unzip -t output/test-b28.pptx | tail -1
No errors detected in compressed data of output/test-b28.pptx.

$ .venv/bin/python -c "reopen..." 
reopen OK: 7 Folien, 1 Chart(s), 8 Logo-Bild(er)

$ .venv/bin/python tests/test_smoke.py
SMOKE OK: 8 Folien, PPTX + HTML gebaut

$ .venv/bin/python -c "import web.app"
web/app.py Import OK

Render: rsync -> gemivo, soffice --headless --convert-to pdf, pdftoppm -r 70
-> output/render/b28f-1..7.png (glm-sicht-Scores siehe Tabelle Runde 4)
```
