"""Studio: Presentation Director - orchestriert den Run als State-Machine.

Ablauf Weg A: Director-Plan -> Story -> Art -> Build (native PPTX via
SlideForce-Builder) -> Render (soffice/pdftoppm) -> Critic je Folie ->
max 3 Fix-Runden -> Report. Nach JEDEM Schritt wird state.json persistiert
(studio/state.py), ein Lauf ist jederzeit mit --resume fortsetzbar.
"""
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from slideforce import ai_design as AI
from slideforce.readers import read_content

from . import glm, render, roles
from . import webop as OP

ZIEL_SCORE = 8


def _log(log, msg):
    try:
        log(msg)
    except Exception:
        pass


# ---------------------------------------------------------------- Quelle
def quelle_lesen(quelle, grenze=14000):
    """Quelldatei als Text fuer die Rollen (md/txt roh, Office via Reader)."""
    p = Path(quelle)
    suf = p.suffix.lower()
    if suf in (".md", ".markdown", ".txt"):
        txt = p.read_text(encoding="utf-8", errors="replace")
    else:
        txt = AI._slides_as_text(read_content(p, source_title=p.stem))
    txt = txt.strip()
    if len(txt) > grenze:
        txt = txt[:grenze] + "\n[... Quelle vom Studio gekuerzt ...]"
    return txt


# ---------------------------------------------------------------- Schritte
def schritt_director(state, log):
    t0 = time.time()
    txt = quelle_lesen(state.data["quelle"])
    plan = roles.director(state.data["briefing"], txt,
                          state.data["min"], state.data["max"])
    if plan is None:
        state.set_schritt("director", "error",
                          {"fehler": "kein gueltiger Plan"}, dauer_s=time.time() - t0)
        raise RuntimeError("Director-Plan fehlgeschlagen (GLM)")
    state.set_schritt("director", "ok", {"plan": plan}, dauer_s=time.time() - t0)
    _log(log, f"[director] ok: {plan.get('folienzahl')} Folien geplant, "
              f"Kernbotschaft: {str(plan.get('kernbotschaft'))[:70]}")


def schritt_story(state, log):
    t0 = time.time()
    plan = state.schritt("director").get("plan") or {}
    txt = quelle_lesen(state.data["quelle"])
    sb = roles.story(state.data["briefing"], plan, txt,
                     state.data["min"], state.data["max"])
    fehler = roles.validiere_storyboard(sb, state.data["min"], state.data["max"])
    if fehler:                                   # 1 Feedback-Retry
        _log(log, f"[story] ungueltig ({'; '.join(fehler[:3])}) -> Retry")
        sb = roles.story(
            state.data["briefing"] + "\n\n Korrigiere diese Fehler des letzten "
            f"Versuchs: {'; '.join(fehler)}", plan, txt,
            state.data["min"], state.data["max"])
        fehler = roles.validiere_storyboard(sb, state.data["min"], state.data["max"])
    if fehler:
        state.set_schritt("story", "error", {"fehler": fehler},
                          dauer_s=time.time() - t0)
        raise RuntimeError(f"Storyboard ungueltig: {fehler[:3]}")
    for i, f in enumerate(sb["folien"], 1):      # nr deterministisch
        f["nr"] = i
    state.set_schritt("story", "ok", {"storyboard": sb}, dauer_s=time.time() - t0)
    titel = [str(f.get("titel") or "") for f in sb["folien"]]
    _log(log, f"[story] ok: {len(sb['folien'])} Folien, 1. Titel: {titel[0][:60]}")


def schritt_art(state, log):
    t0 = time.time()
    sb = state.schritt("story").get("storyboard")
    design = roles.art(state.data["briefing"], sb)
    if not (isinstance(design, dict) and isinstance(design.get("folien"), list)
            and design["folien"]):
        state.set_schritt("art", "error", {"fehler": "kein gueltiges Design"},
                          dauer_s=time.time() - t0)
        raise RuntimeError("Art-Design fehlgeschlagen (GLM)")
    state.set_schritt("art", "ok", {"design": design}, dauer_s=time.time() - t0)
    ds = design.get("designsystem") or {}
    _log(log, f"[art] ok: {len(design['folien'])} Folien designt - "
              f"{str(ds.get('leitidee'))[:70]}")


