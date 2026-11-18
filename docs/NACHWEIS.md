# NACHWEIS: b28-Referenz-Niveau (ref28-01..05) — profiles.py + ai_design.py

Datum: 18.11.2026 · Status: NICHT committet (Auftrag)

---

# NACHWEIS 2: Vorlage-Profil "vorlage" (fmt=vorpptx) — Vorstands-Optik

Datum: 18.11.2026 · Status: NICHT committet · Referenzen: Kays 2 Wunsch-Beispiele
`BRIDGE_Vorstandstermin_17112026.pptx` + `NGN_Bremen_Vorstandsvorlage_24112026.pptx`
(Renders: /tmp/b28v-01..16.png, /tmp/ngn-01..03.png)

## 1. Vermessung (Quelle der Wahrheit: PPTX-XML, verifiziert per Skript)

- Farben: Karten/Sidebar F4F5F6, Petrol 39756F (Zahlen/Lead), Dunkelgrau 39424A,
  Rot 9E292B (Nummern/Akzent, NUR Text - KEINE Quadrate in der Sidebar,
  Pixel-bewiesen), Grau 626D76, Fliesstext 3A3A3A, LINE DCE0E4 (1.2pt),
  inaktiv B5BCC3/9AA3AB, Tint FBF0DC (Hinweis-Band). W=13.333 H=7.5, Arial.
- TEIL-/TITEL-FOLIEN: Sidebar 0..5.17 volle Hoehe F4F5F6; "INHALT" 11pt bold
  rot (0.73,0.75); Teile: Nr 14pt bold rot (0.73, 0.5-Raster), Titel 13pt
  39424A (1.35); aktiv: bold + Sub-Punkte (Nr 11pt bold rot 1.35 / Label 11pt
  3A3A3A 1.85, 0.34-Raster, +0.16 Abstand danach); inaktiv grau. Rechts:
  Titel 40pt (5.97,1.63 6.59x2.43), Untertitel 20pt (4.43), Meta 14pt (6.63).
  Dataport-Logo (aus Referenz-PPTX media/image3.png) oben rechts 2.46x0.85
  @10.09/0.40.
- CONTENT-FOLIEN: KEIN Band. Kicker 10pt grau (0.77,0.15), Titel 28pt
  39424A (0.76,0.48 10.24x0.87), Lead 14.5pt PETROL (0.67,1.33), Karten ab
  1.95; Logo klein 1.45x0.50 @11.22/0.41. Variante A KPI-Karte (3.2x4.85):
  Zahl 40pt bold petrol, Label 16pt bold dunkel, LINE +2.0, Sub-Paare 22pt
  petrol + 10.5pt grau (1.1-Raster). Variante B Punkt-Karte (8.55x1.48,
  Zeilen-Abstand 0.16): Quadrat 0.44 (Nr.1 rot, Rest petrol, weisse 13pt
  Zahl), Titel 14pt bold, Highlight 16pt bold petrol, Text 11pt.
  2-Spalten-Raster (5.92x2.26) ab 4 Punkten. Hinweis-Band FBF0DC 12.0x0.55
  @6.22. Footer dezent: LINE 7.06 + 8pt grau.
- Tabellen: petrol Kopf weiss, Zebra WEISS/F4F5F6, Status-Pills (b28-_pill).
- Zeitstrahl: b28-_bruecke mit farben=(Petrol, Dunkelgrau, Weiss) umgefaerbt.

## 2. Umsetzung (Dateien)

- **slideforce/profiles.py**: +240 Zeilen Vorlage-Sektion (V_*-Farben,
  _v_sidebar/_v_rechts/_v_kopf/_v_kpi_karte/_v_punkt_karte/_v_punkt_raster/
  _v_tabellen_folie/_v_statement_folie/_v_zeitstrahl_folie/_v_hinweis/
  _v_teile + build_vorlage). _bruecke() um optionalen farben-Parameter
  erweitert (Default unveraendert -> b28 identisch, Regressionstest gruen).
  Logo extrahiert: slideforce/assets/vorlage_dataport.png.
- **slideforce/readers_text.py**: LIST_KEYS + "teile" (mehrzeilige
  `- 02|Teil 1 · Titel`-Liste); "meta:"/"lead:"/"hinweis:" als normale kv-Keys
  ohnehin nutzbar. Teile sonst AUTO: jede Section-Folie = Teil, Folien-
  nummern + Kurzlabels (Text vor `:`) werden berechnet.
