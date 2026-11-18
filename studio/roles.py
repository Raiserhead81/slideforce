"""Studio-Rollen: Presentation Director, Story Architect, Art Director,
Visual Critic - jede Rolle EIN GLM-5.3-Aufruf (bzw. Vision-Call beim Critic).

Der Website Operator baut deterministisch (kein GLM): studio/webop.py
nutzt slideforce.profiles.build_vorlage DIREKT im venv (kein HTTP).
Alle Prompts erzwingen reines JSON; Validierung + 1 Feedback-Retry.
"""
import time

from . import glm
from slideforce import ai_design as AI

HEUTE = time.strftime("%d.%m.%Y")

# ---------------------------------------------------------------- Director
DIRECTOR_SYSTEM = """Du bist Presentation Director einer Praesentations-Agentur und orchestrierst die Deck-Produktion. Du planst Struktur und Dramaturgie, desigst NICHT selbst. Dein Plan ist die Grundlage fuer Story Architect und Art Director."""

_DIRECTOR_SCHEMA = """Gib AUSSCHLIESSLICH dieses JSON aus (kein Markdown, keine Erklaerung):
{"zielgruppe":"...","anlass":"...","kernbotschaft":"EIN Satz","dramaturgie":"Spannungsbogen in 2-3 Saetzen",
 "teile":["Titel Teil 1","Titel Teil 2"],"folienzahl":N,
 "fokusthemen":[{"thema":"...","gewicht":1-3}],"risiken":["..."],"editorial_note":"..."}
Regeln:
- folienzahl N liegt ZWISCHEN den genannten min/max-Grenzen (inklusive Titel- und Teilfolien).
- teile: 2-3 inhaltliche Teile fuer die INHALT-Sidebar.
- kernbotschaft: die eine Aussage, die der Vorstand mitnehmen soll.
- focusthemen gewichtet nach Relevanz fuer DIESEN Vorstand; nichts erfinden, nur aus Briefing/Quelle."""


def director(briefing, quelle_text, ziel_min, ziel_max):
    user = (f"BRIEFING:\n{briefing}\n\nQUELLE (Rohmaterial, gekuerzt):\n"
            f"{quelle_text}\n\nZIEL: Folienzahl zwischen {ziel_min} und {ziel_max}.")
    d = glm.chat_json(DIRECTOR_SYSTEM + "\n\n" + _DIRECTOR_SCHEMA, user,
                      max_tokens=2500)
    if not (isinstance(d, dict) and d.get("folienzahl")):
        return None
    try:
        d["folienzahl"] = int(d["folienzahl"])
    except (TypeError, ValueError):
        return None
    if not (ziel_min <= d["folienzahl"] <= ziel_max):
        d["folienzahl"] = min(max(d["folienzahl"], ziel_min), ziel_max)
    return d


# ---------------------------------------------------------------- Story
STORY_SYSTEM = """Du bist Story Architect einer Praesentations-Agentur: Du entwicklest das Storyboard mit Action Titles und trennst strikt FAKTEN von ANNAHMEN.
- Action Title = vollstaendiger Aussage-Satz mit Subjekt und Richtung (NICHT "Status Migration", SONDERN "Migration erreicht 93 Prozent und liegt im Plan").
- FAKTEN stehen auf den Folien: jede Zahl, jeder Termin MUSS aus der Quelle stammen - niemals erfinden oder glaetten.
- ANNAHMEN (Interpretationen, Hochrechnungen, fehlende Belege) kommen NICHT auf die Folie, sondern ins Feld "annahmen" (erscheint nur im Report/Notizen).
- Jede Folie traegt GENAU EINE Kernbotschaft.
- ARGUMENT-SPINE (Minto): Deck folgt einem Bogen - Situation (was gilt) -> Komplikation (was fehlt/bedroht) -> Aufloesung (was wir tun/tun haben). Kapitel-Trenner markieren die Bogen-Stationen.
- GHOST-DECK-TEST (PFLICHT vor Ausgabe): Lese nur die Titelle in Reihenfolge. Sie muessen ALLEIN die komplette Geschichte erzaehlen. Tun sie das nicht: Titel schaerfen oder Folien umordnen, bevor du antwortest.
- TEXT-DISZIPLIN: max 40 Woerter Fliesstext je Inhaltsfolie, 3-5 punkte je Folie (mehr = Folie splitten), telegraphische Sprache ohne Fuellwoerter."""


