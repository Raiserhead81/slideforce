"""Studio: Render-Pipeline PPTX -> PDF -> PNG je Folie.
soffice (headless) -> pdftoppm. Deterministisch, keine KI."""
import re
import subprocess
from pathlib import Path


def render_folien(pptx_path, out_dir, dpi=110, timeout=240):
    """PPTX -> out_dir/<stem>.pdf + folie-XX.png. Gibt (pdf, [png,...]) zurueck."""
    pptx_path, out_dir = Path(pptx_path), Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(["soffice", "--headless", "--convert-to", "pdf",
                    "--outdir", str(out_dir), str(pptx_path)],
                   check=True, capture_output=True, timeout=timeout)
    pdf = out_dir / (pptx_path.stem + ".pdf")
    if not pdf.is_file():
        raise RuntimeError(f"PDF fehlt nach soffice: {pdf}")
    subprocess.run(["pdftoppm", "-png", "-r", str(dpi), str(pdf),
                    str(out_dir / "folie")],
                   check=True, capture_output=True, timeout=timeout)
    pngs = sorted(out_dir.glob("folie-*.png"),
                  key=lambda p: int(re.search(r"(\d+)\.png$", p.name).group(1)))
    if not pngs:
        raise RuntimeError(f"keine PNGs nach pdftoppm in {out_dir}")
    return str(pdf), [str(p) for p in pngs]


def _svg_dupe_attrs_raus(svg):
    """GLM-SVGs enthalten oft doppelte Attribute je Element - libxml2 lehnt ab.
    Reparatur: je Tag nur das erste Auftreten jedes Attributnamens behalten."""
    def tag_fix(m):
        inner = m.group(1)
        if inner.startswith(("/", "!", "?")):
            return m.group(0)
        self_closing = inner.rstrip().endswith("/")
        body = inner.rstrip()[:-1] if self_closing else inner
        mm = re.match(r"\s*([\w:.-]+)", body)
        if not mm:
            return m.group(0)
        attrs = re.findall(
            r"([\w:-]+)\s*=\s*(\"[^\"]*\"|'[^']*')", body)
        gesehen, neu = set(), []
        for name, wert in attrs:
            if name not in gesehen:
                gesehen.add(name)
                neu.append(f"{name}={wert}")
        s = f"<{mm.group(1)}" + (" " + " ".join(neu) if neu else "")
        if self_closing:
            s += " /"
        return s + ">"
    return re.sub(r"<([^>]*)>", tag_fix, svg)


def svg_zu_png(svg_text, out_png, breite=1200):
    """SVG-String -> PNG (cairosvg). Gibt Pfad oder None bei Fehler.
    Bei kaputtem SVG (z.B. doppelte Attribute von GLM): Reparatur-Versuch."""
    import cairosvg
    out_png = Path(out_png)
    out_png.parent.mkdir(parents=True, exist_ok=True)
    for versuch_text in (svg_text, _svg_dupe_attrs_raus(svg_text)):
        try:
            cairosvg.svg2png(bytestring=versuch_text.encode("utf-8"),
                             write_to=str(out_png), output_width=breite)
            if out_png.is_file() and out_png.stat().st_size > 500:
                return str(out_png)
        except Exception as e:
            import sys
            print(f"[render] svg_zu_png: {type(e).__name__}: {e}",
                  file=sys.stderr, flush=True)
    return None