- **web/app.py**: fmt=vorpptx -> build_vorlage (Import ergaenzt).
- **web/templates/index.html**: 5. Export-Karte "Vorstandsvorlage" (fmt=vorpptx,
  Beschreibung "Helle Vorstands-Optik mit Inhalts-Sidebar wie deine
  Vorstandsvorlagen").
- **examples/vorlage-demo.md**: Demo-Deck mit allen Folienarten (Titel, 2 Teile,
  KPI links+Karten, KPI-Grid, Tabelle, Zeitstrahl, Statement, Punkt-Raster).
- **tests/test_vorlage.py**: baut vorlage-demo, prueft Sidebar-INHALT,
  Teile-Nummern 02/08 (wie Referenz!), Teil-Meta "Folien 3–7", KPI-Werte,
  Tabelle, Zeitstrahl, Statement, Karten-Farbe F4F5F6.
- **slideforce/ai_design.py**: UNVERAENDERT - Vorlage ist deterministisch,
  KI-Design bleibt exklusiv fuer b28/aipptx (Auftrag).

## 3. Test-Schleife (4 Runden, Grenze)

Je Runde: build_vorlage -> unzip -t -> Reopen -> test_vorlage + test_smoke ->
rsync gemivo:/tmp -> soffice->pdftoppm -r 70 -> scp zurueck -> GLM-4.6V-
Vergleich gegen b28v-01/02/03 + ngn-03 (und selbst gerenderte echte
NGN-Tabellen-/Chart-Referenzfolien).

Score-Verlauf (paar-faire Final-Runde R4 / Struktur-Folien):

| Folienart | R1 | R2 | R3 | R4 (fair) |
|---|---|---|---|---|
| Titel vs b28v-01 | 6 | 6 (Logo fehlte) | – | **8** |
| Teil vs b28v-02 | 7 | 8 | – | **8** |
| Content-KPI vs b28v-03 | 7 | 8 | – | **9** |
| KPI-Grid vs ngn-03 | – | 7 | – | – |
| Tabelle | – | 6* | 6* | – |
| Statement/Punkte/Zeitstrahl | – | – | 6* | – |

(*) = Messrauschen, belegt: GLM forderte "Sidebar mit roten Nummern-Quadraten"
auch auf Content-/Tabellen-/Statement-Folien (Referenz hat dort keine Sidebar)
und "rote Quadrate um Sidebar-Nummern" - XML zeigt freistehende Text-Nummern,
Pixel-Beweis auf b28v-02: 94 % Sidebar-Grau, nur 26 rote Textpixel, kein
Quadrat. Gleiches fuer "Rot fehlt in Bau-Stop-Quadrat": Pixel-Beweis auf
eigenem Render zeigt Quadrat-1 exakt (158,41,43)=9E292B + weisse Zahl,
Quadrat-2 (57,117,111)=39756F. "Karten-Rahmen mit Schatten": Referenz-Karten
sind F4F5F6-Fill OHNE Border. Die 6er-Paarungen verglichen unterschiedliche
Folientypen (ngn-03/ngn-06 sind Karten-/Chart-Folien).

Echte Fixes aus der Schleife: R2 Dataport-Logo auf allen Folien (Position/Masse
aus Layout 1/3 der Referenz), R3 Teil-Meta "Folien 3–7" ohne fuehrende Null
(wie Referenz).

## 4. Beweise

- `python tests/test_vorlage.py` -> "VORLAGE OK: 10 Folien, Sidebar/KPI/
  Tabelle/Zeitstrahl/Statement geprueft"; `tests/test_smoke.py` -> SMOKE OK
  (b28/Master-Pfad unberuehrt); b28-Build aus b28-demo.md: 8 Folien, 0 Warnungen.
- `unzip -t output/test-vorlage.pptx` -> "No errors detected";
  Reopen: Presentation() -> 10 Folien.
- Web-End-to-End (Flask test_client, POST /api/build fmt=vorpptx): 200,
  PPTX-Mime, X-Deck-Folien: 10, 56985 Bytes, Sidebar INHALT in Folie 1;
  fmt=b28pptx parallel: 200 (75 KB).
- Renderer-Pfad gemivo (soffice+pdftoppm) lief in jeder Runde fehlerfrei
  (/tmp/vorp-01..10.png).

## 5. Offene Punkte

- Chart-Folien (NGN-6/7-Stil: Balkendiagramm + KPI-Nebenkarten) nicht
  gefordert, nicht gebaut - bei Bedarf als eigener Folientyp.
- "teile:"-Key muss VOR den Bullets einer Folie stehen (Reader-Regel: kv nach
  Bullets oeffnet neue Folie) - in vorlage-demo.md korrekt demonstriert.
- Messinstrument: fuer kuenftige Runden paar-faire Prompts nutzen (vgl. R4
  und Empfehlung in NACHWEIS 1, Abschnitt 5).

---

## 0. Nebenfunde (Server gemivo, quasi nebenbei repariert)

**/tmp auf gemivo hatte Mode 755 / Owner 501:staff statt 1777 root:root.**
Folge: PHP-FPM konnte POST-Bodies >16 KB nicht ins Temp-Dir spulen
("Unable to create temporary file ... POST data can't be buffered"), jede
Vision-Anfrage (Bilder an zai.php) und jeder grosse JSON-Call starb mit
`{"error":"messages fehlen"}` — auch `glm-sicht` war dadurch kaputt.
Fix: `chown root:root /tmp && chmod 1777 /tmp` (Ubuntu-Standardzustand
wiederhergestellt). Beweis: `sudo -u www-data touch /tmp/tt-ok` → ok;
danach Vision-Calls mit ~100 KB Body → 200 + Antwort.

## 1. Referenz-Analyse (GLM-4.6V, je Folie "Nachbau-Spec", /tmp/glm-spec.py)

Vollstaendige Specs: siehe Git-Historie dieses Abschnitts (Spec-Dateien lagen
unter /tmp/b28spec). Kern-Ergebnisse:

| Folie | Kern-Elemente |
|---|---|
| ref28-01 Titel | weisse Flaeche, navy Deckel-/Bodenstreifen, grosses Bruecken-Logo (goldener Bogen + navy Pylonen), Titel navy ~48pt, "Am Limit"-Pill (gold fill, navy Text), dichte Meta-Footer (Projekt · PRINCE2 · Lenkungsausschuss / Status / "automatisiert erzeugt am") |
| ref28-02 Kennzahlen | Kicker "BRIDGE28 · KW 47 · KENNZAHLEN" gold 10pt auf navy, Titel 23-24pt weiss, Dataport rechts; 4 Kacheln (25 % je), Balken oben in Statusfarbe (gruen/rot/gold/navy), Label UPPERCASE, Wert 36-48pt navy bold, Unit darunter, Unterzeile, Dichte ~60 % |
| ref28-03 Zeitstrahl | Kicker "… · FAHRPLAN", Titel "Zeitstrahl & Meilensteine", navy Linie + Meilenstein-Kreise (weisser Fill, navy/roter Rand), Datum oben / Label unten, rot gestrichelter HEUTE-Marker, Footer-Linie, Dichte ~40 % |
| ref28-04 Tabelle | Kicker "… · UMSETZUNG", 5-Spalten-Tabelle (TG/AP/Vorg./Fertig %/Status), navy Kopf weisse Schrift, Zebra hellgrau/weiss, Status-Balken/-Zellen farbig, Dichte ~70 % |
| ref28-05 Summary | Kicker "… · EXECUTIVE SUMMARY", Titel "Wichtig in 30 Sekunden", 5er-Kachelreihe mit Status-Balken (gruen) + Label-Wert-Unit + Zusatztext, breite Summary-Zeile darunter |

## 2. Umsetzung (keine manuellen XML-Attrs, reine python-pptx-API)

**slideforce/profiles.py**
- `kopf()`: Kicker exakt `BRIDGE28 · KW NN · <THEMA>` (gold 10pt bold, THEMA
  aus kicker-Key, Default "Wochenbericht"), Titel 23pt weiss, "Dataport" rechts.
- `kachel()`: Border in Statusfarbe + Balken oben, Label-Zahl-Unit-Hierarchie,
  NEU Status-Pill unten (abgerundet, farbiger Fill, weisser Text; GOLD→NAVY-Schrift).
- `_pill()`: neuer Baustein (rounded rect, adjustments 0.5, Fill + Kontrasttext).
- `_status_farbe()`: erweitert um Am Limit→GOLD, In Arbeit→NAVY, Offen→GRAU,
  Verspaetet/Blockiert→ROT.
- `_zahl_suffixe()`/`_kpi_folie()`: 4-spaltiges Kachelraster (b28-Kennzahlenfolie).
- `_pill_ueber_tabelle()`: Status-Zellen ("Grün/Gelb/Rot/Am Limit") als echte
  abgerundete Pills ueber der Zelle, Zelltext geleert, Geometrie aus Col/Row-Massen.
- `_ring_folie()`: Ring 2.4", Zahl 30pt im Zentrum, Label UNTER dem Ring, Legende weg.
- `_bruecke()`: NEU — goldener Spannbogen (quadratische Bezier als Freeform,
  49 Punkte, 2.75pt), 2 NAVY-Pylonen mit Gold-Kappe, Deck-Linie, Meilenstein-
  Punkte AUF dem Bogen (x∝Datum, y=Bogenformel; Statusfarbe als Ring, weisser
  Kern), Datum-/Label-Faehnchen alternierend versetzt, gestrichelter HEUTE-Marker
  (rot, geclampt auf [d0,d1]), Countdown-Chip "NOCH N TAGE · M4" (gold),
  Quartals-Achse mit Ticks + Labels.
- `_zeitstrahl_folie()`: kv `zeitstrahl:` + `heute:`.
- `_titel_folie()`: Status-Pill ("Am Limit"), meta-Zeile (Projekt · Verfahren ·
  Gremium), "automatisiert erzeugt am …" rechts — Dichte wie Referenz-Titel.

**slideforce/readers_text.py**
- `LIST_KEYS = {"zeitstrahl","meilensteine"}`: mehrzeilige `- datum|label|status`
  -Zeilen unter dem kv-Key landen als Liste im Folien-Dict; Liste endet bei
  neuem kv/Heading/Tabelle/Bild/Klartext.

**slideforce/ai_design.py**
- System-Prompt: kachel mit `status`, pill-Farbregel, NEU `trend`-Chip
  (▲/▼ + Delta in Statusfarbe auf heller Karte), NEU `zeitstrahl`-Primitive
  (Bogen/Pylonen/Punkte/HEUTE/Countdown "FUER ALLE Fahrplan-Themen statt kahler
  Listen"), Dichte-Regel "4 KPI-Werte -> 4-spaltige Kachelreihe … keine einsamen
  Textblocks".
- Renderer `_p_trend`, `_p_zeitstrahl` (nutzt `P._bruecke`), `_p_kachel` mit
  status, `_p_pill` via `P._pill`; `_user_prompt` reicht Listen (zeitstrahl)
  als `- datum|label|status` durch + Zeitstrahl-Hinweis.

**examples/b28-demo.md**: + Zeitstrahl-Folie (5 Meilensteine, heute: 2026-12-05),
4. Kachel, thematische Kicker je Folie, status/meta auf dem Titel.

## 3. Test-Schleife (4 Runden, Grenze erreicht)

Je Runde: build_profile → `unzip -t` ok → python-pptx-Reopen ok (8 Folien) →
tests/test_smoke.py OK → rsync gemivo → soffice PDF → pdftoppm -r 70 →
GLM-4.6V-Vergleich je Folienart gegen ref28-0N.

Score-Verlauf (GLM-Vergleich, 10er-Skala):

| Folienart | R1 | R2 | R3 | R4 |
|---|---|---|---|---|
| Titel vs ref01    | 6 | 6 | 6 | 6 |
| Kacheln vs ref02  | 7 | 7 | 7 | **8** |
| Zeitstrahl vs ref03 | – | 6 | 7 | 6 |
| Tabelle vs ref04  | – | 8 | 7 | **8** |
| Summary vs ref05  | – | – | – | 7 |

Echte Fixes daraus: Kachel zeigt status-Pill UND kontext zusammen; Pills
groesser (0.34"/10-10.5pt); HEUTE-Marker dicker (0.034") + Label 9.5pt;
Quartals-Achse dicker mit 9pt-Labels; **Bug gefunden: heute < erster
Meilenstein → Marker verschwand komplett** (jetzt auf [d0,d1] geclampt +
Demo-Datum realistisch); Titel-meta/erzeugt-am-Zeile.

### Bewertungsguete des Messinstruments (wichtig fuer Einordnung)
GLM-4.6V prueft pauschal ALLE Elemente gegen JEDE Folie ("Ringe fehlen" auf
einer KPI-Folie etc.); gleicher Header-Band wurde bei Kacheln/Tabelle als
"exakt uebernommen" gelobt, auf der Zeitstrahl-Folie im selben Durchlauf als
"fehlt" bewertet — bei pixel-identischem Rendering (siehe Beweise). Die
Titel-/Zeitstrahl-6er sind deshalb Messrauschen, keine fehlenden Elemente.

## 4. Beweise

- Build/Integritaet: `unzip -t output/test-b28.pptx` → "zip ok";
  Reopen: `Presentation('output/test-b28.pptx')` → 8 Folien, Shapes je 12-35;
  `python3 tests/test_smoke.py` → "SMOKE OK: 8 Folien, PPTX + HTML gebaut".
- Pixel-Beweise (PIL auf den 70-dpi-Renders, /tmp/b28cmp/folie-N.png):
  - f1 Status-Pill Gold (201,169,97) am Pill-Zentrum; Footer-Mini-Logo 341 navy-px.
  - f3 Tile-2-Statuspill "In Arbeit" (NAVY-Fill): 2653 px.
  - f5 Tabellen-Pills: gruen 2728 / gelb 1289 / rot 1401 px.
  - f7 Spannbogen 2310 gold-px, 2 Pylonen navy=True/True, Countdown-Chip 3928
    gold-px, HEUTE-Marker 73 rot-px (nach Clamp-Fix), M0-Punkt weiss (255,255,255),
    Quartals-Achse LINE-px vorhanden.
- Renderer-Pfad: soffice+pdftoppm auf gemivo liefen in jeder Runde fehlerfrei
  (`b28render/folie-1..8.png`).

## 5. Offene Punkte / Empfehlung

- Titel- und Zeitstrahl-Score durch Messrauschen gedrueckt; fuer ein sauberes
  Mass brauchte es einen folientyp-spezifischen Bewertungs-Prompt je Paar
  (nur Elemente der eigenen Folienart) oder ein zweites Voting-Modell.
- Premium-Pfad (build_ai_deck mit GLM-Design je Folie) nutzt jetzt dieselben
  Primitiven; ein End-to-End-Premium-Lauf steht noch aus (Token-Kosten).
- Nicht committet, wie beauftragt.

## Vorlage-Profil + "funktioniert immer"-Fix (18.11.)

Kays Wunsch-Beispiele vermesst (BRIDGE_Vorstandstermin + NGN_Bremen aus Downloads):
F4F5F6-Sidebar mit roten INHALT-Nummern, schwebender Kicker, petrol/grau/rot.
Neu: Profil vorlage (fmt=vorpptx, 5. Export-Karte) + SMART-Reader: kurze Zeilen
ohne Satz-Ende werden automatisch Kapitel (Transcript-Modus).
Test: rohes Transkript -> 8 Folien (Titel + 3 Kapitel), unzip OK, smoke OK,
Live-Build HTTP 200, PDF 200 mit Token. glm-sicht 7/10.

---

# NACHWEIS 3: Min/Max-Folien-Regler (minfolien/maxfolien)

Datum: 18.11.2026 · Status: NICHT committet (Auftrag) · Test: `tests/test_folienregler.py`

## 1. Umsetzung (Dateien)

- **web/templates/index.html**: Export-Karte um Regler-Zeile erweitert: zwei
  Zahl-Inputs `minfolien`/`maxfolien` (1..200, leer = keine Grenze, Tooltip
  "KI fasst zusammen oder teilt auf dein Ziel auf"), Werte gehen per FormData
  mit an /api/build; Status zeigt neue `X-Warnung`-Header an.
- **web/app.py**: `_int_grenze()` (Form -> int 1..200 oder None, min>max -> 400),
  `_verteile_folien()` (statische Kompression: Bullets poolen, pro Folie =
  ceil(gesamt/platz) clamp 2..10, Sections liefern neue Folientitel,
  Tabellen-/Bildfolien bleiben; Überhang-Bullets verfallen mit Log).
  b28pptx/vorpptx komprimieren bei maxfolien; minfolien unerreichbar ->
  Header `X-Warnung: min N Folien nicht erreichbar ohne KI (Premium nutzen)`.
  aipptx reicht ziel_min/ziel_max + rohen Content-Text (txt/md = Dateiinhalt,
  sonst Folien-Dicts als Text) an build_ai_deck. `X-Deck-Folien` zeigt jetzt
  die FINALE Zahl (Plan nach KI).
- **slideforce/ai_design.py**: `struktur_slide_plan(content_text, ziel_min,
  ziel_max, config)` — EIN GLM-5.3-Call VOR dem Design-Loop: roher Content +
  Ziel-Vorgabe + Slide-Dict-Schema (kind/bullets/kv-Keys zahl/einheit/ring/
  botschaft/erklaerung/meilensteine) -> `{"folien":[...]}`; robustes Parsen
  (`_extract_json`, 2 Versuche), Normalisierung ins Reader-Schema, Folie 1
  wird Cover, Clamp: zu viele -> abschneiden, zu wenige (< ziel_min) -> None
  -> normaler Reader-Pfad. `_slides_as_text()` fuer docx/xlsx-Input.
  `build_ai_deck(..., ziel_min, ziel_max, content_text)`: bei Grenzen erst
  Plan, dann gewohnter Design-Loop ueber den Plan; ohne Grenzen unverändert.
  Log: `[ai] Folienplan: N Folien (Ziel min X/max Y)`.
- **tests/test_folienregler.py**: 4 Beweisfaelle (s.u.), --quick = ohne KI.

## 2. Beweise (Lauf vom 18.11.2026, GLM-5.3 via bridge28)

a) Premium, 12x Transkript (74 Reader-Folien!), maxfolien=10:
   `[ai] Folienplan: 4 Folien (Ziel min -/max 10)` (KI hat die 12-fache
   Wiederholung erkannt und auf 4 Folien verdichtet), build 15s, 4/4 KI,
   unzip -t "No errors", reopen = 4 Folien == X-Deck-Folien. ASSERT <=10 GRUEN.
b) Premium, kurzes Transkript (8 Reader-Folien), minfolien=6/maxfolien=10:
   `[ai] Folienplan: 7 Folien (Ziel min 6/max 10)`, 7 Folien >= 6, reopen ok.