def _STORY_SCHEMA(ziel_min, ziel_max):
    return f"""Gib AUSSCHLIESSLICH dieses JSON aus (kein Markdown):
{{"deck_titel":"<Marke>: <Untertitel>","untertitel":"...","meta":"Stand {HEUTE} \u00b7 Vorstand",
 "annahmen":["global nicht auf Folien belegbare Annahme",...],
 "folien":[
  {{"nr":1,"rolle":"titel","titel":"<Marke>: <Untertitel>","untertitel":"...","meta":"..."}},
  {{"nr":2,"rolle":"teil","titel":"<Teiltitel>"}},
  {{"nr":3,"rolle":"kpi","titel":"<Action Title>","kicker":"KURZLABEL","lead":"eine petrolfarbene Leitzeile",
    "zahl":"<groesster Wert>","label":"<Label zur Zahl>","subs":[["93 %","abgeschlossen"],...],
    "punkte":["<Kartentitel>: <Aussage>",...],"annahmen":["..."]}},
  {{"nr":4,"rolle":"content","titel":"<Action Title>","kicker":"...","lead":"...",
    "punkte":["<Kartentitel>: <Aussage>",...],"annahmen":["..."]}},
  {{"nr":5,"rolle":"statement","titel":"<Action Title>","botschaft":"<die eine grosse Aussage, 1-2 Saetze>","zusatz":"<einordnung>"}},
  {{"nr":6,"rolle":"tabelle","titel":"<Action Title>","kicker":"...","kopf":["Spalte1","Status"],"zeilen":[["...","gruen"],...]}},
  {{"nr":7,"rolle":"zeitstrahl","titel":"<Action Title>","heute":"JJJJ-MM-TT","meilensteine":[["JJJJ-MM-TT","Kurzname","fertig|kritisch|offen"],...]}}
 ]}}
Regeln:
- GENAU {ziel_min}-{ziel_max} Folien: Folie 1 ist IMMER rolle=titel, danach 2-3 rolle=teil als Kapitel-Trenner, der Rest verteilt auf kpi/content/statement/tabelle/zeitstrahl.
- Mind. 1 kpi-Folie (substanzielle Zahl aus der Quelle), hoechstens 1 zeitstrahl, hoechstens 1 tabelle, hoechstens 1 statement.
- punkte: max 6 pro Folie, jeder als "Kurztitel: Aussage-Satz" (max 160 Zeichen).
- tabellen-Statuszellen nutzen diese Worte (werden farbig): gruen, gelb, rot, kritisch, am limit, in arbeit, offen.
- subs: 2-3 [wert, bezeichnung]-Paare zur KPI-Zahl.
- Nur belegbare Fakten auf Folien; alles andere ins jeweilige "annahmen"."""


ROLLEN = {"titel", "teil", "kpi", "content", "statement", "tabelle", "zeitstrahl"}


def story(briefing, plan, quelle_text, ziel_min, ziel_max):
    plan_txt = "\n".join(f"{k}: {v}" for k, v in (plan or {}).items()
                         if not isinstance(v, (list, dict)))
    if plan and plan.get("teile"):
        plan_txt += "\nteile: " + " | ".join(str(t) for t in plan["teile"])
    user = (f"BRIEFING:\n{briefing}\n\nDIRECTOR-PLAN:\n{plan_txt or '-'}\n\n"
            f"QUELLE (Rohmaterial):\n{quelle_text}")
    return glm.chat_json(STORY_SYSTEM + "\n\n" + _STORY_SCHEMA(ziel_min, ziel_max),
                         user, max_tokens=9000)


def validiere_storyboard(sb, ziel_min, ziel_max):
    """Storyboard gegen Kernregeln pruefen. Liste von Fehlerstrings (leer = ok)."""
    fehler = []
    if not isinstance(sb, dict) or not isinstance(sb.get("folien"), list):
        return ["storyboard.folien fehlt/keine Liste"]
    n = len(sb["folien"])
    if not (ziel_min <= n <= ziel_max):
        fehler.append(f"Folienzahl {n} ausserhalb [{ziel_min}, {ziel_max}]")
    rollen = [str(f.get("rolle", "")).lower() for f in sb["folien"]
              if isinstance(f, dict)]
    if rollen and rollen[0] != "titel":
        fehler.append("Folie 1 ist nicht rolle=titel")
    if rollen.count("titel") > 1:
        fehler.append("mehr als eine titel-Folie")
    for r in rollen:
        if r not in ROLLEN:
            fehler.append(f"unbekannte rolle: {r}")
    return fehler


