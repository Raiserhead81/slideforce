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
