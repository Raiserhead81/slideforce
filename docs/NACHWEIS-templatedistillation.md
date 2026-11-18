# NACHWEIS: Template-Distillation (18.11.2026, Kay: "pptx generator und html builder soll das lernen und koennen")

Quelle des Lernens: ~/Downloads/20261118_NGN_Bremen_Ergebnisse_DoD_und_Zeitplan.pptx
(32 Layouts, Petrol/Rot/Gold, Arial, Buehnen-Layouts). Vorherige NACHWEIS.md
unveraendert gelassen (Historie b28/Vorlage bleibt).

## Was gebaut
- slideforce/masterprofil.py (NEU): Master vermessen -> Profil (Canvas, Theme,
  Layouts mit Platzhalter-Geometrie in %, Rollen DE+EN-Keywords,
  2-Pass-Zuordnung). API: analyse/lade_profil/speichere_profil/rolle_zu_layout/
  layout_profil.
- layoutmap.py: pick() versteht zusaetzlich statement/botschaft, zahl/kpi,
  agenda, summary/zusammenfassung, roadmap, risiko, vier.
- builder.py: build() laedt Profil, waehlt Layout per Rolle (kind->rolle-Map),
  Fallback weiterhin lm.pick.
- html_export.py: Profil -> LAYCSS (tbox/bwrap absolut in %), hell/dunkel je
  Rolle, Papier- und Akzentfarbe aus Theme gelernt. Content-Box = groesste
  Nicht-Titel-Box unterhalb Titelzone (Fix fuer Ueberlappung).
- web/app.py: Master-Upload cachet <master>.profil.json, /api/layouts liefert
  jetzt auch role.

## Beweise (alle in dieser Session erzeugt)
1. NGN-Rollen: titel->01 Titelfolie Bremen, section->04 Kapiteltrenner,
   statement->05 Statement, kpi->06 Grosse Zahl, agenda->07 Agenda,
   chart->13 Diagramm, table->14 Tabelle, content->15 Titel und Inhalt,
   two->16 Zwei Spalten, three->17 Drei Spalten, picture->21 Bild,
   roadmap->22 Phasen, risiko->25 Risikomatrix, closing->30 Abschluss.
2. PPTX-Test (8 Folien, /tmp/ngn_test.pptx): jede Folie im korrekten Layout
   (gleiche Liste wie Rollen).
3. HTML-Test (/tmp/ngn_test.html): lay-Klassen 0/3/5/13/14/15/21/29 gesetzt,
   hell/dunkel korrekt, LAYCSS-Boxen: bwrap lay-14 = left 5.03% top 26% w 75%
   h 64.67% (echte Inhaltsbox, nicht mehr Untertitel-Box).
4. glm-sicht Screenshots: Titelfolie SCORE 8/10; Content-Folie nach Fix
   "Kein Ueberlappung zwischen Titel und Bullets"; KPI-Folie grosse Zahl
   347 lesbar "sorgt fuer sofortige Aufmerksamkeit"; Tabellen-Folie
   "vollstaendig sichtbar, Kopfzeile gut lesbar".
5. pytest tests/test_smoke.py tests/test_vorlage.py tests/test_studio_state.py:
   5 passed. (test_folienregler braucht /tmp/normales-transkript.txt -
   Umgebungsproblem, von dieser Aenderung unberuehrt.)
6. Flask-Testclient: Login-Token 302, GET /api/layouts 200 mit Rollen-Feld.

## Sichtpruefung (GLM 4.5V / 5.3-flash ueber glm-sicht)
Screenshots /tmp/ngn_sicht.png (Folie 1), /tmp/ngn_f4.png (Content),
/tmp/ngn_f3.png (KPI), /tmp/ngn_f5.png (Tabelle). Offene Kosmetik laut Pruefer:
Kicker-Farbe auf Titelfolie = Theme-Akzent (Rot statt Petrol - Master-Vorgabe),
Footer-Zaehler klein. Keine Blocker.

## Nachreich (Gate-Runde 2)
- Imports: builder.py und web/app.py nutzen jetzt Top-Imports
  (builder -> layoutmap + masterprofil; masterprofil -> html_theme + layoutmap;
  html_theme/layoutmap importieren nichts zurueck = kein Kreislauf).
  Beweis: `python -c "import slideforce.masterprofil, slideforce.layoutmap,
  slideforce.builder, slideforce.html_export, web.app"` laeuft sauber
  (diese Session, keine Fehlermeldung).
- Testlauf mit NGN-Profil: siehe Beweise 1-4 (Rollen-Zuordnung PPTX + HTML +
  Screenshots) - genau der geforderte Testlauf mit den neuen Profilen.

## Visuelle Artefakte (im Diff, frisch gerendert nach letztem Fix)
- docs/beweis/templatedistillation/folie1.png: Titelfolie (dunkel, lay-0)
- docs/beweis/templatedistillation/folie3.png: KPI Grosse Zahl (lay-5, hell)
- docs/beweis/templatedistillation/folie4.png: Titel und Inhalt (lay-14, Boxen)
- docs/beweis/templatedistillation/folie5.png: Tabelle (lay-13, hell)
Quelle: HTML-Export aus NGN-Master + 8-Folien-Testdeck, Screenshot per
sichtpruefung, geprueft mit glm-sicht (Scores + Befunde in dieser Datei).
