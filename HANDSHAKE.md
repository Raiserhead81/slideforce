# HANDSHAKE SlideForce -> neue Session (18.11.2026, abends)

## Wer ich bin
Gemma, Kays Agentin (Mini). Chef heisst KAY. Session läuft als coding agent im SlideForce-Projekt.

## Was LIVE steht (alles bewiesen, auf GitHub Raiserhead81/slideforce, main)
- **SlideForce:** https://slideforce.gemivo.de  (Token-Zugang: `?token=<WERT>` setzt Session auf JEDEM Pfad; Token-Wert liegt UNVERSIONIERT in `web/token.txt` auf dem Server, nicht in Git)
- Server: gemivo, `/opt/slideforce/` (venv, systemd `slideforce.service`, Flask Port 8821, nginx + letsencrypt, proxy_read_timeout 600s)
- 5 Export-Karten: pptx (Master-Fill) / html / b28pptx (BRIDGE28-Design-Profil) / aipptx (Premium: GLM 5.3 designt JEDE Folie via JSON-Primitives, x-ai-folien Header) / vorpptx (Vorstandsvorlage-Profil nach Kays 2 Wunsch-Beispielen aus Downloads)
- Folien-Regler: minfolien/maxfolien (aipptx: GLM-Folienplan destilliert; statik: Verteilung)
- Kays 96-Folien-Deck lief erfolgreich durch (Log: journalctl -u slideforce)
- Transkript-SMART: kurze Zeilen ohne Satz-Ende = Kapitel (roher Text -> strukturiertes Deck)

## Projekt-Dateien (Mini: ~/gemma-projekte/slideforce)
- Engine: slideforce/ (readers_text/office, builder, profiles.py [b28+vorlage], ai_design.py [premium+folienplan], html_export.py, layoutmap.py, html_theme.py)
- Web: web/app.py (Token-Gate in before_request, /api/build, /api/layouts, /api/save, /api/saved, /files/<name>), templates/index.html (Dark-UI, 4x Vision-Iteration, Score 8/10)
- Tests: tests/test_smoke.py, test_vorlage.py, test_folienregler.py
- Referenz: docs/referenz/ref28-0*.png (Kays echter Export gerendert), docs/NACHWEIS.md (GLM-Gate braucht Nachweise IM DIFF - Message reicht nicht!)

## OFFENER AUFTRAG: GLM Presentation Studio (Kays Master Prompt, Best-of aus 2 Versionen)
Ziel: Agentur-Niveau-Produktionssytem UM die bestehende SlideForce-App (KEINE zweite Software):
- Rollen (alle GLM-5.3 via bridge28.gemivo.de/zai.php, Token in web/ai-config.json - UNVERSIONIERT): Presentation Director (State-Machine), Story Architect (Action Titles, Fakten/Annahmen), Art Director (Editorial-Niveau, Designsystem je Deck), Website Operator (nutzt SlideForce-Funktionen direkt im venv), Visual Critic (gerenderte PNGs, Score je Folie, Ziel 9/10, max 3 Korrektur-Runden dann transparent dokumentieren)
- brand/dataport/: Vermessene Werte: Petrol 39756F, Grau 39424A, Rot 9E292B, Karten F4F5F6, Tints F8E8E8/FBF0DC, weisser Grund, Logo slideforce/assets/vorlage_dataport.png, Referenz-Slides docs/referenz/
- 3 Produktionswege: A native PPTX (aipptx-Infra existiert), B Visual HTML (GLM designt je Folie HTML/CSS-Fragment -> Deck-Framework), C Hybrid (native + GLM-SVG-Infografiken via cairosvg -> PNG)
- State-Persistenz: studio/runs/<id>/state.json, fortsetzbar. Report: storyboard + designsystem + scores + schwaechen
- E2E: Vorstandsthema ITK-Bremen, 8-12 Folien, Weg A, alle >= 8/10 Vision
- Einstieg: studio/cli.py (`python studio/cli.py "<briefing>" --quelle <datei> --min 8 --max 12 --weg A`) + spaeter Web-Karte
- **Status 18.11. spaet: ETAPPE 1 + 2 FERTIG (committed, gepusht, deployed).**
  - Etappe 1 (Weg A): ABGENOMMEN - Run 20261118-200324, 9/10 Folien >= 8/10 (Folie 1: 7 intern / 8 extern)
  - Etappe 2a (Weg C Hybrid): E2E Run 20261118-202449, 10/11 Folien >= 8/10, GLM-SVG + cairosvg + Reparatur-Pass
  - Etappe 2b (Weg B Visual HTML): Code komplett, Tests 12 passed, E2E OFFEN (GLM 429 Tageslimit, resume: 20261118-203927 oder Web-Resume)
  - Etappe 2c (Web-Karte 05 Studio): LIVE auf slideforce.gemivo.de (200), app.run()-Blocker gefixt (NACHWEIS 8)
  - ETAPPE 3 OFFEN: Weg-B-E2E (sobald Kontingent), Doku documentation/*.md, glm-sicht der UI (429 des Pruefmodells)

## Gelernte Lektionen (NICHT wiederholen)
- PPTX-Corruption: KEINE manuellen XML-Attrs in python-pptx (spc/marL/_rPr.set) - PowerPoint öffnet sonst nicht (LibreOffice toleriert!)
- Download-Endung: UI-Download immer '.pptx' (fmt als Suffix war Kays "kann keiner öffnen"-Bug)
- GLM-Gate: Commit-Beweise als docs/NACHWEIS.md im Diff mitschicken
- Vision-Checks am GERENDERTEN Deck (gemivo: soffice -> pdf -> pdftoppm -> png -> ~/bin/glm-sicht), nicht an der Webseite
- Kays Wunsch-Stil = helle Vorstandsvorlage (F4F5F6/Petrol/Rot), NICHT navy/gold des alten Wochenberichts-Exports
- Bildgenerierung: ComfyUI auf Mini NICHT aktiv (Port 8188 tot) - Hybrid-Weg erstmal via GLM-SVG + cairosvg
- GLM-Proxy: bridge28.gemivo.de/zai.php (Kays Z.ai-Token, verbraucht Kays Kontingent; Premium-Folie = ~2.5k Token gemessen)

## Nach jeder Etappe
Deploy: rsync code -> ssh gemivo 'systemctl restart slideforce' -> curl 200 + gemma-proof -> commit via glm-commit (Gate!) -> push.