def schritt_hybrid(state, log):
    """Weg C: GLM-SVG-Infografiken fuer datengetriebene Folien (kpi/zeitstrahl)
    via cairosvg -> PNG, als 'image' ins Art-Design (nativ + Infografik)."""
    t0 = time.time()
    design = state.schritt("art").get("design") or {}
    folien = list(design.get("folien") or [])
    briefing = state.data["briefing"]
    kandidaten = []
    for i, f in enumerate(folien):
        if not isinstance(f, dict):
            continue
        kind = str(f.get("kind") or f.get("rolle") or "").lower()
        daten = bool(f.get("zeitstrahl")) or any(
            str(k).startswith("zahl") for k in f)
        if daten and kind not in ("title", "titel", "section", "teil"):
            kandidaten.append(i)
    if not kandidaten:
        _log(log, "[hybrid] keine Datenfolien - nativ ohne SVG")
        return
    svg_dir = state.dir / "svg"
    gemacht = []
    for idx in kandidaten:
        nr = idx + 1
        svg = roles.hybrid_svg(briefing, folien[idx], design, nr)
        if not svg:
            _log(log, f"[hybrid] Folie {nr}: keine SVG-Antwort, nativ belassen")
            continue
        png = render.svg_zu_png(svg, svg_dir / f"infografik-{nr:02d}.png")
        if png:
            folien[idx] = dict(folien[idx])
            folien[idx]["image"] = png
            gemacht.append(nr)
            _log(log, f"[hybrid] Folie {nr}: Infografik-PNG ok")
        else:
            _log(log, f"[hybrid] Folie {nr}: SVG-Render fehlgeschlagen, nativ")
    design["folien"] = folien
    state.set_schritt("art", "ok", {"design": design, "hybrid_svgs": gemacht})
    _log(log, f"[hybrid] ok: {len(gemacht)} Infografiken (Folie {gemacht})")


def schritt_build(state, log):
    t0 = time.time()
    sb = state.schritt("story").get("storyboard")
    design = state.schritt("art").get("design") or {}
    slides, warn = OP.slides_aus_design(design, sb)
    if not slides:
        state.set_schritt("build", "error", {"fehler": "keine Folien"},
                          dauer_s=time.time() - t0)
        raise RuntimeError("Build: keine nutzbaren Folien")
    pptx = state.artefakt("deck.pptx")
    OP.build_pptx(slides, pptx)
    state.set_schritt("build", "ok", {
        "pptx": str(pptx), "folien": len(slides), "warnungen": warn,
        "slides": slides}, dauer_s=time.time() - t0)
    _log(log, f"[build] ok: {len(slides)} Folien -> {pptx.name}"
              + (f" ({len(warn)}x Fallback)" if warn else ""))


def schritt_render(state, log):
    t0 = time.time()
    pptx = state.schritt("build").get("pptx")
    pdf, pngs = render.render_folien(pptx, state.dir / "render")
    state.set_schritt("render", "ok", {"pdf": pdf, "pngs": pngs},
                      dauer_s=time.time() - t0)
    _log(log, f"[render] ok: {len(pngs)} PNGs")


def muster(slide):
    if slide.get("table"):
        return "tabelle"
    if slide.get("zeitstrahl"):
        return "zeitstrahl"
    if slide.get("botschaft"):
        return "statement"
    if any(k.startswith("zahl") for k in slide):
        return "kpi"
    k = slide.get("kind", "content")
    return {"title": "titel", "section": "teil"}.get(k, k)


