"""SlideForce: Theme-Extraktion. Farben + Fonts aus dem Folienmaster lesen."""
import re
import zipfile


def extract_theme(master_path):
    """clrScheme + Fonts aus ppt/theme/theme1.xml -> dict mit CSS-Farben."""
    try:
        with zipfile.ZipFile(str(master_path)) as z:
            xml = z.read("ppt/theme/theme1.xml").decode("utf-8", errors="replace")
    except KeyError:
        return None
    colors = {}
    for name in ("dk1", "lt1", "dk2", "lt2", "accent1", "accent2", "accent3",
                 "accent4", "accent5", "accent6", "hlink"):
        m = re.search(rf'<a:{name}>.*?(?:srgbClr val="([0-9A-Fa-f]{{6}})"|sysClr[^/]*lastClr="([0-9A-Fa-f]{{6}})")',
                      xml, re.S)
        if m:
            colors[name] = "#" + (m.group(1) or m.group(2)).lower()
    fonts = {}
    for role in ("major", "minor"):
        m = re.search(rf'<a:{role}Font>.*?<a:latin typeface="([^"]*)"', xml, re.S)
        if m:
            fonts[role] = m.group(1)
    return {"colors": colors, "fonts": fonts}