# ---------------------------------------------------------------- Art
ART_SYSTEM = """Du bist Art Director einer Praesentations-Agentur und erreichst Editorial-Niveau: ruhig, hell, praezise, vorstandstauglich. Du setzt das gegebene Storyboard 1:1 in ein FEDESIGN um - du aenderst Aussagen NICHT, du schaerfst nur Formulierung, Reihenfolge und visuelle Betonung (maximal 10 % Umformulierung, Zahlen und Fakten bleiben exakt).

DESIGN-BRAND DATAPORT (FEST, nicht verhandelbar):
- Petrol #39756F (dominant: Zahlen, Leads, Tabellenkopf), Dunkelgrau #39424A (Texte/Titel),
  Rot #9E292B (Akzent, Statement-Balken, INHALT-Marker), Karten #F4F5F6,
  Tints #FBF0DC (goldene Hinweis-Baender) / #F8E8E8, Weiss #FFFFFF Grund.
- HELLE Vorstandsvorlage (Sidebar, schwebende Titel, Karten) - NICHT dunkel/navy/gold.
- Typo Arial; grosse petrolfarbene Kennzahlen; Kartentitel 14pt bold; Kicker klein grau.

BAU-VOKABULAR (Slide-Dicts, vom Renderer deterministisch gezeichnet; du gestaltest NUR Daten):
kind/title/subtitle/meta/kicker/lead/bullets/hinweis/notes konkret je Muster:
- titel:  {{"kind":"title","title":"<Marke>: <Untertitel>","subtitle":"...","meta":"Stand .. \u00b7 Vorstand","teile":["01|Teil 1","02|Teil 2"]}}
- teil:   {{"kind":"section","title":"...","subtitle":"...","meta":"optional"}}
- kpi:    {{"kind":"content","kicker":"...","title":"<Action Title>","lead":"eine Zeile petrol","zahl":"93 %","label":"Migrationsstand",
           "bullets":[[0,"479|Anschluesse gesamt"],[0,"Milestone M2: Umstellung Kernnetz abgeschlossen"],[0,"Risiko: Lieferketten Engpass Haerder"]],"hinweis":"optional Prefix: Text"}}
          bullets mit "wert|bezeichnung" werden Unterwerte der KPI-Karte (max 3), Karten ohne "|" werden Punkt-Karten (max 4).
- content:{{"kind":"content","kicker":"...","title":"<Action Title>","lead":"...","bullets":[[0,"Kurztitel: Aussage"],...],"hinweis":"..."}}
          max 6 Karten; **Aussage** als petrol-Highlight moeglich.
- statement: {{"kind":"content","kicker":"...","title":"...","botschaft":"...","zusatz":"..."}}
- tabelle: {{"kind":"content","kicker":"...","title":"...","table":[["Bereich","Status"],["Netz","gruen"]]}}, max 9 Zeilen inkl. Kopf;
          Statuszellen mit diesen Worten werden farbige Pillen: gruen, gelb, rot, kritisch, am limit, in arbeit, offen.
- zeitstrahl: {{"kind":"content","kicker":"...","title":"...","heute":"JJJJ-MM-TT","zeitstrahl":[["JJJJ-MM-TT","M1","fertig"],...]}} (min 3, max 7 Meilensteine).
- jede Folie: optional "notes" (Sprechnotiz).

EDITORIALE HART-REGELN (Critic prueft genau das):
- Action Titles HOECHSTENS 45 Zeichen, wenn ein lead gesetzt ist (sonst max 88) - immer als VOLLSTAENDIGER, sinnvoll endender Satz (nie mitten im Wort abbrechend).
- KEIN "**" in title/subtitle/kicker/lead/label/botschaft/nur in Karten-Texten (bullets).
- Deck-Titelfolie: title max 48 Zeichen ("Marke: Kurztitel"), subtitle max 100.
- tabelle: 4-7 Zeilen inkl. Kopf, Spalten wie Risiko/Massnahme/Verantwortlicher/Status, wenn der Stoff das hergibt.
- zahl max 12 Zeichen (darf nie umbrechen); Tabellenzellen max 30 Zeichen mit VOLLSTAENDIGEN Zahlen ("85.000 Euro", nie "85.0").
- statement NUR fuer eine einzige grosse Botschaft (keine Aufzaehlung!); botschaft ANDERS und STAERKER formulieren als der Action Title (kein Duplikat!); bei Aufzaehlungen oder duennem Stoff content mit Karten nutzen.
- content-Folien: IDEALERWEISE 4-6 Karten ("Kurztitel: Aussage"), nur bei knappem Stoff 3; Kartentitel max 40 Zeichen, jeder Karten-Text SUBSTANZIELL (12-25 Woerter, nie nur 2-3 Woerter). Die Folie muss die Flaeche fuellen.
- zeitstrahl: 3-5 Meilensteine, moeglichst gleichmaessig ueber das Jahr verteilt (nie zwei im selben Monat), Label max 12 Zeichen.
- Jeder Wert/Kennzahl erscheint max. EINMAL pro Folie (keine Redundanz zwischen KPI-Karte und Punkt-Karten).
- KPI-Reihe (2-3 Zahlen): nur die ERSTE Karte 2 subs (Werte max 12 Zeichen), die folgenden ohne; Sub-Werte nie laenger als 8 Zeichen.
- lead: eine Zeile, max 80 Zeichen, petrol, keine Aufzaehlungen.
- RAUM-DISZIPLIN: WEISSRAUM ist Qualitaets-Signal - niemals jede Flaeche fuellen. Lieber 4 Karten grosszuegig als 6 gequetscht. Elemente DUERFEN SICH NIE UEBERLAPPEN (Critic faengt das immer). 
- KEIN DEKO: Linien/Baender/Felder nur mit Informationszweck (Gruppierung, Betonung, Status). Farbe lenkt Aufmerksamkeit auf den Kernbefund - alles andere bleibt neutral grau/dunkel.
- ANTI-SLOP: keine erfundenen Farben (nur die Brand-Palette) · keine Deko-Icons/Emojis · keine Deko-Verlaeufe · keine Deko-Kennzahlen ("data slop") · jedes Element verdient seinen Platz - Leere wird mit Komposition geloest, nie mit Fuellinhalt.
- SELF-SUFFICIENT-TEST: Jede Folie muss ohne Praesentierer verstaendlich sein - Kernbefund steht auf der Folie, nicht nur in der Sprechnotiz.
- Nicht zutreffende Felder WEGLASSEN - niemals null/None/"-" als Wert eintragen."""


