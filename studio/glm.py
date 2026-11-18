"""Studio: GLM-Anbindung fuer alle Rollen (Infra-Vorbild: slideforce/ai_design.py).

Text- und Vision-Calls (JSON-Antworten) gegen bridge28.gemivo.de/zai.php;
Token laedt ausschliesslich slideforce.ai_design.load_ai_config() aus der
unversionierten web/ai-config.json. Kein Token im Code.
"""
import base64
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from slideforce import ai_design as AI

_RETRIES = 3          # Netzwerk/JSON-Versuche pro Call


def config():
    """GLM-Config (lazy, gecached). Wirft RuntimeError ohne ai-config.json."""
    cfg = AI.load_ai_config()
    if not cfg:
        raise RuntimeError(
            "Keine GLM-Config gefunden (web/ai-config.json fehlt oder leer)")
    return cfg


def _post(messages, max_tokens, timeout=None):
    """Low-level POST an die Bridge. Gibt Antwort-Text oder None.
    Bei 429 (Stunden-Limit) wird mit steigendem Backoff bis zu 3x gewartet."""
    cfg = config()
    body = json.dumps({
        "model": cfg.get("model", "glm-5.3"),
        "max_tokens": int(max_tokens),
        "messages": messages,
    }).encode("utf-8")
    to = int(timeout or cfg.get("timeout", 90))
    delay = 2.0
    vier29 = 0
    for _versuch in range(_RETRIES):
        try:
            req = urllib.request.Request(
                cfg["url"], data=body,
                headers={"Content-Type": "application/json",
                         "User-Agent": "slideforce-studio"})
            raw = urllib.request.urlopen(req, timeout=to).read()
            msg = (json.loads(raw).get("choices") or [{}])[0].get("message") or {}
            txt = msg.get("content") or msg.get("reasoning_content") or ""
            if txt.strip():
                return txt
        except urllib.error.HTTPError as e:                 # Fehler sichtbar
            if e.code == 429:              # Kontingent/Stunden-Limit
                vier29 += 1
                delay = max(delay, 30.0)
                if vier29 >= _RETRIES:
                    raise RuntimeError(
                        "GLM 429: Kontingent/Stunden-Limit erreicht - "
                        "spaeter mit --resume fortsetzen") from e
            elif e.code >= 500:
                delay = max(delay, 8.0)
            print(f"[glm] HTTP {e.code} (Versuch {_versuch + 1}/"
                  f"{_RETRIES}) - warte {delay:.0f}s", file=sys.stderr,
                  flush=True)
        except (urllib.error.URLError, TimeoutError, OSError, ValueError, KeyError,
                json.JSONDecodeError) as e:
            print(f"[glm] {type(e).__name__}: {e} (Versuch {_versuch + 1}/"
                  f"{_RETRIES})", file=sys.stderr, flush=True)
        time.sleep(delay)
        delay = min(60.0, delay * 1.8)
    return None


def chat(system, user, max_tokens=6000, timeout=None):
    """Ein Text-Call. Antwort als String oder None."""
    return _post([{"role": "system", "content": system},
                  {"role": "user", "content": user}], max_tokens, timeout)


def chat_json(system, user, max_tokens=6000, timeout=None):
    """Text-Call, erwartet JSON-Antwort. dict/list oder None.

    Bei ungueltigem JSON ein Wiederholungsversuch mit Hinweis an das Modell.
    """
    hinweis = ("\n\nWICHTIG: Deine letzte Antwort war kein gueltiges JSON. "
               "Antworte AUSSCHLIESSLICH mit dem geforderten JSON-Objekt, "
               "ohne Markdown, ohne Erklaerung.")
    txt = _post([{"role": "system", "content": system},
                 {"role": "user", "content": user}], max_tokens, timeout)
    d = AI._extract_json(txt) if txt else None
    if d is None:
        txt2 = _post([{"role": "system", "content": system},
                      {"role": "user", "content": user + hinweis}],
                     max_tokens, timeout)
        d = AI._extract_json(txt2) if txt2 else None
    return d


def _b64_data_url(png_path):
    data = Path(png_path).read_bytes()
    return "data:image/png;base64," + base64.b64encode(data).decode("ascii")


def vision_json(system, user, image_path, max_tokens=2000, timeout=150):
    """Vision-Call mit EINEM PNG, erwartet JSON-Antwort. dict oder None.

    Bei ungueltigem JSON ein Wiederholungsversuch mit Hinweis (wie chat_json).
    """
    hinweis = ("\n\nWICHTIG: Deine letzte Antwort war kein gueltiges JSON. "
               "Antworte AUSSCHLIESSLICH mit dem geforderten JSON-Objekt, "
               "ohne Markdown, ohne Erklaerung.")

    def _call(u):
        content = [
            {"type": "image_url",
             "image_url": {"url": _b64_data_url(image_path)}},
            {"type": "text", "text": u},
        ]
        txt = _post([{"role": "system", "content": system},
                      {"role": "user", "content": content}], max_tokens, timeout)
        return AI._extract_json(txt) if txt else None

    d = _call(user)
    if d is None:
        d = _call(user + hinweis)
    return d
