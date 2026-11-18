# GLM Presentation Studio - Bedienung

Das Studio ist die vollautomatische Produktionsebene um die SlideForce-App:
GLM 5.3 plant, storyboardet, designt, baut und kontrolliert ein Deck selbst -
bis jede Folie die Critic-Schwelle erreicht hat (Ziel 8/10, max 3 Fix-Runden).

## Live-Web (einfachster Weg)

https://slideforce.gemivo.de - Karte **05 Studio**:

1. Quelle oben bereitstellen (Karte 02 Inhalt-Datei oder Karte 03 Transkript)
2. Briefing eintippen (z.B. "ITK-Bremen Vorstand 2026")
3. Weg waehlen (A/B/C), optional min/max Folien
4. "Run starten" - der Run laeuft im Hintergrund (5-20 Min)
5. Fortschritt in der Run-Liste (Schritte + Scores, Polling alle 15s)
6. Downloads: deck.pptx / deck.html / report.md - "Resume" setzt abgebrochene
   Runs fort (auch nach Kontingent-429 oder Server-Restart)

## CLI (lokal auf dem Mini)

```bash
cd ~/gemma-projekte/slideforce
.venv/bin/python studio/cli.py "<briefing>" --quelle <datei.md> --min 8 --max 12 --weg A
```

- `--weg A` native PPTX (Standard) · `--weg B` Visual HTML · `--weg C` Hybrid
- Abbruch/Fehler: `--resume <run-id>` (steht in der Fehlermeldung)
- Runs liegen unter `studio/runs/<id>/` (state.json nach jedem Schritt)

## Die 3 Produktionswege

| Weg | Ergebnis | Besonderheit |
|-----|----------|--------------|
| A | native PPTX | Vorstandsvorlage-Profil (helle dataport-Optik), schnell |
| B | deck.html | GLM designt JEDE Folie als eigene HTML-Seite (1600x900), Chromium-Screenshots fuer die Kritik, Pfeiltasten-Navigation |
| C | PPTX + Infografiken | wie A, aber KPI-/Zeitstrahl-Folien bekommen zusaetzlich eine GLM-SVG-Infografik (cairosvg -> PNG rechts auf der Folie) |

## Was der Report enthaelt

`studio/runs/<id>/report.md`: Storyboard (Action Titles, Fakten/Annahmen),
Designsystem (Leitidee), Scores je Folie je Runde, Rest-Schwaechen transparent
(wenn nach 3 Fix-Runden etwas unter 8/10 bleibt), Zeiten je Schritt.

## Brand dataport (feste Werte)

Petrol #39756F · Grau #39424A · Rot #9E292B (nur Akzent) · Karten #F4F5F6 ·
Tints #F8E8E8/#FBF0DC · weisser Grund · Logo assets/vorlage_dataport.png
Referenz-Slides: docs/referenz/