_ART_SCHEMA = """Gib AUSSCHLIESSLICH dieses JSON aus:
{"designsystem":{"leitidee":"ein Satz","prinzipien":["...","...","..."]},
 "folien":[ <Slide-Dicts, REIHENFOLGE GENAU wie Storyboard, eine pro Storyboard-Folie> ]}
Die folien-Liste hat EXAKT so viele Eintraege wie das Storyboard."""


def art(briefing, storyboard):
    import json as _json
    user = (f"BRIEFING:\n{briefing}\n\nSTORYBOARD (verbindlich):\n"
            + _json.dumps(storyboard, ensure_ascii=False))
    return glm.chat_json(ART_SYSTEM + "\n\n" + _ART_SCHEMA, user, max_tokens=12000)


# ---------------------------------------------------------------- Critic
CRITIC_SYSTEM = """Du bist Visual Critic einer Praesentations-Agentur und bewertest GERENDERTE Folien einer hellen Dataport-Vorstandsvorlage (Petrol/Grau/Rot, Karten auf Weiss, INHALT-Sidebar, Arial).
Bewerte streng wie ein Art Director im Abnahmemeeting:
- 9-10: Agenturniveau - Editorial, ruhig, perfekt balanciert, alles lesbar, nichts abgeschnitten.
- 7-8: solide, aber mit klaren Schwaechen (Unbalance, Textwust, schwache Hierarchie).
- <7: echte Maengel (abgeschnittener/ueberlappender Text, ueberfuellte oder leere Flaechen, kaputte Optik, inkonsistentes Design).
Text, der ausserhalb seiner Karte oder ueber den Rand laeuft, ist IMMER ein Makel. Ueberlappende Elemente sind IMMER ein Makel.
Zusaetzliche harte Checks (jeweils Makel wenn verletzt):
- ACTION-TITLE-TEST: Titel ist ein vollstaendiger Aussage-Satz mit Subjekt und Richtung? Ein nacktes Themen-Label ("Ergebnisse", "Zeitplan") ist ein Makel.
- SELBSTTRAGEND-TEST: Versteht man den Kernbefund der Folie ohne Praesentierer? Fehlt die Annotation am Kernelement, ist ein Makel.
- WEISSRAUM-TEST: Ist die Folie ueberfuellt (>6 Inhaltszellen) oder unbalanciert (eine Ecke leer, Rest voll)?
- DEKO-TEST: Gibt es Linien/Baender/Farbe ohne Informationszweck?"""


