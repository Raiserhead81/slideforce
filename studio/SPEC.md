# GLM Presentation Studio - Spec (Etappe 1: Weg A)

## Ziel
Agentur-Niveau-Produktionssystem UM die bestehende SlideForce-App (keine zweite Software).
Rollen sind GLM-5.3-Aufrufe. Infra-Vorbild: slideforce/ai_design.py (GLM-Anbindung, Token-Loading).

## Rollen (GLM-5.3 via bridge28.gemivo.de/zai.php, Token: web/ai-config.json, UNVERSIONIERT)
- Presentation Director: State-Machine, orchestriert alle Rollen, fuehrt state.json
- Story Architect: Action Titles, Fakten vs. Annahmen getrennt
- Art Director: Editorial-Niveau, Designsystem je Deck
- Website Operator: nutzt SlideForce-Build-Funktionen DIREKT im venv (import slideforce.*, kein HTTP)
- Visual Critic: bewertet GERENDERTE PNGs je Folie, Score 0-10, Ziel 9/10,
  max 3 Korrektur-Runden, danach Rest-Schwaechen transparent im Report

## Design-Brand dataport (Feste Werte)
- Petrol #39756F, Grau #39424A, Rot #9E292B, Karten #F4F5F6, Tints #F8E8E8/#FBF0DC
- Weiss #FFFFFF Grund, Logo: slideforce/assets/vorlage_dataport.png, Referenz: docs/referenz/
- Stil: HELLE Vorstandsvorlage, NICHT navy/gold

## Etappe 1: Weg A (native PPTX, baut auf aipptx-Infra auf)
- Einstieg: studio/cli.py
  `python studio/cli.py "<briefing>" --quelle <datei> --min 8 --max 12 --weg A`
- Ablauf pro Run: Director-Plan -> Story (Storyboard JSON) -> Art (Designsystem JSON)
  -> Build (native PPTX via SlideForce-Builder im venv) -> Render
  (soffice -> pdf -> pdftoppm -> PNGs) -> Critic je Folie -> max 3 Fix-Runden -> Report
- State: studio/runs/<id>/state.json nach JEDEM Schritt persistieren, fortsetzbar
  (CLI-Flag --resume <id>)
- Report: studio/runs/<id>/report.md (storyboard + designsystem + scores + schwaechen)

## Abnahmekriterien Etappe 1
1. `python studio/cli.py "ITK-Bremen Vorstand 2026" --quelle <testdatei> --min 8 --max 12 --weg A` laeuft E2E lokal
2. state.json pro Run, fortsetzbar
3. PPTX laesst sich oeffnen (unzip OK, KEINE manuellen XML-Attrs in python-pptx - Corruption-Lektion!)
4. Vision-Scores je Folie >= 8/10 (oder max 3 Runden + Schwaechen dokumentiert)
5. pytest: state save/load, mindestens ein Rollen-Aufruf gemockt

## NICHT in Etappe 1
- Weg B (Visual HTML), Weg C (Hybrid/GLM-SVG+cairosvg), Web-Karte "Studio", Deploy