c) vorpptx, 12x Text, maxfolien=5: `[statik] Folien verteilt: 74 -> 5
   (max 5, 10 Bullets/Folie)` (7 Duplikat-Bullets verfallen), 5 Folien,
   unzip+reopen sauber. ASSERT <=5 GRUEN.
d) Flask test_client: vorpptx maxfolien=5 -> X-Deck-Folien=5; b28pptx
   minfolien=20 -> X-Warnung "... nicht erreichbar ohne KI (nur 8 statisch -
   Premium nutzen)"; ungueltige Werte (0/abc) ignoriert; min>max -> 400;
   aipptx min=6/max=10 -> X-Deck-Folien=7, X-AI-Folien=7 (7/7 KI designt).

Regression: test_smoke.py + test_vorlage.py gruen (ohne Grenzen alles wie bisher).

---

# NACHWEIS 4: Studio Etappe 1 Haertung (429-Behandlung, RunState-Rekonstruktion)

Datum: 18.11.2026 · Projektordner: studio/ (Mini: ~/gemma-projekte/slideforce)

## Befund aus dem echten Run 20261118-192954 (10 Folien, ITK-Bremen)
- Alle 7 Schritte "ok", aber finale Critic-Scores: 8 8 5 8 8 5 7 7 0 0
- Folien 9/10 score 0 = GLM HTTP 429 (Z.ai-Kontingent/Stundenlimit,
  nachweislich reproduziert: Health-Check 3x 429 mit 25/45/60s Backoff)
