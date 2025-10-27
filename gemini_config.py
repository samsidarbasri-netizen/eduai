"""
gemini_config.py (versi final & stabil)
Menangani koneksi model Gemini, generator LKPD, analisis jawaban siswa, dan analisis kelas.
"""

import os
import json
import re
import time
from typing import Optional, Dict, Any, Tuple
import google.generativeai as genai

_MODEL = None
_CHOSEN_MODEL = None

def setup_gemini(api_key: str):
    """Inisialisasi koneksi Gemini API"""
    global _MODEL, _CHOSEN_MODEL
    genai.configure(api_key=api_key)
    _CHOSEN_MODEL = "gemini-1.5-flash"
    _MODEL = genai.GenerativeModel(_CHOSEN_MODEL)
    return _MODEL

def get_model():
    return _MODEL

# ---------------------------------------------------------
# 🔹 Fungsi Generator LKPD (dikembalikan seperti versi awal)
# ---------------------------------------------------------
def generate_lkpd(model, theme: str, max_retry: int = 1):
    """Generate LKPD berbasis tema pembelajaran"""
    prompt = f"""
    Buat LKPD interaktif untuk tema "{theme}".
    Format keluaran HARUS JSON dengan struktur:
    {{
      "judul": "Judul LKPD",
      "tujuan_pembelajaran": ["Tujuan 1", "Tujuan 2"],
      "materi_singkat": "Ringkasan 1 paragraf.",
      "kegiatan": [
        {{
          "nama": "Kegiatan 1",
          "petunjuk": "Petunjuk kegiatan.",
          "pertanyaan_pemantik": [{{"pertanyaan": "Pertanyaan 1"}}, {{"pertanyaan": "Pertanyaan 2"}}]
        }}
      ],
      "jawaban_benar": ["Contoh jawaban 1", "Contoh jawaban 2"]
    }}
    """

    for attempt in range(max_retry + 1):
        try:
            response = model.generate_content(prompt)
            raw = getattr(response, "text", str(response))
            m = re.search(r'\{.*\}', raw, re.DOTALL)
            if m:
                data = json.loads(m.group(0))
                return data, {"success": True}
        except Exception as e:
            time.sleep(1)
    return None, {"error": "Gagal membuat LKPD"}

# ---------------------------------------------------------
# 🔹 Analisis jawaban siswa & kelas
# ---------------------------------------------------------
def analyze_answer(model, question: str, student_answer: str):
    """Analisis jawaban siswa dan beri saran nilai"""
    prompt = f"""
    Soal: {question}
    Jawaban siswa: {student_answer}

    Berikan analisis singkat:
    1. Apakah jawaban benar atau salah (dengan alasan singkat)
    2. Nilai numerik (0-100)
    3. Saran perbaikan singkat (1 kalimat)
    Format: teks biasa yang mudah dibaca.
    """
    try:
        response = model.generate_content(prompt)
        return response.text if response else "Gagal menganalisis jawaban."
    except Exception as e:
        return f"Error: {e}"

def analyze_class_summary(model, student_data):
    """Analisis tingkat pemahaman seluruh siswa"""
    data_text = "\n".join([f"{s['Nama']} - Nilai: {s['Nilai']} - Catatan: {s['Analisis']}" for s in student_data])
    prompt = f"""
    Berikut data siswa:
    {data_text}

    Buat ringkasan:
    - Rata-rata pemahaman kelas
    - Pola kesalahan umum
    - Saran perbaikan pembelajaran
    """
    try:
        response = model.generate_content(prompt)
        return response.text if response else "Gagal menganalisis kelas."
    except Exception as e:
        return f"Error: {e}"
