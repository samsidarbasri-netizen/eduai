import os
import json
import re
import time
from typing import Optional, Dict, Any, Tuple
import google.generativeai as genai

LKPD_DIR = "lkpd_outputs"
ANSWERS_DIR = "answers"
_MODEL = None
_CHOSEN_MODEL_NAME = None

# ---------------------------------------------------------
# JSON Extraction Helper
# ---------------------------------------------------------
def _extract_json_from_text(text: str) -> Optional[str]:
    if not text:
        return None
    cleaned = text.replace("```json", "").replace("```", "").strip()
    m = re.search(r"\{.*\}", cleaned, re.DOTALL)
    return m.group(0) if m else cleaned

# ---------------------------------------------------------
# INIT MODEL
# ---------------------------------------------------------
def init_model(api_key: Optional[str]) -> Tuple[bool, str, Dict[str, Any]]:
    global _MODEL, _CHOSEN_MODEL_NAME
    debug = {}

    if not api_key or not isinstance(api_key, str) or api_key.strip() == "":
        return False, "API key kosong atau tidak valid.", debug

    try:
        genai.configure(api_key=api_key)
        models = genai.list_models()
        model_names = [m.name for m in models]
        debug["available_models"] = model_names

        candidates = [
            "models/gemini-2.5-flash",
            "gemini-2.5-flash",
            "models/gemini-1.5-flash",
            "gemini-1.5-flash",
            "gemini-1.5"
        ]
        chosen = next((c for c in candidates if not model_names or c in model_names), "models/gemini-1.5-flash")

        _MODEL = genai.GenerativeModel(chosen)
        _CHOSEN_MODEL_NAME = chosen
        debug["chosen_model"] = chosen
        return True, f"Model initialized: {chosen}", debug

    except Exception as e:
        return False, f"Init error: {e}", debug

def get_model():
    return _MODEL

# ---------------------------------------------------------
# GENERATE LKPD
# ---------------------------------------------------------
def generate_lkpd(theme: str, max_retry: int = 1) -> Tuple[Optional[Dict[str, Any]], Dict[str, Any]]:
    debug = {"chosen_model": _CHOSEN_MODEL_NAME}
    model = get_model()
    if model is None:
        debug["error"] = "Model not initialized"
        return None, debug

    prompt = f"""
    Buat LKPD interaktif untuk tema "{theme}".
    Output HARUS JSON valid dengan format:
    {{
      "judul": "Judul LKPD",
      "tujuan_pembelajaran": ["Tujuan 1", "Tujuan 2"],
      "materi_singkat": "Ringkasan singkat dan kontekstual.",
      "kegiatan": [
        {{
          "nama": "Kegiatan 1",
          "petunjuk": "Langkah singkat kegiatan.",
          "pertanyaan_pemantik": [
            {{"pertanyaan": "Pertanyaan analitis dan kontekstual."}},
            {{"pertanyaan": "Pertanyaan reflektif."}}
          ]
        }}
      ],
      "jawaban_benar": ["Contoh jawaban yang baik dan lengkap."]
    }}
    """

    try:
        response = model.generate_content(prompt)
        raw = getattr(response, "text", str(response))
        json_part = _extract_json_from_text(raw)
        data = json.loads(json_part)
        return data, debug
    except Exception as e:
        debug["error"] = str(e)
        return None, debug

# ---------------------------------------------------------
# ANALISIS JAWABAN (Semi-Otomatis)
# ---------------------------------------------------------
def analyze_answer_with_ai(answer: str) -> Dict[str, Any]:
    """AI menganalisis kualitas jawaban siswa"""
    model = get_model()
    if not model or not answer:
        return {"penjelasan": "Tidak ada analisis.", "skor": 0}

    try:
        prompt = f"""
        Analisislah jawaban berikut dari siswa:
        "{answer}"

        Berikan penilaian tingkat pemahaman (0–100)
        dan penjelasan singkat mengapa mendapat skor itu.
        Format:
        {{
            "penjelasan": "...",
            "skor": 0–100
        }}
        """
        response = model.generate_content(prompt)
        raw = getattr(response, "text", str(response))
        json_part = _extract_json_from_text(raw)
        result = json.loads(json_part)
        return {
            "penjelasan": result.get("penjelasan", "(Tanpa penjelasan)"),
            "skor": result.get("skor", 0)
        }
    except Exception as e:
        return {"penjelasan": f"AI error: {e}", "skor": 0}

# ---------------------------------------------------------
# SAVE / LOAD JSON
# ---------------------------------------------------------
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
