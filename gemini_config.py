"""
gemini_config.py (defensive version)

- Tidak memanggil streamlit saat import (safe).
- Exports:
  - init_model(api_key) -> (ok:bool, message:str, debug:dict)
  - get_model()
  - list_available_models() -> dict (debug)
  - generate_lkpd(theme) -> (data_or_none, debug_dict)
  - save_json / load_json helpers
"""

import os
import json
import re
import time
from typing import Optional, Dict, Any, Tuple

import google.generativeai as genai

# Local storage (volatile on Streamlit Cloud)
LKPD_DIR = "lkpd_outputs"
ANSWERS_DIR = "answers"

_MODEL = None
_CHOSEN_MODEL_NAME = None

def _extract_json_from_text(text: str) -> Optional[str]:
    if not text:
        return None
    cleaned = text.replace("```json", "").replace("```", "").strip()
    # find first {...} block
    m = re.search(r'\{.*\}', cleaned, re.DOTALL)
    return m.group(0) if m else cleaned

def init_model(api_key: Optional[str]) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Initialize genai and select a model if available.
    Returns (ok, message, debug_info)
    debug_info contains 'available_models' (if list succeeded) and 'chosen_model'.
    """
    global _MODEL, _CHOSEN_MODEL_NAME
    debug = {}
    try:
        if not api_key or not isinstance(api_key, str) or api_key.strip() == "":
            return False, "API key kosong atau tidak valid.", debug

        genai.configure(api_key=api_key)

        # Try to list models once for debug
        try:
            models = genai.list_models()
            model_names = [m.name for m in models]
            debug['available_models'] = model_names
        except Exception as e:
            # listing models may fail in some configs; record error but continue
            debug['list_models_error'] = f"{type(e).__name__}: {e}"
            model_names = []

        # Prefer these names (order). We'll pick first available.
        candidates = [
            "models/gemini-2.5-flash",
            "gemini-2.5-flash",
            "models/gemini-1.5-flash",
            "gemini-1.5-flash",
            "gemini-1.5"
        ]

        chosen = None
        for c in candidates:
            if not model_names or c in model_names:
                chosen = c
                break

        # If list_models failed and chosen None, fallback to commonly used name:
        if not chosen:
            chosen = "models/gemini-1.5-flash"

        # instantiate model (may raise if name invalid)
        try:
            _MODEL = genai.GenerativeModel(chosen)
            _CHOSEN_MODEL_NAME = chosen
            debug['chosen_model'] = chosen
            return True, f"Model initialized: {chosen}", debug
        except Exception as e:
            debug['init_model_error'] = f"{type(e).__name__}: {e}"
            # try a minimal fallback name
            try:
                _MODEL = genai.GenerativeModel("gemini-1.5-flash")
                _CHOSEN_MODEL_NAME = "gemini-1.5-flash"
                debug['fallback_used'] = "gemini-1.5-flash"
                return True, "Model initialized with fallback gemini-1.5-flash", debug
            except Exception as e2:
                debug['fallback_error'] = f"{type(e2).__name__}: {e2}"
                return False, f"Failed to initialize model: {e} ; fallback failed: {e2}", debug

    except Exception as e:
        return False, f"Unexpected init error: {type(e).__name__}: {e}", debug

def list_available_models() -> Dict[str, Any]:
    """Return dict with available model names or error details."""
    try:
        models = genai.list_models()
        return {"ok": True, "count": len(models), "names": [m.name for m in models]}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}

def get_model():
    return _MODEL

def generate_lkpd(theme: str, max_retry: int = 1) -> Tuple[Optional[Dict[str, Any]], Dict[str, Any]]:
    """
    Generate LKPD; returns (data_dict_or_None, debug_info)
    debug_info includes raw_response (if any), error messages, chosen_model used.
    """
    debug = {"chosen_model": _CHOSEN_MODEL_NAME}
    model = get_model()
    if model is None:
        debug['error'] = "Model not initialized"
        return None, debug

    # prompt instruct JSON output
    prompt = f"""
    Buat LKPD interaktif untuk tema \"{theme}\".
    OUTPUT: hanya JSON valid (tanpa penjelasan lain). Contoh format:
    {{
      "judul": "Judul LKPD",
      "tujuan_pembelajaran": ["Tujuan 1", "Tujuan 2"],
      "materi_singkat": "Ringkasan 1 paragraf.",
      "kegiatan": [
        {{
          "nama":"Kegiatan 1",
          "petunjuk":"Petunjuk singkat",
          "pertanyaan_pemantik":[{{"pertanyaan":"Pertanyaan 1"}}]
        }}
      ],
      "jawaban_benar": ["Contoh jawaban 1", "Contoh jawaban 2"]
    }}
    """

    attempt = 0
    last_raw = None
    while attempt <= max_retry:
        try:
            response = model.generate_content(prompt)
            raw = getattr(response, "text", str(response))
            debug['raw_response'] = raw[:5000] if raw else ""
            last_raw = raw

            # try to extract JSON block
            json_part = _extract_json_from_text(raw)
            if not json_part:
                debug['parse_error'] = "No JSON block found in response"
                raise ValueError("No JSON block found")

            # take first {...} block
            start = json_part.find("{")
            end = json_part.rfind("}")
            if start == -1 or end == -1:
                debug['parse_error'] = "Malformed JSON block"
                raise ValueError("Malformed JSON block")

            json_str = json_part[start:end+1]
            data = json.loads(json_str)
            debug['success'] = True
            return data, debug

        except Exception as e:
            debug.setdefault('attempts', []).append({"attempt": attempt, "error": f"{type(e).__name__}: {e}"})
            attempt += 1
            # small backoff
            time.sleep(0.8 * attempt)
            if attempt > max_retry:
                # return debug including last_raw for diagnosis
                if last_raw:
                    debug['last_raw'] = last_raw[:5000]
                return None, debug

# simple save/load
def save_json(folder: str, file_id: str, data: dict):
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, f"{file_id}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_json(folder: str, file_id: str):
    path = os.path.join(folder, f"{file_id}.json")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None
