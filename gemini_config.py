import os
import json
import re
from typing import Optional, Dict, Any, Tuple
import google.generativeai as genai
import pandas as pd
from datetime import datetime

LKPD_DIR = "lkpd_outputs"
ANSWERS_DIR = "answers"
REKAP_DIR = "rekap"

_MODEL = None
_CHOSEN_MODEL_NAME = None

os.makedirs(LKPD_DIR, exist_ok=True)
os.makedirs(ANSWERS_DIR, exist_ok=True)
os.makedirs(REKAP_DIR, exist_ok=True)


def _extract_json_from_text(text: str) -> Optional[str]:
    if not text:
        return None
    cleaned = text.replace("```json", "").replace("```", "").strip()
    m = re.search(r'\{.*\}', cleaned, re.DOTALL)
    return m.group(0) if m else cleaned


def init_model(api_key: Optional[str]) -> Tuple[bool, str, Dict[str, Any]]:
    global _MODEL, _CHOSEN_MODEL_NAME
    debug = {}
    try:
        if not api_key or not isinstance(api_key, str) or api_key.strip() == "":
            return False, "API key kosong atau tidak valid.", debug

        genai.configure(api_key=api_key)

        # Ambil model
        candidates = [
            "models/gemini-2.5-flash",
            "models/gemini-1.5-flash",
            "gemini-1.5"
        ]

        chosen = None
        for c in candidates:
            try:
                _MODEL = genai.GenerativeModel(c)
                chosen = c
                break
            except Exception:
                continue

        if not chosen:
            return False, "Gagal inisialisasi model Gemini.", debug

        _CHOSEN_MODEL_NAME = chosen
        debug["chosen_model"] = chosen
        return True, f"Model aktif: {chosen}", debug

    except Exception as e:
        return False, f"Unexpected init error: {type(e).__name__}: {e}", debug


def get_model():
    return _MODEL


def analyze_answer_with_ai(answer: str) -> Dict[str, Any]:
    """Analisis jawaban per pertanyaan"""
    model = get_model()
    if not model or not answer:
        return {"penjelasan": "Model tidak aktif atau jawaban kosong.", "skor": 0}

    prompt = f"""
    Analisis jawaban berikut dari siswa dan berikan skor 0-100 serta penjelasan singkat:
    Jawaban: {answer}

    Format keluaran:
    {{
        "skor": <angka>,
        "penjelasan": "<teks singkat>"
    }}
    """

    try:
        res = model.generate_content(prompt)
        extracted = _extract_json_from_text(res.text)
        if extracted:
            return json.loads(extracted)
    except Exception:
        pass
    return {"penjelasan": "Analisis gagal.", "skor": 0}


def analyze_student_overall(nama: str, jawaban_list: list) -> Dict[str, Any]:
    """Analisis pemahaman keseluruhan siswa berdasarkan semua jawaban"""
    model = get_model()
    if not model or not jawaban_list:
        return {"nama": nama, "rata_nilai": 0, "analisis_singkat": "Tidak ada jawaban."}

    gabung_jawaban = "\n".join([f"{i+1}. {j['jawaban']}" for i, j in enumerate(jawaban_list)])
    prompt = f"""
    Berdasarkan kumpulan jawaban berikut dari siswa bernama {nama}, analisis tingkat pemahamannya.
    Berikan skor rata-rata (0-100) dan deskripsi singkat (maks 30 kata).

    Jawaban:
    {gabung_jawaban}

    Format keluaran JSON:
    {{
        "rata_nilai": <angka>,
        "analisis_singkat": "<teks singkat>"
    }}
    """

    try:
        res = model.generate_content(prompt)
        extracted = _extract_json_from_text(res.text)
        if extracted:
            result = json.loads(extracted)
            return {
                "nama": nama,
                "rata_nilai": result.get("rata_nilai", 0),
                "analisis_singkat": result.get("analisis_singkat", "")
            }
    except Exception:
        pass

    return {"nama": nama, "rata_nilai": 0, "analisis_singkat": "Gagal analisis."}


def export_rekap_to_excel(lkpd_id: str, rekap_data: list) -> str:
    """Ekspor hasil rekap nilai ke file Excel"""
    df = pd.DataFrame(rekap_data)
    filename = os.path.join(REKAP_DIR, f"{lkpd_id}_rekap.xlsx")
    df.to_excel(filename, index=False)
    return filename


def load_json(folder, name):
    path = os.path.join(folder, f"{name}.json")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def save_json(folder, name, data):
    path = os.path.join(folder, f"{name}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