def critic(png_path, nr, titel, muster):
    user = (f"Gerenderte Folie {nr} (Muster: {muster}, Action Title soll sein: "
            f"\"{titel}\"). Bewerte die FOLIE wie beschrieben.")
    d = glm.vision_json(CRITIC_SYSTEM + """

Gib AUSSCHLIESSLICH dieses JSON aus:
{"score":0-10,"schwaechen":["konkrete, behebbare Schwaeche",...],"fix":"EINE konkrete Anweisung an den Art Director (inhaltlich/Daten-Ebene, KEIN XML/KEINE Koordinaten) oder ""}""",
                         user, png_path, max_tokens=1800)
    if not isinstance(d, dict):
        return {"score": 0, "schwaechen": ["Critic-Antwort unbrauchbar"], "fix": ""}
    try:
        d["score"] = int(round(float(d.get("score", 0))))
    except (TypeError, ValueError):
        d["score"] = 0
    d["score"] = max(0, min(10, d["score"]))
    d.setdefault("schwaechen", [])
    d.setdefault("fix", "")
    return d


# ---------------------------------------------------------------- Repair
def art_repair(briefing, folie_slide_dict, critic_ergebnis, nr):
    """Eine schwache Folie ueberarbeiten: Critic-Feedback -> neues Slide-Dict."""
    import json as _json
    system = ART_SYSTEM + """

Du reparierst GENAU EINE Folie anhand der Critic-Kritik. Gib AUSSCHLIESSLICH das
korrigierte Slide-Dict als JSON aus (nur diese eine Folie, gleiche Struktur).
Fakten und Zahlen bleiben exakt erhalten; du darfst kuerzen, umformulieren,
Karten neu verteilen (max 6), das Muster wechseln (kpi/content/statement/
tabelle/zeitstrahl) oder Kicker/Lead schaerfen."""
    user = (f"BRIEFING: {briefing}\n\nFOLIE {nr} (aktuelles Design):\n"
            + _json.dumps(folie_slide_dict, ensure_ascii=False)
            + f"\n\nCRITIC (score {critic_ergebnis.get('score')}/10):\n"
            + "Schwaechen: " + "; ".join(critic_ergebnis.get("schwaechen") or [])
            + f"\nFix-Anweisung: {critic_ergebnis.get('fix') or '-'}")
    d = glm.chat_json(system, user, max_tokens=3000)
    return d if isinstance(d, dict) else None


# ---------------------------------------------------------------- Hybrid SVG (Weg C)
HYBRID_SYSTEM = """Du bist Dataviz-Infografiker einer Praesentations-Agentur. Du baust EINE
Infografik als reines SVG (viewBox="0 0 1200 900", font-family Arial) im Brand der
hellen Dataport-Vorstandsvorlage: Grund #FFFFFF, Karten #F4F5F6, Petrol #39756F,
Grau #39424A, Rot #9E292B (nur Akzent), Tints #F8E8E8/#FBF0DC.
Regeln: keine externen Bilder/Fonts/Scripts, kein CSS-<style>-Import, Text NICHT
abschneiden (textLength nur mit lengthAdjust), Kernzahl mindestens 160px im
1200er viewBox, Beschriftungen mindestens 40px, Zahlen exakt uebernehmen, max 5
Datenelemente, ruhig und vorstandstauglich. gib nur das SVG-Element selbst aus."""

