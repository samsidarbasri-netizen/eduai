"""
gemini_config.py (versi sederhana)
Hanya untuk membuat LKPD otomatis dari tema yang diberikan guru.
"""

import os
import json
import re
from typing import Optional, Dict, Any

import google.generativeai as genai

_MODEL = None

def init_model(api_key: Optional[str]):
    """Inisialisasi Gemini API."""
    global _MODEL
    try:
        if not api_key:
            return False, "API key kosong."
        genai.configure(api_key=api_key)
        _MODEL = genai.GenerativeModel("models/gemini-1.5-flash")
        return True, "Model siap digunakan."
    except Exception as e:
        return False, f"Gagal inisialisasi model: {e}"

def get_model():
    return _MODEL

def _extract_json(text: str):
    text = text.replace("```json", "").replace("```", "").strip()
    m = re.search(r"\{.*\}", text, re.DOTALL)
    return m.group(0) if m else None

def generate_lkpd(theme: str) -> Optional[Dict[str, Any]]:
    """Menghasilkan struktur LKPD otomatis dari tema."""
    model = get_model()
    if not model:
        return None

    prompt = f"""
    Buatkan LKPD sederhana dalam format JSON untuk tema "{theme}".
    Gunakan format:
    {{
      "judul": "Judul LKPD",
      "tujuan": ["Tujuan 1", "Tujuan 2"],
      "materi_singkat": "Penjelasan singkat.",
      "pertanyaan": [
        {{"soal": "Pertanyaan 1?"}},
        {{"soal": "Pertanyaan 2?"}}
      ]
    }}
    """

    try:
        res = model.generate_content(prompt)
        raw = getattr(res, "text", str(res))
        json_part = _extract_json(raw)
        if not json_part:
            return None
        return json.loads(json_part)
    except Exception:
        return None