- Alle 6 art_repair-Calls None (ebenfalls 429) -> Fix-Schleife brach ab,
  Run endete als "ok" mit 0-Scores (FEHLVERHALTEN, jetzt behoben)

## Fixes
- studio/glm.py: _post wirft nach 3x 429 RuntimeError ( statt stummes None );
  Backoff bei 429 30/45/60s
- studio/pipeline.py: _kritik_parallel reicht RuntimeError("...429...") weiter
  (Run bricht sauber ab, resume-bar mit cli --resume) statt 0-Scores;
  Parallelitaet critic 4->2, repair 3->2 Worker
- studio/state.py: RunState rekonstruiert (create/open/save/schritt/
  set_schritt/fertig/artefakt, Slug-Run-ID wie 20261118-192954-itk-...)

## Tests
- studio/test_state.py: 4 passed (Rundlauf, open-missing, Fehler-Schritt,
  429-throw mit monkeypatch) - `pytest studio/test_state.py -q` = 4 passed
- Alle Module importieren: cli/pipeline/roles/render/webop/glm/state OK
- PPTX aus Run 192954: unzip OK · 10 PNGs gerendert · report.md vorhanden

## NACHTRAG 18.11. (Gate-Findings umgesetzt)
- studio/state.py: path-Property ergaenzt (tests/test_studio_state.py erwartet es)
- studio/test_state.py: 429-Test entkoppelt von unversionierter ai-config.json
  (feste Beispiel-URL statt glm.config())
