import os
import json
import re
import google.generativeai as genai
from typing import Optional, Dict, Any

LKPD_DIR = "lkpd_outputs"
ANSWERS_DIR = "answers"

_MODEL = None

def init_model(api_key: Optional[str]):
    global _MODEL
    try:
        if not api_key:
            return False, "API key tidak tersedia."
        genai.configure(api_key=api_key)
        _MODEL = genai.GenerativeModel("models/gemini-1.5-flash")
        return True, "Model siap digunakan."
    except Exception as e:
        return False, f"Error inisialisasi: {e}"

def get_model():
    return _MODEL

def _extract_json(text: str):
    if not text:
        return None
    text = text.replace("```json", "").replace("```", "").strip()
    match = re.search(r"\{.*\}", text, re.DOTALL)
    return match.group(0) if match else None

def generate_lkpd(theme: str) -> Optional[Dict[str, Any]]:
    model = get_model()
    if not model:
        return None
    prompt = f"""
    Buat LKPD interaktif dengan tema "{theme}".
    Output hanya JSON dengan format:
    {{
      "judul": "Judul LKPD",
      "tujuan_pembelajaran": ["Tujuan 1","Tujuan 2"],
      "materi_singkat": "Ringkasan singkat",
      "kegiatan": [
        {{
          "nama": "Kegiatan 1",
          "petunjuk": "Petunjuk singkat",
          "pertanyaan_pemantik": [
            {{"pertanyaan":"Pertanyaan 1"}},
            {{"pertanyaan":"Pertanyaan 2"}}
          ]
        }}
      ],
      "jawaban_benar": [
         "Contoh jawaban benar pertanyaan 1",
         "Contoh jawaban benar pertanyaan 2"
      ]
    }}
    """
    try:
        res = model.generate_content(prompt)
        text = getattr(res, "text", str(res))
        json_str = _extract_json(text)
        return json.loads(json_str) if json_str else None
    except Exception:
        return None

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