_HYBRID_SCHEMA = """Gib AUSSCHLIESSLICH dieses JSON aus:
{"svg":"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 1200 900'> ... </svg>"}"""


def hybrid_svg(briefing, folie_slide_dict, design, nr):
    """GLM-SVG-Infografik fuer eine Folie (Weg C Hybrid). SVG-String oder None.

    Robust gegen GLMs schwankendes Antwortformat: JSON-Wrapper nur Erstversuch,
    sonst <svg>...</svg> direkt per Regex aus dem Roh-Text ziehen. 3 Call-Versuche.
    """
    import json as _json
    import re as _re
    user = (f"BRIEFING: {briefing}\n\nDESIGNSYSTEM (Leitidee): "
            + _json.dumps((design or {}).get("designsystem") or {}, ensure_ascii=False)
            + f"\n\nFOLIE {nr} (Inhalte verbindlich, Zahlen exakt):\n"
            + _json.dumps(folie_slide_dict, ensure_ascii=False)
            + "\n\n" + _HYBRID_SCHEMA)
    system = HYBRID_SYSTEM
    for _versuch in range(3):
        txt = glm.chat(system, user, max_tokens=8000, timeout=300)
        if txt:
            d = AI._extract_json(txt)            # sauberer JSON-Weg
            svg = d.get("svg") if isinstance(d, dict) else None
            if not (isinstance(svg, str) and svg.strip().startswith("<svg")):
                m = _re.search(r"<svg[\s\S]*?</svg>", txt)   # roher SVG-Weg
                svg = m.group(0) if m else None
            if isinstance(svg, str) and svg.strip().startswith("<svg"):
                return svg
            user2 = user + "\n\nWICHTIG: Antworte NUR mit dem JSON {\"svg\": \"...\"}."
        else:
            user2 = user
        if _versuch == 1:
            system = HYBRID_SYSTEM + "\nDu gibst NUR das JSON-Objekt aus, ohne Prosa."
            user = user2
    return None


# ---------------------------------------------------------------- Weg B: Visual HTML
HTML_SYSTEM = """Du bist Art Director UND Frontend-Entwickler einer Praesentations-Agentur.
Du designt EINE Folie als komplette, selbststaendige HTML-Seite auf Editorial-Niveau:
ruhig, hell, vorstandstauglich, exakt im Brand der Dataport-Vorstandsvorlage.
Harte Anforderungen:
- komplettes Dokument: <!doctype html><html><head><meta charset="utf-8">
  <style>...</style></head><body>...</body></html>
- body: width:1600px; height:900px; margin:0; overflow:hidden (Folie, kein Scroll)
- Farben: Grund #FFFFFF, Karten #F4F5F6, Petrol #39756F, Grau #39424A,
  Rot #9E292B nur als Akzent, Tints #F8E8E8/#FBF0DC, Text min 20px
- font-family Arial, KEINE externen Ressourcen (kein CDN, kein Webfont, kein Bild,
  keine data-URIs), alles CSS inline im <style>-Block
- Typo-Hierarchie (Kicker klein/Sperrbuchstaben, Titel gross, klare Karten),
  grosszuegiger Weissraum, Zahlen exakt uebernehmen, NICHTS abschneiden
- dezente SVG-Infografik inline erlaubt (gleiche Farbwelt)
- ICONS/SYMBOLE ERWUENSCHT: jede Karte/jeder Kernpunkt bekommt ein kleines
  Inline-SVG-Icon (stroke-basiert, 2px Strichstaerke, rund 40-56px, EINfarbig
  Petrol #39756F, gleicher Stil ueber die ganze Folie). Nutze klare Metaphern
  (Pfeil, Standort-Pin, Uhr,checks, Anker, Zollstock, Zahnrabd). Kein Emoji.
- EDITORIAL-FEINSCHLIFF: feine Hairlines (1px, #D8DEE2) zur Gliederung, grosse
  dominante Zahlen (96-140px Petrol), Kicker mit letter-spacing 0.2em, max 2
  Schriftgraezen-Welten pro Karte, grosszuegiger Weissraum (min 60px Aussenrand)
- ICON-KONSISTENZ: wenn Icons genutzt werden, dann ALLE im selben Stil
  (gleiche Strichstaerke, gleiche Groesse) und ALLE in EINER Farbe
  (Petrol); Rot bleibt ausschliesslich dem einzelnen Spaetzenakzent
- Farbdisziplin: ein Farbsystem, keine Mischung beliebig bunter Boxen
- DEUTSCH MIT ECHTEN UMLAUTEN: alle Texte mit ä ö ü ß schreiben, NIE ae/oe/ue-Ausweichschreibweise"""