def _kritik_parallel(items):
    """[(nr, png, titel, muster)] -> {nr: critic-dict}."""
    erg = {}
    with ThreadPoolExecutor(max_workers=2) as ex:
        futs = {ex.submit(roles.critic, png, nr, titel, mus): nr
                for nr, png, titel, mus in items}
        for fut in as_completed(futs):
            nr = futs[fut]
            try:
                erg[nr] = fut.result()
            except RuntimeError as e:
                if "429" in str(e):
                    raise          # Kontingent leer: Run sauber abbrechen
                erg[nr] = {"score": 0, "schwaechen": ["Critic-Fehler"], "fix": ""}
            except Exception:
                erg[nr] = {"score": 0, "schwaechen": ["Critic-Fehler"], "fix": ""}
    return erg


def critic_runde(state, log, runde):
    """Bewertet ALLE aktuellen Folien -> Scores-Liste (aufsteigend nach nr)."""
    pngs = state.schritt("render").get("pngs") or []
    slides = state.schritt("build").get("slides") or []
    items = [(i + 1, pngs[i], str(slides[i].get("title") or ""), muster(slides[i]))
             for i in range(min(len(pngs), len(slides)))]
    t0 = time.time()
    erg = _kritik_parallel(items)
    scores = []
    for nr, png, titel, mus in items:
        c = erg.get(nr) or {}
        scores.append({"nr": nr, "muster": mus, "score": c.get("score", 0),
                       "schwaechen": c.get("schwaechen") or [],
                       "fix": c.get("fix") or ""})
    kritik = state.schritt("critic")
    runden = list(kritik.get("runden") or [])
    runden.append({"runde": runde, "scores": scores})
    state.set_schritt("critic", "ok", {"runden": runden}, dauer_s=time.time() - t0)
    enough = ", ".join(f"{s['nr']}:{s['score']}" for s in scores)
    _log(log, f"[critic] Runde {runde}: {enough}")
    return scores


def _repair_folien(state, log, schwach):
    """Art-Repairs parallel je schwacher Folie; design+slides aktualisieren."""
    design = state.schritt("art").get("design") or {}
    slides = list(state.schritt("build").get("slides") or [])
    folien = list(design.get("folien") or [])
    nr_liste = [s["nr"] for s in schwach]

    def rep(nr):
        idx = nr - 1
        neu = roles.art_repair(state.data["briefing"], slides[idx],
                               schwach_dict[nr], nr)
        neu = OP._norm_slide(neu) if neu is not None else None
        if neu is not None and not neu.get("image") and slides[idx].get("image"):
            neu["image"] = slides[idx]["image"]   # Infografik (Weg C) erhalten
        return nr, neu

    schwach_dict = {s["nr"]: s for s in schwach}
    geaendert = []
    with ThreadPoolExecutor(max_workers=2) as ex:
        for nr, neu in ex.map(rep, nr_liste):
            if neu is None:
                _log(log, f"[repair] Folie {nr}: Reparatur unbrauchbar, bleibt")
                continue
            slides[nr - 1] = neu
            if nr - 1 < len(folien):
                folien[nr - 1] = neu
            geaendert.append(nr)
    design["folien"] = folien
    art_alt = state.schritt("art")                 # hybrid_svgs u.a. bewahren
    state.set_schritt("art", "ok", {"design": design,
                                    "hybrid_svgs": art_alt.get("hybrid_svgs")})
    if geaendert:
        # Reparaturen muessen in den Build Fliessen: fix_runden baut aus
        # build.slides - ohne Zurueckschreiben waeren Reparaturen wirkungslos.
        state.data.setdefault("schritte", {}).setdefault(
            "build", {})["slides"] = slides
        state.save()
    return geaendert


