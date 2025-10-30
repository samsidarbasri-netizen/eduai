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


# ------------------ Utility ------------------
def _extract_json_from_text(text: str) -> Optional[str]:
    if not text:
        return None
    cleaned = text.replace("```json", "").replace("```", "").strip()
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    return match.group(0) if match else cleaned


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
def generate_lkpd(theme: str, difficulty: str = "sedang", max_retry: int = 1) -> Tuple[Optional[Dict[str, Any]], Dict[str, Any]]:
    """
    Menghasilkan LKPD format Pembelajaran Mendalam (Memahami – Mengaplikasikan – Merefleksi)
    dengan parameter tingkat kesulitan: mudah / sedang / sulit.
    """
    debug = {"chosen_model": _CHOSEN_MODEL_NAME, "difficulty": difficulty}
    model = get_model()
    if not model:
        debug["error"] = "Model not initialized"
        return None, debug

    difficulty_text = {
        "mudah": "Gunakan pertanyaan yang bersifat dasar dan eksploratif sederhana, cocok untuk pemula.",
        "sedang": "Gunakan pertanyaan yang menantang pemahaman dan aplikasi konsep secara moderat.",
        "sulit": "Gunakan pertanyaan analitis-reflektif yang menuntut sintesis dan argumentasi mendalam.",
    }.get(difficulty.lower(), "Gunakan pertanyaan dengan tingkat menengah (sedang).")

    prompt = f"""
    Buatkan saya Lembar Kerja Peserta Didik (LKPD) untuk materi: {theme}.

    Tingkat kesulitan: {difficulty.upper()}.
    {difficulty_text}

    Format harus mengikuti Pembelajaran Mendalam (tanpa perhitungan dan visual), 
    dengan struktur JSON berikut:
    {{
      "judul": "LKPD Pembelajaran Mendalam: Memahami {theme} ({difficulty.upper()})",
      "tujuan_pembelajaran": ["..."],
      "materi_singkat": "...",
      "tahapan_pembelajaran": [
        {{
          "tahap": "Memahami",
          "pertanyaan": ["..."]
        }},
        {{
          "tahap": "Mengaplikasikan",
          "pertanyaan": ["..."]
        }},
        {{
          "tahap": "Merefleksi",
          "pertanyaan": ["..."]
        }}
      ],
      "jawaban_benar": ["Contoh jawaban konseptual yang menunjukkan pemahaman sesuai tingkat kesulitan."],
      "format_akhir": "Jawaban Siswa (Nama Siswa: …)"
    }}

    ⚠️ Ketentuan:
    - LKPD berbentuk teks naratif reflektif (tanpa tabel/gambar/diagram).
    - JSON HARUS valid dan hanya berisi elemen di atas.
    """

    attempt = 0
    while attempt <= max_retry:
        try:
            response = model.generate_content(prompt)
            raw = getattr(response, "text", str(response))
            debug["raw_response"] = raw[:2000]
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
                return None, debug


# ------------------ Penilaian Jawaban Siswa ------------------
def analyze_answer_with_ai(question=None, student_answer=None, lkpd_context=None, *args, **kwargs) -> Dict[str, Any]:
    model = get_model()
    if not model:
        return {"score": 0, "feedback": "Model belum siap."}

    if question is None and len(args) > 0:
        question = args[0]
    if student_answer is None and len(args) > 1:
        student_answer = args[1]
    if lkpd_context is None and len(args) > 2:
        lkpd_context = args[2]

    if not student_answer or not student_answer.strip():
        return {"score": 0, "feedback": "Siswa tidak menjawab."}

    prompt = f"""
    Anda adalah sistem penilai otomatis berbasis AI.

    Konteks LKPD:
    {lkpd_context}

    Pertanyaan:
    {question}

    Jawaban siswa:
    {student_answer}

    Instruksi:
    1️⃣ Berikan skor objektif (0–100) berdasarkan ketepatan konsep dan kedalaman pemahaman.
    2️⃣ Berikan umpan balik singkat dan spesifik.

    Format HARUS:
    SKOR: [angka]
    FEEDBACK: [teks]
    """

    try:
        resp = model.generate_content(prompt)
        text = getattr(resp, "text", str(resp)) or ""
        score = 0
        feedback = "Siswa tidak menjawab."

        if "SKOR:" in text:
            try:
                score_line = text.split("SKOR:")[1].split("\n")[0].strip()
                score = int(''.join(c for c in score_line if c.isdigit()) or "0")
            except:
                score = 0

        if "FEEDBACK:" in text:
            feedback = text.split("FEEDBACK:")[1].strip()

        return {"score": score, "feedback": feedback}
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