_HTML_SCHEMA = """Gib AUSSCHLIESSLICH dieses JSON aus:
{"html":"<!doctype html> ... komplette Folien-Seite ... "}
"""

def _html_aus_text(txt):
    """Roh-Text -> komplette HTML-Seite (JSON-Erstversuch, sonst Regex)."""
    import re as _re
    if not txt:
        return None
    d = AI._extract_json(txt)
    html = d.get("html") if isinstance(d, dict) else None
    if not (isinstance(html, str) and "<html" in html.lower()):
        m = _re.search(r"<!doctype html[\s\S]*?</html>", txt, _re.I)
        html = m.group(0) if m else None
    return html if html and "</html>" in html.lower() else None




# ---------------------------------------------------------------- Logo-Injektion (Weg B)
_LOGO_URI = None


def _logo_data_uri():
    global _LOGO_URI
    if _LOGO_URI is None:
        import base64
        from pathlib import Path
        p = Path(__file__).resolve().parent.parent / "slideforce" / "assets" / "vorlage_dataport.png"
        _LOGO_URI = "data:image/png;base64," + base64.b64encode(p.read_bytes()).decode()
    return _LOGO_URI


def _html_logo_injizieren(html):
    """dataport-Logo fix oben rechts injizieren (GLM baut es nicht selbst)."""
    import re as _re
    if "dp-logo-img" in html:
        return html
    img = ("<img class='dp-logo-img' src='" + _logo_data_uri() +
           "' style='position:fixed;top:26px;right:40px;width:150px;z-index:9'>")
    return _re.sub(r"</body>", img + "</body>", html, count=1, flags=_re.I)


def html_folie(briefing, folie_slide_dict, design, nr):
    """GLM designt EINE Folie als komplette HTML-Seite. String oder None."""
    import json as _json
    nl = chr(10)
    user = ("BRIEFING: " + briefing + nl + nl + "DESIGNSYSTEM (Leitidee): "
            + _json.dumps((design or {}).get("designsystem") or {}, ensure_ascii=False)
            + nl + nl + "FOLIE " + str(nr) + " (Inhalte verbindlich, Zahlen exakt):" + nl
            + _json.dumps(folie_slide_dict, ensure_ascii=False)
            + nl + nl + _HTML_SCHEMA)
    for versuch in range(3):
        txt = glm.chat(HTML_SYSTEM, user, max_tokens=12000, timeout=300)
        html = _html_aus_text(txt)
        if html:
            return _html_logo_injizieren(html)
        user = user + nl + nl + 'WICHTIG: Antworte NUR mit dem JSON {"html": "<!doctype html> ..."}. Keine Prosa.'
    return None


def html_repair(briefing, folie_slide_dict, altes_html, critic_ergebnis, nr):
    """Eine schwache HTML-Folie anhand der Kritik reparieren."""
    import json as _json
    nl = chr(10)
    user = ("BRIEFING: " + briefing + nl + nl
            + "FOLIE " + str(nr) + " (aktueller Stand, zu reparieren):" + nl
            + str(altes_html) + nl + nl
            + "CRITIC (score " + str(critic_ergebnis.get('score')) + "/10): "
            + "; ".join(critic_ergebnis.get("schwaechen") or []) + nl
            + "Fix-Anweisung: " + (critic_ergebnis.get("fix") or "-") + nl + nl
            + "Repariere die Folie. Fakten/Zahlen bleiben exakt."
            + nl + nl + _HTML_SCHEMA)
    for versuch in range(3):
        txt = glm.chat(HTML_SYSTEM, user, max_tokens=12000, timeout=300)
        html = _html_aus_text(txt)
        if html:
            return _html_logo_injizieren(html)
        user = user + nl + nl + 'Antworte NUR mit dem JSON {"html": "..."}.'
    return None