def fix_runden(state, log):
    """Nach Erst-Kritik: max state.max_fixrunden Reparatur-Runden (< 8/10)."""
    scores = (state.schritt("critic").get("runden") or [{}])[-1].get("scores") or []
    runde = len(state.schritt("critic").get("runden") or [])
    while True:
        schwach = [s for s in scores if s["score"] < ZIEL_SCORE]
        if not schwach:
            _log(log, "[fix] alle Folien >= 8/10 - fertig")
            return
        if runde > state.data.get("max_fixrunden", 3):
            _log(log, f"[fix] max. Runden erreicht, {len(schwach)} Folie(n) "
                      f"unter {ZIEL_SCORE}/10 (siehe Report)")
            return
        runde += 1
        _log(log, f"[fix] Runde {runde}: repariere Folien "
                  f"{[s['nr'] for s in schwach]}")
        geaendert = _repair_folien(state, log, schwach)
        if not geaendert:
            _log(log, "[fix] keine Reparatur moeglich - Abbruch der Runden")
            return
        t0 = time.time()
        pptx = state.artefakt("deck.pptx")
        OP.build_pptx(state.schritt("build").get("slides"), pptx)
        pdf, pngs = render.render_folien(pptx, state.dir / "render")
        state.set_schritt("build", "ok", {
            "pptx": str(pptx), "folien": len(state.schritt("build").get("slides")),
            "warnungen": state.schritt("build").get("warnungen") or [],
            "slides": state.schritt("build").get("slides")}, dauer_s=time.time() - t0)
        state.set_schritt("render", "ok", {"pdf": pdf, "pngs": pngs})
        # Re-Critic nur der geaenderten Folien, Rest uebernimmt alte Scores
        alt = {s["nr"]: s for s in scores}
        neu_pngs = state.schritt("render").get("pngs") or []
        neu_slides = state.schritt("build").get("slides") or []
        items = [(nr, neu_pngs[nr - 1], str(neu_slides[nr - 1].get("title") or ""),
                  muster(neu_slides[nr - 1])) for nr in geaendert
                 if nr - 1 < len(neu_pngs)]
        erg = _kritik_parallel(items)
        merged = []
        for nr in sorted(alt):
            if nr in erg:
                c = erg[nr]
                alt[nr] = {"nr": nr, "muster": alt[nr].get("muster"),
                           "score": c.get("score", 0),
                           "schwaechen": c.get("schwaechen") or [],
                           "fix": c.get("fix") or ""}
            merged.append(alt[nr])
        kritik = state.schritt("critic")
        runden = list(kritik.get("runden") or [])
        runden.append({"runde": runde, "scores": merged})
        state.set_schritt("critic", "ok", {"runden": runden})
        scores = merged
        _log(log, "[critic] " + ", ".join(f"{s['nr']}:{s['score']}" for s in scores))