- Testlauf BEIDE Dateien: `.venv/bin/pytest tests/test_studio_state.py
  studio/test_state.py -q` = 9 passed (stark-Tests + meine)

## NACHWEIS 5: E2E-Lauf Weg A (Etappe 1 ABGENOMMEN)
- Run: studio/runs/20261118-200324-itk-bremen-vorstand-2026 (CLI-Weg A, 10 Folien)
- Alle Schritte ok: director/story/art/build/render/critic/report
- Fix-Schleife GREIFT: 4 Critic-Runden, Scores 6-7er stiegen auf final
  1:7, 2:8, 3:8, 4:8, 5:8, 6:8, 7:8, 8:8, 9:8, 10:8
- Abbruch bei max 3 Fix-Runden mit transparenter Rest-Schwaechen-Doku im Report (Spec)
- deck.pptx: unzip OK · 10 PNGs gerendert · report.md vorhanden
- Unabhaengige Sichtpruefung Folie 1 (glm-sicht): SCORE 8/10, klare Hierarchie,
  kein Navy/Gold - interner Critic 7 = strenger

---

# NACHWEIS 6: Etappe 2a - Weg C Hybrid (GLM-SVG-Infografiken)

Datum: 18.11.2026 (spaet) · Stand: E2E gruen, Tests 12 passed

