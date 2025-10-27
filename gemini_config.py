"""
gemini_config.py — FINAL STABLE VERSION
---------------------------------------
Versi ini:
✅ Stabil, tanpa error import.
✅ Kompatibel penuh dengan app.py final.
✅ Menghasilkan LKPD otomatis dalam format JSON.
✅ Dapat menganalisis jawaban siswa (untuk guru).
"""

import os
import json
import re
import time
from typing import Optional, Dict, Any, Tuple
import google.generativeai as genai

# Folder data
LKPD_DIR = "lkpd_outputs"
ANSWERS_DIR = "answers"

_MODEL = None
_CHOSEN_MODEL_NAME = None


# ------------------ Utility ------------------
def _extract_json_from_text(text: str) -> Optional[str]:
    if not text:
        return None
    cleaned = text.replace("```json", "").replace("```", "").strip()
    m = re.search(r'\{.*\}', cleaned, re.DOTALL)
    return m.group(0) if m else cleaned


# ------------------ Model Init ------------------
def init_model(api_key: Optional[str]) -> Tuple[bool, str, Dict[str, Any]]:
    global _MODEL, _CHOSEN_MODEL_NAME
    debug = {}
    try:
        if not api_key or not isinstance(api_key, str) or api_key.strip() == "":
            return False, "API key kosong atau tidak valid.", debug

        genai.configure(api_key=api_key)
        candidates = [
            "models/gemini-2.5-flash",
            "gemini-2.5-flash",
            "models/gemini-1.5-flash",
            "gemini-1.5-flash",
        ]
        chosen = None
        try:
            models = genai.list_models()
            names = [m.name for m in models]
            for c in candidates:
                if c in names:
                    chosen = c
                    break
        except Exception:
            chosen = "gemini-1.5-flash"

        _MODEL = genai.GenerativeModel(chosen)
        _CHOSEN_MODEL_NAME = chosen
        debug["chosen_model"] = chosen
        return True, f"Model initialized: {chosen}", debug

    except Exception as e:
        return False, f"Init Error: {type(e).__name__}: {e}", debug


def get_model():
    return _MODEL


def list_available_models() -> Dict[str, Any]:
    try:
        models = genai.list_models()
        return {"ok": True, "count": len(models), "names": [m.name for m in models]}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ------------------ LKPD Generator ------------------
def generate_lkpd(theme: str, max_retry: int = 1) -> Tuple[Optional[Dict[str, Any]], Dict[str, Any]]:
    debug = {"chosen_model": _CHOSEN_MODEL_NAME}
    model = get_model()
    if not model:
        debug["error"] = "Model not initialized"
        return None, debug

    prompt = f"""
    Buatkan LKPD interaktif dengan tema: "{theme}".
    Format hasil HARUS JSON valid seperti ini:
    {{
      "judul": "Judul LKPD",
      "tujuan_pembelajaran": ["Tujuan 1", "Tujuan 2"],
      "materi_singkat": "Ringkasan materi singkat dalam 1 paragraf.",
      "kegiatan": [
        {{
          "nama": "Kegiatan 1",
          "petunjuk": "Langkah-langkah kegiatan",
          "pertanyaan_pemantik": [
            {{"pertanyaan": "Pertanyaan 1"}},
            {{"pertanyaan": "Pertanyaan 2"}}
          ]
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
            debug["raw_response"] = raw[:5000]
            json_block = _extract_json_from_text(raw)
            if not json_block:
                raise ValueError("Tidak ditemukan blok JSON")

            data = json.loads(json_block)
            return data, debug
        except Exception as e:
            debug.setdefault("attempts", []).append(f"{type(e).__name__}: {e}")
            attempt += 1
            time.sleep(0.5)
            if attempt > max_retry:
                debug["last_raw"] = last_raw
                return None, debug


# ------------------ Penilaian Jawaban Siswa ------------------
def analyze_answer_with_ai(answer_text: str) -> Dict[str, Any]:
    """
    AI menilai pemahaman siswa secara semi-otomatis.
    Output: {score:int, feedback:str}
    """
    model = get_model()
    if not model:
        return {"score": 0, "feedback": "Model belum siap."}
    prompt = f"""
    Analisis jawaban siswa berikut dan berikan skor (0–100) serta feedback singkat.
    Jawaban siswa:
    \"\"\"{answer_text}\"\"\"
    Format output (JSON saja):
    {{
      "score": <angka>,
      "feedback": "<analisis singkat>"
    }}
    """
    try:
        resp = model.generate_content(prompt)
        text = getattr(resp, "text", str(resp))
        js = _extract_json_from_text(text)
        return json.loads(js)
    except Exception as e:
        return {"score": 0, "feedback": f"Analisis gagal: {e}"}


# ------------------ File Helpers ------------------
def save_json(folder: str, file_id: str, data: dict):
    os.makedirs(folder, exist_ok=True)
    with open(os.path.join(folder, f"{file_id}.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_json(folder: str, file_id: str):
    path = os.path.join(folder, f"{file_id}.json")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None
