"""
gemini_config.py — FINAL DEPLOY VERSION (v4)
-----------------------------------------------------
✅ Format Pembelajaran Mendalam (Memahami – Mengaplikasikan – Merefleksi)
✅ LKPD hanya berupa teks konseptual — tanpa grafik, tabel, diagram, atau gambar
✅ Mendukung tingkat kesulitan (mudah – sedang – sulit)
✅ Penilaian otomatis + dukungan penilaian manual & rekapan nilai
✅ Kompatibel penuh dengan app.py
"""

import os
import json
import re
import time
from typing import Optional, Dict, Any, Tuple
import google.generativeai as genai
from datetime import datetime

# ------------------ Folder ------------------
LKPD_DIR = "lkpd_outputs"
ANSWERS_DIR = "answers"

_MODEL = None
_CHOSEN_MODEL_NAME = None

# =========================================================
# 🧩 Utility
# =========================================================
def _extract_json_from_text(text: str) -> Optional[str]:
    """Ambil blok JSON dari teks mentah hasil model Gemini."""
    if not text:
        return None
    cleaned = text.replace("```json", "").replace("```", "").strip()
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    return match.group(0) if match else cleaned

# =========================================================
# ⚙️ Model Initialization
# =========================================================
def init_model(api_key: Optional[str]) -> Tuple[bool, str, Dict[str, Any]]:
    """Inisialisasi model Gemini dengan API key."""
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
    """Ambil instance model aktif."""
    return _MODEL

def list_available_models() -> Dict[str, Any]:
    """Melihat daftar model Gemini yang tersedia."""
    try:
        models = genai.list_models()
        return {"ok": True, "count": len(models), "names": [m.name for m in models]}
    except Exception as e:
        return {"ok": False, "error": str(e)}

# =========================================================
# 🧠 Format Kesulitan LKPD
# =========================================================
def get_difficulty_guidelines(level: str) -> str:
    """Aturan pembuatan LKPD berdasarkan tingkat kesulitan."""
    level = (level or "").lower().strip()
    if level == "mudah":
        return """
Tingkat Kesulitan: MUDAH
- Gunakan bahasa sederhana dan komunikatif.
- Contoh konkret dari kehidupan sehari-hari.
- Pertanyaan bersifat dasar (C1–C2).
"""
    elif level == "sedang":
        return """
Tingkat Kesulitan: SEDANG
- Gunakan bahasa semi-akademik.
- Sertakan analisis ringan dan hubungan sosial.
- Pertanyaan pada level penerapan (C3–C4).
"""
    elif level == "sulit":
        return """
Tingkat Kesulitan: SULIT
- Gunakan bahasa ilmiah dan reflektif.
- Sertakan studi kasus kompleks.
- Pertanyaan analisis kritis, evaluatif (C5–C6).
"""
    return "Tingkat kesulitan tidak dikenali (gunakan: mudah / sedang / sulit)."

# =========================================================
# 📘 LKPD Generator
# =========================================================
def generate_lkpd(theme: str, difficulty: str = "sedang", max_retry: int = 1) -> Tuple[Optional[Dict[str, Any]], Dict[str, Any]]:
    """
    Menghasilkan LKPD format Pembelajaran Mendalam (Memahami – Mengaplikasikan – Merefleksi)
    Disesuaikan dengan tingkat kesulitan.
    """
    debug = {"chosen_model": _CHOSEN_MODEL_NAME}
    model = get_model()
    if not model:
        debug["error"] = "Model belum diinisialisasi."
        return None, debug

    difficulty_text = get_difficulty_guidelines(difficulty)

    prompt = f"""
Anda adalah asisten guru yang membuat LKPD berbasis *Pembelajaran Mendalam*.

Tema: {theme}
{difficulty_text}

Buat LKPD dalam format JSON berikut:
{{
  "judul": "LKPD Pembelajaran Mendalam - {theme}",
  "tingkat_kesulitan": "{difficulty}",
  "tujuan_pembelajaran": ["..."],
  "materi_singkat": "...",
  "tahapan_pembelajaran": [
    {{
      "tahap": "Memahami",
      "uraian": "..."
    }},
    {{
      "tahap": "Mengaplikasikan",
      "uraian": "..."
    }},
    {{
      "tahap": "Merefleksi",
      "uraian": "..."
    }}
  ],
  "jawaban_benar": ["Contoh jawaban umum untuk pemahaman konseptual."],
  "format_akhir": "Jawaban Siswa (Nama Siswa: …)"
}}

⚠️ Aturan tambahan:
- Gunakan teks naratif tanpa tabel, poin, atau gambar.
- Gunakan kedalaman dan gaya sesuai tingkat kesulitan di atas.
- Hasilkan **hanya JSON valid** tanpa tambahan penjelasan.
"""

    attempt = 0
    while attempt <= max_retry:
        try:
            response = model.generate_content(prompt)
            raw = getattr(response, "text", str(response))
            debug["raw_response"] = raw[:4000]
            json_block = _extract_json_from_text(raw)
            if not json_block:
                raise ValueError("Tidak ditemukan blok JSON valid.")
            data = json.loads(json_block)
            return data, debug
        except Exception as e:
            debug.setdefault("attempts", []).append(f"{type(e).__name__}: {e}")
            attempt += 1
            time.sleep(0.5)
            if attempt > max_retry:
                return None, debug

# =========================================================
# 🧾 Penilaian Jawaban Otomatis / Manual
# =========================================================
def analyze_answer_with_ai(question=None, student_answer=None, lkpd_context=None, *args, **kwargs) -> Dict[str, Any]:
    """
    Fungsi penilaian otomatis AI yang kompatibel dengan app.py.
    Keyword argument: question, student_answer, lkpd_context.
    """
    model = get_model()
    if not model:
        return {"score": 0, "feedback": "Model belum siap."}

    if not student_answer or not student_answer.strip():
        return {"score": 0, "feedback": "Siswa tidak menjawab."}

    prompt = f"""
Anda adalah sistem penilai otomatis AI.
Konteks LKPD:
{lkpd_context}

Pertanyaan:
{question}

Jawaban siswa:
{student_answer}

Instruksi:
1️⃣ Nilai ketepatan konsep dan kedalaman pemahaman (skor 0–100).
2️⃣ Berikan umpan balik singkat, spesifik, dan mendidik.

Format output HARUS:
SKOR: [angka]
FEEDBACK: [teks]
"""
    try:
        resp = model.generate_content(prompt)
        text = getattr(resp, "text", str(resp)) or ""
        score, feedback = 0, "Siswa tidak menjawab."

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

# =========================================================
# 💾 File I/O (Rekapan Nilai & Jawaban)
# =========================================================
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