# ---------------------------------------------------------------- Report
def schritt_report(state, log):
    t0 = time.time()
    sb = state.schritt("story").get("storyboard") or {}
    design = state.schritt("art").get("design") or {}
    ds = design.get("designsystem") or {}
    slides = state.schritt("build").get("slides") or []
    runden = state.schritt("critic").get("runden") or []
    rpt = state.artefakt("report.md")
    z = []

    z.append(f"# Studio-Run {state.data['id']}\n")
    z.append(f"- **Briefing:** {state.data['briefing']}")
    z.append(f"- **Quelle:** {state.data['quelle']}")
    z.append(f"- **Weg:** {state.data['weg']} (native PPTX) · "
             f"Folienziel {state.data['min']}-{state.data['max']} · "
             f"erreicht: {len(slides)}")
    z.append(f"- **PPTX:** `{state.schritt('build').get('pptx')}`")
    z.append("")

    z.append("## Kernbotschaft & Dramaturgie\n")
    plan = state.schritt("director").get("plan") or {}
    z.append(f"- **Zielgruppe:** {plan.get('zielgruppe', '-')}")
    z.append(f"- **Kernbotschaft:** {plan.get('kernbotschaft', '-')}")
    z.append(f"- **Dramaturgie:** {plan.get('dramaturgie', '-')}")
    teile = plan.get("teile") or []
    if teile:
        z.append(f"- **Teile:** {' | '.join(str(t) for t in teile)}")
    z.append("")

    z.append("## Designsystem (Art Director)\n")
    z.append(f"- **Leitidee:** {ds.get('leitidee', '-')}")
    for p in ds.get("prinzipien") or []:
        z.append(f"  - {p}")
    z.append("- **Brand:** Dataport (Petrol #39756F, Grau #39424A, Rot #9E292B, "
             "Karten #F4F5F6, Tints #FBF0DC/#F8E8E8, Weiss)")
    z.append("")

    z.append("## Storyboard\n")
    z.append("| Nr | Muster | Action Title |")
    z.append("|---:|---|---|")
    for f in sb.get("folien") or []:
        z.append(f"| {f.get('nr')} | {f.get('rolle')} | "
                 f"{str(f.get('titel') or '').replace('|', '/')} |")
    z.append("")

    if runden:
        z.append("## Qualitaet (Visual Critic, Ziel >= 8/10)\n")
        kopf = "| Folie | Muster | " + " | ".join(
            f"R{r['runde']}" for r in runden) + " |"
        z.append(kopf)
        z.append("|---:|---|" + "---:|" * len(runden))
        n = len(runden[-1].get("scores") or [])
        for i in range(n):
            reihe = [r["scores"][i] for r in runden if i < len(r["scores"])]
            mus = reihe[-1].get("muster", "")
            z.append(f"| {reihe[-1]['nr']} | {mus} | "
                     + " | ".join(str(s["score"]) for s in reihe) + " |")
        z.append("")
        final = runden[-1].get("scores") or []
        schwach = [s for s in final if s["score"] < ZIEL_SCORE]
        if schwach:
            z.append("### Offene Schwaechen (nach max. Korrektur-Runden)\n")
            for s in schwach:
                z.append(f"- **Folie {s['nr']} ({s['score']}/10):** "
                         + "; ".join(s.get("schwaechen") or []))
        else:
            z.append(f"**Alle {len(final)} Folien >= {ZIEL_SCORE}/10.**")
        z.append("")

    ann = list(sb.get("annahmen") or [])
    for f in sb.get("folien") or []:
        for a in f.get("annahmen") or []:
            ann.append(f"Folie {f.get('nr')}: {a}")
    if ann:
        z.append("## Annahmen (NICHT auf Folien belegt)\n")
        for a in ann:
            z.append(f"- {a}")
        z.append("")

    warn = state.schritt("build").get("warnungen") or []
    if warn:
        z.append("## Build-Hinweise\n")
        for w in warn:
            z.append(f"- {w}")
        z.append("")

    z.append("## Zeiten\n")
    z.append("| Schritt | Dauer s |")
    z.append("|---|---:|")
    for name in ("director", "story", "art", "build", "render", "critic"):
        d = state.schritt(name).get("dauer_s")
        if d is not None:
            z.append(f"| {name} | {d} |")
    rpt.write_text("\n".join(z), encoding="utf-8")
    state.set_schritt("report", "ok", {"pfad": str(rpt)}, dauer_s=time.time() - t0)
    _log(log, f"[report] ok: {rpt}")


# ---------------------------------------------------------------- Run
def run(state, log=print):
    """Kompletten Lauf bis zum Report fuehren; fertige Schritte ueberspringen
    (Resume). Wirft bei hartem Fehler - state.json bleibt fortsetzbar."""
    if not state.fertig("director"):
        schritt_director(state, log)
    if not state.fertig("story"):
        schritt_story(state, log)
    if not state.fertig("art"):
        schritt_art(state, log)
    if state.data.get("weg") == "C" and not state.schritt("art").get("hybrid_svgs"):
        schritt_hybrid(state, log)
    if not state.fertig("build"):
        schritt_build(state, log)
    if not state.fertig("render"):
        schritt_render(state, log)
    if not state.fertig("critic"):
        critic_runde(state, log, runde=1)
    fix_runden(state, log)
    if not state.fertig("report"):
        schritt_report(state, log)
    return state.schritt("report").get("pfad")
