# GLM Presentation Studio - Architektur

## Rollen (alle GLM-5.3 via bridge28.gemivo.de/zai.php)

| Rolle | Datei | Aufgabe |
|-------|-------|---------|
| Presentation Director | roles.director | Plan (Zielgruppe, Kernbotschaft, Folienzahl), State-Machine-Orchestrierung in pipeline.run() |
| Story Architect | roles.story | Storyboard mit Action Titles, Fakten/Annahmen getrennt, validiert (validiere_storyboard) |
| Art Director | roles.art / art_repair | Designsystem + Folien-Designs (JSON-Slide-Dicts), Reparatur anhand Critic-Feedback |
| Website Operator | webop.py | nutzt SlideForce-Builder DIREKT im venv (slides_aus_design, build_pptx) - kein HTTP |
| Visual Critic | roles.critic | bewertet GERENDERTE PNGs je Folie (Vision), Score 0-10 + Schwaechen + Fix-Anweisung |
| Infografiker (Weg C) | roles.hybrid_svg | GLM-SVG im Brand, cairosvg-Render mit Reparatur-Pass |
| Frontend-Designer (Weg B) | roles.html_folie / html_repair | komplette HTML-Seite je Folie (1600x900, kein externes Zeug) |

GLM-Client: studio/glm.py - POST an die Bridge, 3 Retries mit Backoff,
429 -> RuntimeError (Run bricht SAUBER ab und ist resume-bar; nie 0-Scores).

## Ablauf (State-Machine, studio/pipeline.py)

director -> story -> art -> [C: hybrid | B: html | A: build] -> render ->
critic (Runde 1) -> fix_runden (max 3) -> report. Jeder Schritt persistiert
studio/runs/<id>/state.json; resume ueberspringt fertige Schritte.

Fix-Runden: Schwache Folien (< 8/10) werden repariert, neu gerendert und NUR
die geaenderten Folien re-kritisiert; Scores werden gemerged.

## Robustheit (Lektionen aus echten Runs)

- GLMs Antwortformat schwankt (valides/kaputtes JSON, Markdown-Fences,
  doppelte SVG-Attribute). Strategie ueberall: JSON-Erstversuch, dann
  Regex-Fallback auf das Rohformat (<svg>...</svg>, <!doctype html>...),
  dann Retry mit Hinweis-Prompt (3 Versuche).
- svg_zu_png: Reparatur-Pass _svg_dupe_attrs_raus (je Tag nur das erste
  Auftreten eines Attributs; Self-Closing sauber erhalten).
- Repair bewahrt Weg-C-Infografiken (image-Feld + hybrid_svgs im art-Schritt).
- Critic-Ausfall einzeln -> score 0 + "Critic-Fehler"; 429 insgesamt ->
  RuntimeError -> sauberer Abbruch (report = error, resume moeglich).

## Rendering

- PPTX: soffice -> pdf -> pdftoppm -> PNGs (render.render_folien)
- HTML: headless Chromium (render.html_screenshot); Chromium wird auf dem
  Mini UND gemivo aus vorhandenen playwright-caches gefunden (_chrome_bin,
  Mac- und Linux-Pfade)

## Web-Integration (web/app.py)

Karte 05: POST /api/studio/start (Hintergrund-Thread), GET /api/studio/status,
POST /api/studio/resume, GET /api/studio/runs, GET /api/studio/file (whitelist:
deck.pptx/deck.html/report.md). WICHTIG: Neue Routen MUESSEN vor den
`if __name__ == "__main__": app.run()`-Block - dahinter registrieren sie nie
(siehe docs/NACHWEIS.md, NACHWEIS 8).

## Tests

`.venv/bin/pytest tests/test_studio_state.py studio/test_state.py -q`
(12+ Tests: RunState-Rundlauf, Resume, 429-RuntimeError, SVG-Reparatur,
html_screenshot-Kette, Regex-Fallbacks). Echte GLM-Calls sind in den Tests
gemockt; E2E-Laeufe mit Kontingent siehe docs/NACHWEIS.md.