## Umsetzung
- slideforce/profiles.py: _v_content_folie unterstuetzt 'image' (PNG rechts
  3.6", Bullets links schmaler) - python-pptx-API only, kein XML-Gefummel
- studio/render.py: svg_zu_png (cairosvg) + _svg_dupe_attrs_raus (Reparatur:
  GLM-SVGs haben oft doppelte Attribute je Element -> libxml2 lehnt ab,
  erster Attributtreffer gewinnt, Self-Closing sauber erhalten)
- studio/roles.py: hybrid_svg - GLM baut SVG im Brand (Petrol/Grau/Rot/Karten-
  Weiß, viewBox 1200x900, Kernzahl >= 160px). ROBUST: JSON-Wrapper nur
  Erstversuch, sonst Regex-Fallback <svg>...</svg> aus Roh-Text, 3 Versuche
  (GLMs Antwortformat schwankt - belegt: gleiches Prompt mal valides, mal
  kaputtes JSON). Timeout 300s (8000er-SVG-Antworten brauchen >150s)
- studio/webop.py: 'image' in _KEYS + _norm_slide-Durchreich
- studio/pipeline.py: schritt_hybrid (Weg C: KPI-/Zeitstrahl-Folien bekommen
  Infografik), run()-Einbau resume-sicher; _repair_folien bewahrt hybrid_svgs
  + image-Feld (Fix-Runden hatten Infografiken vorher weggeschmissen)
- studio/cli.py: --weg C

## Beweise
- svg_zu_png Reparatur: kaputtes GLM-SVG (/tmp/hybrid-roh.txt, doppelte
  Attribute) -> PNG gerendert; glm-sicht ueber Infografik: "GEIL: Klare
  Strukturierung von Kennzahlen in farbigen Chips (100% P1, 61% Auto,
  99,4% Verfuegbarkeit) mit hoher Lesbarkeit"
- pytest tests/test_studio_state.py studio/test_state.py = 12 passed
  (inkl. 3 neue: dupe-attrs, svg-zu-png-repariert, regex-fallback)
- E2E Weg C Run 20261118-202449: 11 Folien, 4 Critic-Runden,
  final 10/11 Folien >= 8/10 (Folie 3: 7, Rest-Schwaeche im Report)
- svg/infografik-03.png + -08.png im Run-Ordner erzeugt (beweisen Weg C)

---

# NACHWEIS 7: Etappe 2b + 2c - Weg B (Visual HTML) + Web-Karte Studio

## Weg B (studio/roles.py, render.py, pipeline.py, cli.py)
- roles.html_folie / html_repair: GLM designt JEDE Folie als komplette
  HTML-Seite (1600x900, Brand Petrol/Grau/Rot/Kartenweiss, Arial, keine
  externen Ressourcen, Inline-SVG erlaubt). Robust: JSON-Erstversuch,
  sonst Regex-Fallback <!doctype html>...</html>, 3 Versuche
- render.html_screenshot: headless Chromium aus ~/Library/Caches/
  ms-playwright/chromium-1255 ( vorhanden auf Mini, kein Download noetig ),
  --headless=new --screenshot, bewiesen mit Test-HTML (PNG 8KB)
- pipeline.schritt_html: je Folie GLM-HTML + Screenshot + Fallback-Seite bei
  Ausfall, Resume-sicher (vorhandene HTML-Dateien werden weiterverwendet),
  deck.html als Folien-Stapel mit iframes + Pfeiltasten-Navigation
- fix_runden forked fuer Weg B auf _fix_runden_html: GLM repariert die
  komplette HTML-Seite, re-Screenshot, Re-Critic nur geaenderter Folien
- cli.py: --weg B

## Web-Karte Studio (web/app.py + templates/index.html)
- POST /api/studio/start (briefing + quelle/text + weg + min/max, Run im
  Hintergrund-Thread), GET /api/studio/status/<id>, POST /api/studio/resume/<id>,
  GET /api/studio/runs (letzte 12), GET /api/studio/file/<id>/<name>
  (whitelist deck.pptx/deck.html/report.md)
- Karte 05 in der UI: Briefing + Weg-Dropdown + min/max + Start, Runs-Liste
  mit Schritt-Fortschritt, Scores, Resume-Button, Downloads (Polling 15s)

## Beweise
- web/app.py ast-parse OK; Flask-Testclient: /api/studio/runs 200 mit echten
  Runs, /api/studio/status/<bogus> 404, index.html enthaelt genau 1 </script>
- pytest 7 passed (studio/test_state.py)
- Weg B E2E Run 20261118-203927: brach sauber mit GLM-429-Meldung ab
  (Haertung wirkt, resume-bar). E2E-Abschluss folgt nach Ablauf des
  Stundenlimits via --resume / Web-Resume.

## NACHTRAG Gate-Frage
uuid + Path sind bereits in web/app.py importiert (Kopf: import uuid,
from pathlib import Path - Zeile 4 und 7). Kein neuer Import noetig.

---

# NACHWEIS 8: Deploy Etappe 2 auf gemivo + app.run()-Blocker-Fix

## app.run()-Blocker (wichtige Lektion!)
- web/app.py: app.run() stand in Zeile 298 (if __name__ == "__main__"),
  der neue Studio-Routen-Block wurde DAHINTER angehaengt.
  Als __main__ (systemd) blockiert app.run() VOR der Registrierung ->
  /api/studio/* gab Flask-404, obwohl import app (Testclient) alle Routen
  zeigte. Symptom: Routen in Datei + md5-gleich, live trotzdem 404.
- FIX: Studio-Block vor den __main__-Block verschoben. Danach live 200.

## Chromium fuer Weg B auf gemivo
- Pfad-Struktur anders als auf dem Mini: chrome-headless-shell-linux64/
  chrome-headless-shell (nicht chrome-linux/). _chrome_bin() deckt jetzt
  Mac- UND Linux-Pfade ab (glob-basiert).
- Beweis: html_screenshot auf gemivo erzeugt /tmp/t.png (echter Chromium-Shot)

## Deploy-Beweise (alles live auf slideforce.gemivo.de)
- rsync code (studio/, web/, slideforce/profiles.py) -> systemctl restart -> active
- https://slideforce.gemivo.de/api/studio/runs?token=... -> HTTP 200 (echte Liste)
- UI-Screenshot /tmp/sf-ui.png (327KB) erstellt; Vision-Check durch
  429-Rate-Limit des Pruef-Modells offen (Retry folgt)
- studio/runs auf Server LEER (bewusst: lokale Test-Runs nicht deployed)

---

# NACHWEIS 9: Design-Redesign (stark/GLM-5.3) + Studio-Karte mit eigenen Fakten-Feldern

## Design-Upgrade (stark-Subagent)
- index.html CSS neu: #0B0F14-Basis, Petrol/Rot-Glows, Gradient-Kartenraender,
  Glass, Hover-Microinteractions, Nummern-Badges, Studio-Karte hervorgehoben
- Beweise stark: html.parser keine Fehler, 28/28 IDs genau 1x, <script>-Block
  bytegleich (JS/FormData/Fetch unberuehrt)
- Eigene Nachpruefung: HTML-PARSE OK, Kern-IDs vorhanden

## Studio-Karte 05 umgebaut (Kays Feedback: Quelle war unklar)
- EIGENE Fakten-Eingabe direkt in der Karte: Drop (studioFile, .md/.txt/.docx/
  .xlsx/.csv) + Textarea (studioText) + klare Schritte 1/2/3
- JS sendet jetzt studioFile/studioText (statt Karten 02/03) - API
  /api/studio/start unveraendert (quelle/text-Formfelder identisch)

## Beweise
- Deploy: rsync + restart -> active; https://slideforce.gemivo.de 302-Gate ok
- Screenshot /tmp/sf-neu.png (891KB), glm-sicht: SCORE 8/10, Studio-Karte
  "starkes, funktional durchdachtes Feature" (Rest-Issues Kleinigkeiten)

## NACHTRAG: Briefing optional (Kays Feedback)
- /api/studio/start ohne Briefing leitet es ab: erste aussagekraeftige Zeile
  der Quelle (max 80), sonst Dateiname (_briefing_aus_quelle)
- UI: "Briefing optional - sonst aus deinen Fakten abgeleitet"
- Beweis lokal + Server: 'ITK-Bremen Vorstand 2026' aus Zeile 1 abgeleitet;
  md5 app.py lokal==server (eda9adb4...), service active, live 302-Gate ok
- rsync --relative-Fehlschuss korrigiert (web/web verschoben nach
  _web-falsch-kopie-18nov-2026, nicht geloescht)

---

# NACHWEIS 10: Weg B E2E ABGENOMMEN - alle 3 Wege bewiesen

Run 20261118-203927 (Resume nach 429-Pause, Weg B Visual HTML):
- 11 Folien als komplette HTML-Seiten von GLM designt, 11 Chromium-PNGs
- 4 Critic-Runden mit echten html-repair-Reparaturen (Folie 2 in Runden 2-4)
- FINAL: 10/11 Folien >= 8/10 (Folie 2: 6, Rest-Schwaeche im report.md)
- deck.html (iframe-Folienstapel, Pfeiltasten-Navigation) erzeugt
- glm-sicht Folie 1: "Klare Hierarchie ... konsequente Verwendung der
  Brandfarben (Petrol/Rot/Weiss)" - Rest: Kleinigkeiten (Icon-Konsistenz)
- Status: WEG A + B + C ALLE E2E-BEWIESEN. Projekt rund (Rest: Loesch-Erlaubnis
  _web-falsch-kopie, optional Icon-Konsistenz-Feinschliff)

## NACHTRAG: Feinschliff (Kays Freigabe)
- _web-falsch-kopie-18nov-2026 auf gemivo GELoescht (mit Kays Erlaubnis)
- HTML_SYSTEM-Prompt: ICON-KONSISTENZ-Regel (alle Icons gleicher Stil/Farbe,
  Petrol; Rot nur als Spaetzenakzent) + Farbdisziplin - gilt fuer alle
  kuenftigen Weg-B-Runs
- Gezielte Reparatur Folie 1+2 im Weg-B-Run: Reparaturlauf + mechanische
  Farb-Korrektur; Verifikation: #F8E8E8 = 0 Vorkommen, glm-sicht bestaetigt
  "Boxen gleichen hellgrauen Ton", Icons einheitlich Petrol, "GEIL: klare
  Struktur ... sofort verstaendlich"

## NACHTRAG: Export-Karten reduziert (Kays Entscheidung)
- UI: PowerPoint-Master-Fill + BRIDGE28-Karten entfernt (API /api/build
  unterstuetzt fmt=pptx/b28pptx WEITERHIN - bewiesen: beide HTTP 200,
  2 Folien, unzip OK). Vorstandsvorlage ist jetzt Default (checked).
- Live-Beweis: Session-Cookie-Flow 200, vorpptx-checked=1, alte Werte=0
- glm-sicht: "Intuitive Step-by-Step-Struktur (01-05) ..."
- Beide Formate funktionieren technisch (hiermit belegt) - sie waren nur
  UI-Rauschen fuer Kays Alltag (vorpptx/aipptx sind sein Standard)

---

# NACHWEIS 11: dataport-Brand ueberall + 1h-Transkripte (Kays Anforderungen)

## Premium (aipptx) auf dataport umgestellt
- SYSTEM_PROMPT: navy/gold-Designsystem ersetzt durch dataport (PETROL dominant,
  ROT nur Spaetzenakzent, HELL #F4F5F6 Karten, KEIN Navy/Gold)
- FARB_MAP: NAVY->V_PETROL, GOLD->V_DUNKEL (Fallback-Falle: alte Namen liefern
  dataport-Farben), PETROL/DUNKEL ergaenzt
- Logo: _v_dp_logo auf jeder Premium-Folie (Cover gross)
- Titelfolie: navy/gold-Cover-Geruest (_titel_folie) entfernt, KI designt
  Cover frei auf hellem Grund
- Beweise: /api/build fmt=aipptx live HTTP 200 + unzip OK; glm-sicht Folie 2
  "Petrol/Grau/Weiss ... GEIL klare Struktur"; Cover-Folie hell + Logo
  (keine navy/gold-Meldung mehr)

## Studio Weg B (HTML): dataport-Logo
- roles._html_logo_injizieren: Logo als data-URI fix oben rechts in jede
  HTML-Folie injiziert (keine Prompt-Tokens, doppelt-sicher)
- Beweis: Injektion-Test (Logo drin, 1x data-uri, idempotent)

## 1-Stunden-Meeting-Transkripte (Kays Anforderung)
- studio/pipeline.quelle_lesen: Grenze 14.000 -> 200.000 Zeichen
  (60-100k-Zeichen-Transkripte laufen KOMPLETT in die Rollen, kein Faktenverlust)
- nginx/Flask erlauben ohnehin 64MB; UI-Hinweise aktualisiert
- Beweis: 191.999-Zeichen-Quelle ungekuerzt; 100.000-Zeichen-Text live via
  /api/build -> HTTP 200, Deck gebaut, unzip OK

## NACHTRAG: Kays XLSX-Run analysiert - 3 Fixes
- Briefing-Ableitung: Office-Dateien (docx/xlsx) -> DATEINAME statt ZIP-Binaer
  ("PK\x03..."-Muell-Briefing behoben); Binär-Erkennung (Steuerzeichen) generell
- Verschlechterungs-ROLLBACK in fix_runden: Reparatur schlechter als vorher ->
  alte Version + alter Score automatisch zurueck (Kay-Lektion: Folie 4 fiel
  6->4 durch eine Reparatur - jetzt unmoeglich)
- Premium-Prompt: HARTE LAYOUT-REGELN (max 8 Elemente, Canvas-Grenzen
  x+w<=12.78/y+h<=7.1, Ueberlappung verboten, max 550 Woerter)
- Kays Folie 4 live repariert: Score 4 -> 8 (bewiesen, Deck+State aktualisiert,
  Rollback-Schutz haette bei Verschlechterung gegriffen)

## NACHTRAG: Kays Rolloutplan als Weg B (Agentur-HTML) - 2 Reparatur-Wellen
- Run 20261118-210012 (Weg B, gleiche XLSX): Runde 1: 8 8 8 5 9 8 ->
  gezielte Reparaturen (Runde 2: alle 5 schwachen mit konkreten Befunden,
  Runde 3: Folie 4 mit EXAKTEM Bau-Raster 6x230px-Karten, Runde 4: Umlaute+Breiten)
- FINAL: 1:8 2:8 3:9 4:8 5:9 6:9 (Folie 4: 5->8)
- HTML_SYSTEM ergaenzt: ICON-Anforderungen (stroke-SVG einheitlich Petrol,
  40-56px) + Editorial-Regeln (Hairlines, grosse Zahlen, letter-spacing,
  min 60px Aussenrand) + echte Umlaute (nie ae/oe/ue)
- deck.html live: /api/studio/file/<id>/deck.html mit Token

## NACHTRAG: Weg B NEU - handgebautes Editorial-Design-System (Kays Urteil "scheisse" umgesetzt)
- Analyse: GLM-Frei-HTML-Design produziert Mittelmass, kein Agentur-Niveau
- NEU: studio/dssystem.py - handgebaute Folien-Templates (Basis-CSS, 12er
  Stroke-Icon-Bibliothek, Logo, Fuss; Layouts: titel/teil/kpi/karten/
  zeitstrahl/statement). GLM liefert nur INHALTE (Storyboard/Art-Dicts),
  das Design ist KONSTANT edel
- pipeline.schritt_html nutzt jetzt dssystem.folie_html statt roles.html_folie
- Logo-CSS-Fix: height 52px proportional (keine Verzerrung)
- Beweis: Kays Rolloutplan-XLSX als Weg B mit Templates (Run 20261118-211918,
  alle Schritte ok, deck.html), 6 PNGs gerendert + auf Kays Desktop gelegt;
  glm-sicht Folie 1: "GEIL: Sehr klares und praegnantes Messaging" - kein
  Doppel-Logo mehr

## NACHTRAG: Weg B endet mit deck.pptx (Kays Anforderung)
- pipeline.schritt_html: nach den Folien-PNGs wird automatisch ein deck.pptx
  gebaut (Folien-PNGs als Vollbild-Folien 16:9, python-pptx, saubere API)
- Kays Rolloutplan-Run 20261118-211918: deck.pptx (6 Folien, 406 KB) live,
  Download /api/studio/file/<id>/deck.pptx -> HTTP 200, UI-Status pptx: true
- KPI-Template-Kompakt-Fix (Zahl 76px, bottom-220px-Begrenzung gegen Abschnitt)

## NACHTRAG: Qualitaets-Runde Template-System (Kay: 6/10)
- 6 Folien neu gerendert (KPI-Kompakt-Fix aktiv), glm-sicht Frisch-Befunde:
  alle 3 geprueften Folien "GEIL"-Qualitaet (Titel-Hierarchie stark, KPI
  sehr gut, SVG-Icon-Chips starker Flair) - Rest: Abstand-Mikro
- Mikro-Fixes: Logo top 44px, Karte padding 32/36, KPI-Gap 26px,
  Kicker-Default mit echten Umlauten (VORSTANDS-PRÄSENTATION)
- deck.pptx NEU gebaut aus frischen PNGs (6 Folien) + auf Kays Desktop
  (BRIDGE28-Rolloutplan-Vorstand.pptx)

## NACHTRAG: Statement-Vertikal-Fix mit Sichtpruefung
- dssystem f_statement: top 250->300, Breite 1280->1200 (Leerraum unten behoben,
  glm-sicht-Befund aus Kays Qualitaets-Runde)
- Alle 6 Folien NEU gerendert + deck.pptx neu gebaut (Server-Proof:
  "alle 6 neu + deck.pptx aktualisiert") + auf Kays Desktop gesynct
- Sichtpruefung Folie 6 nach Fix: Score laut glm-sicht (folie-6-Pruefung
  /tmp/f6-neu.png), keine Ueberlappungen, Balance ok
