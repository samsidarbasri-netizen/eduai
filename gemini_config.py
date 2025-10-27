"""
gemini_config.py — Versi stabil (kompatibel dengan app.py modern)

Fungsi utama:
- Inisialisasi model Gemini API
- Generate LKPD otomatis dalam format JSON
- Simpan / muat data LKPD dan jawaban siswa
- Analisis tingkat pemahaman siswa (semi-otomatis untuk guru)
"""

import os
import json
import re
import time
from typing import Optional, Dict, Any, Tuple
import google.generativeai as genai

# ---------------------------------------------------------
# Direktori penyimpanan lokal (bertahan selama sesi)
# ---------------------------------------------------------
LKPD_DIR = "lkpd_outputs"
ANSWERS_DIR = "answers"
os.makedirs(LKPD_DIR, exist_ok=True)
os.makedirs(ANSWERS_DIR, exist_ok=True)

# ---------------------------------------------------------
# Variabel global untuk model
# ---------------------------------------------------------
_MODEL = None
_CHOSEN_MODEL_NAME = None


# ---------------------------------------------------------
# Helper internal
# ---------------------------------------------------------
def _extract_json_from_text(text: str) -> Optional[str]:
    """Ambil blok JSON dari teks AI (menghapus ```json dan ``` bila ada)."""
    if not text:
        return None
    cleaned = text.replace("```json", "").replace("```", "").strip()
    m = re.search(r'\{.*\}', cleaned, re.DOTALL)
    return m.group(0) if m else None


# ---------------------------------------------------------
# Inisialisasi Model Gemini
# ---------------------------------------------------------
def init_model(api_key: Optional[str]) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Inisialisasi model Gemini.
    Mengembalikan (ok, message, debug_dict)
    """
    global _MODEL, _CHOSEN_MODEL_NAME
    debug = {}
    try:
        if not api_key or not isinstance(api_key, str) or api_key.strip() == "":
            return False, "API key kosong atau tidak valid.", debug

        genai.configure(api_key=api_key)

        # Coba list model
        try:
            models = genai.list_models()
            model_names = [m.name for m in models]
            debug['available_models'] = model_names
        except Exception as e:
            debug['list_models_error'] = f"{type(e).__name__}: {e}"
            model_names = []

        candidates = [
            "models/gemini-2.0-flash",
            "models/gemini-2.5-flash",
            "models/gemini-1.5-flash",
            "gemini-1.5-pro",
            "gemini-1.5-flash"
        ]

        chosen = None
        for c in candidates:
            if not model_names or c in model_names:
                chosen = c
                break
        if not chosen:
            chosen = "gemini-1.5-flash"

        try:
            _MODEL = genai.GenerativeModel(chosen)
            _CHOSEN_MODEL_NAME = chosen
            debug['chosen_model'] = chosen
            return True, f"Model inisialisasi berhasil: {chosen}", debug
        except Exception as e:
            debug['init_model_error'] = f"{type(e).__name__}: {e}"
            return False, f"Gagal inisialisasi model: {e}", debug

    except Exception as e:
        return False, f"Kesalahan inisialisasi: {type(e).__name__}: {e}", debug


# ---------------------------------------------------------
# Mendapatkan model aktif
# ---------------------------------------------------------
def get_model():
    return _MODEL


# ---------------------------------------------------------
# Daftar model yang tersedia
# ---------------------------------------------------------
def list_available_models() -> Dict[str, Any]:
    try:
        models = genai.list_models()
        return {"ok": True, "count": len(models), "names": [m.name for m in models]}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


# ---------------------------------------------------------
# Generate LKPD (AI membuat LKPD berbasis tema)
# ---------------------------------------------------------
def generate_lkpd(theme: str, max_retry: int = 1) -> Tuple[Optional[Dict[str, Any]], Dict[str, Any]]:
    debug = {"chosen_model": _CHOSEN_MODEL_NAME}
    model = get_model()
    if model is None:
        debug['error'] = "Model belum diinisialisasi."
        return None, debug

    prompt = f"""
    Buatkan LKPD (Lembar Kerja Peserta Didik) interaktif untuk tema "{theme}".
    Format keluaran HARUS JSON valid seperti contoh berikut:
    {{
      "judul": "Judul LKPD",
      "tujuan_pembelajaran": ["Tujuan 1", "Tujuan 2"],
      "materi_singkat": "Ringkasan singkat satu paragraf.",
      "kegiatan": [
        {{
          "nama": "Kegiatan 1",
          "petunjuk": "Petunjuk singkat kegiatan 1",
          "pertanyaan_pemantik": [
            {{"pertanyaan": "Pertanyaan analisis 1"}},
            {{"pertanyaan": "Pertanyaan reflektif 2"}}
          ]
        }}
      ],
      "jawaban_benar": ["Contoh jawaban 1", "Contoh jawaban 2"]
    }}
    Jangan sertakan teks di luar format JSON.
    """

    attempt = 0
    last_raw = None
    while attempt <= max_retry:
        try:
            response = model.generate_content(prompt)
            raw = getattr(response, "text", str(response))
            debug['raw_response'] = raw[:2000] if raw else ""
            last_raw = raw

            json_part = _extract_json_from_text(raw)
            if not json_part:
                debug['parse_error'] = "Tidak menemukan blok JSON dalam respons AI"
                raise ValueError("No JSON block found")

            data = json.loads(json_part)
            debug['success'] = True
            return data, debug
        except Exception as e:
            debug.setdefault('attempts', []).append({"attempt": attempt, "error": str(e)})
            attempt += 1
            time.sleep(0.5 * attempt)
            if attempt > max_retry:
                debug['last_raw'] = last_raw
                return None, debug


# ---------------------------------------------------------
# Analisis Pemahaman Siswa (Semi-Otomatis)
# ---------------------------------------------------------
def analyze_student_understanding(text: str) -> dict:
    """
    Analisis jawaban siswa untuk menilai tingkat pemahaman.
    Output contoh:
    {
      "nilai_ai": 85,
      "analisis": "Siswa memahami konsep utama dengan baik, namun kurang mendalam."
    }
    """
    model = get_model()
    if model is None:
        return {"nilai_ai": 0, "analisis": "Model belum diinisialisasi"}

    try:
        prompt = f"""
        Analisis tingkat pemahaman siswa dari teks berikut:
        ---
        {text}
        ---
        Berikan hasil dalam JSON seperti:
        {{
          "nilai_ai": skor antara 0 dan 100,
          "analisis": "Penjelasan singkat mengenai tingkat pemahaman siswa."
        }}
        """

        response = model.generate_content(prompt)
        raw = getattr(response, "text", str(response))
        json_part = _extract_json_from_text(raw)
        if not json_part:
            return {"nilai_ai": 0, "analisis": "Tidak dapat mengekstrak hasil analisis dari AI"}

        result = json.loads(json_part)
        if not isinstance(result, dict):
            raise ValueError("Format JSON tidak valid")

        return {
            "nilai_ai": int(result.get("nilai_ai", 0)),
            "analisis": str(result.get("analisis", ""))
        }
    except Exception as e:
        return {"nilai_ai": 0, "analisis": f"Gagal menganalisis: {type(e).__name__}: {e}"}


# ---------------------------------------------------------
# Simpan dan muat file JSON
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
