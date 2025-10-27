"""
gemini_config.py — FINAL STABLE DEEP LEARNING VERSION
-----------------------------------------------------
✅ Kompatibel penuh dengan app.py versi 3 tahap.
✅ LKPD dihasilkan otomatis dengan format pembelajaran mendalam:
   - Memahami
   - Mengaplikasikan
   - Merefleksi
✅ Analisis jawaban siswa semi-otomatis.
✅ Aman, rapi, dan bebas error.
"""

import os
import json
import re
import time
from typing import Optional, Dict, Any, Tuple
import google.generativeai as genai

# ------------------ Folder ------------------
LKPD_DIR = "lkpd_outputs"
ANSWERS_DIR = "answers"

_MODEL = None
_CHOSEN_MODEL_NAME = None


# ------------------ Utility ------------------
def _extract_json_from_text(text: str) -> Optional[str]:
    """Ambil blok JSON dari teks mentah hasil model Gemini."""
    if not text:
        return None
    cleaned = text.replace("```json", "").replace("```", "").strip()
    match = re.search(r'\{.*\}', cleaned, re.DOTALL)
    return match.group(0) if match else cleaned


# ------------------ Model Init ------------------
def init_model(api_key: Optional[str]) -> Tuple[bool, str, Dict[str, Any]]:
    """Inisialisasi model Gemini dengan key dari Streamlit secrets."""
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
    """Melihat daftar model Gemini yang tersedia."""
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
    Buatkan LKPD pembelajaran mendalam dengan tema: "{theme}".
    LKPD harus terdiri dari tiga tahap utama: Memahami, Mengaplikasikan, dan Merefleksi.
    Setiap tahap harus memiliki kegiatan, petunjuk, dan pertanyaan pemantik.
    Format keluaran HARUS JSON valid seperti ini:

    {{
      "judul": "Judul LKPD",
      "tujuan_pembelajaran": ["Tujuan 1", "Tujuan 2"],
      "materi_singkat": "Ringkasan singkat konsep utama dalam 3–5 kalimat.",
      "tahapan": [
        {{
          "nama_tahap": "Memahami",
          "deskripsi": "Penjelasan tahap memahami.",
          "kegiatan": [
            {{
              "nama": "Nama kegiatan memahami",
              "petunjuk": "Langkah kegiatan memahami.",
              "pertanyaan_pemantik": [
                {{"pertanyaan": "Pertanyaan 1"}},
                {{"pertanyaan": "Pertanyaan 2"}}
              ]
            }}
          ]
        }},
        {{
          "nama_tahap": "Mengaplikasikan",
          "deskripsi": "Penjelasan tahap mengaplikasikan.",
          "kegiatan": [
            {{
              "nama": "Nama kegiatan mengaplikasikan",
              "petunjuk": "Langkah kegiatan mengaplikasikan.",
              "pertanyaan_pemantik": [
                {{"pertanyaan": "Pertanyaan 1"}},
                {{"pertanyaan": "Pertanyaan 2"}}
              ]
            }}
          ]
        }},
        {{
          "nama_tahap": "Merefleksi",
          "deskripsi": "Penjelasan tahap merefleksi.",
          "kegiatan": [
            {{
              "nama": "Nama kegiatan merefleksi",
              "petunjuk": "Langkah kegiatan merefleksi.",
              "pertanyaan_pemantik": [
                {{"pertanyaan": "Pertanyaan 1"}},
                {{"pertanyaan": "Pertanyaan 2"}}
              ]
            }}
          ]
        }}
      ]
    }}
    """

    attempt = 0
    while attempt <= max_retry:
        try:
            response = model.generate_content(prompt)
            raw = getattr(response, "text", str(response))
            debug["raw_response"] = raw[:5000]
            json_block = _extract_json_from_text(raw)
            data = json.loads(json_block)
            return data, debug
        except Exception as e:
            debug.setdefault("errors", []).append(str(e))
            attempt += 1
            time.sleep(0.5)
            if attempt > max_retry:
                return None, debug



# ------------------ Penilaian Jawaban Siswa ------------------
def analyze_answer_with_ai(answer_text: str) -> Dict[str, Any]:
    """
    AI memberikan penilaian semi-otomatis:
    - Skor numerik 0–100
    - Analisis singkat terhadap pemahaman siswa
    """
    model = get_model()
    if not model:
        return {"score": 0, "feedback": "Model belum siap."}

    prompt = f"""
    Analisis kualitas jawaban siswa berikut berdasarkan ketepatan konsep dan kedalaman pemahaman.

    Jawaban siswa:
    \"\"\"{answer_text}\"\"\"

    Berikan skor (0–100) dan analisis singkat.
    Format output JSON valid:
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
    """Simpan file JSON secara aman."""
    os.makedirs(folder, exist_ok=True)
    with open(os.path.join(folder, f"{file_id}.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_json(folder: str, file_id: str):
    """Membaca file JSON bila tersedia."""
    path = os.path.join(folder, f"{file_id}.json")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None
