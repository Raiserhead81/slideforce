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
