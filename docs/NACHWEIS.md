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
