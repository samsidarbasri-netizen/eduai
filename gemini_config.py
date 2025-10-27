"""
gemini_config.py — FINAL CLEAN TEXT VERSION
-----------------------------------------------------
✅ Format Pembelajaran Mendalam (Memahami – Mengaplikasikan – Merefleksi)
✅ LKPD hanya berupa teks konseptual — tanpa grafik, tabel, diagram, atau gambar
✅ Skor otomatis 0 + feedback “Siswa tidak menjawab.”
✅ Aman & kompatibel penuh dengan app.py
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
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    return match.group(0) if match else cleaned


# ------------------ Model Init ------------------
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


# ------------------ LKPD Generator ------------------
def generate_lkpd(theme: str, max_retry: int = 1) -> Tuple[Optional[Dict[str, Any]], Dict[str, Any]]:
    """
    Menghasilkan LKPD format Pembelajaran Mendalam (Teoritis Tanpa Perhitungan)
    Struktur 3 tahap: Memahami – Mengaplikasikan – Merefleksi
    Tidak boleh mengandung gambar, grafik, tabel, diagram, atau visual apapun.
    """
    debug = {"chosen_model": _CHOSEN_MODEL_NAME}
    model = get_model()
    if not model:
        debug["error"] = "Model not initialized"
        return None, debug

    # Prompt revisi sesuai permintaan
    prompt = f"""
    Buatkan saya Lembar Kerja Peserta Didik (LKPD) untuk materi: {theme}.

    LKPD harus menggunakan format Pembelajaran Mendalam (Teoritis Tanpa Perhitungan),
    dengan struktur dan format JSON seperti ini:

    {{
      "judul": "LKPD Pembelajaran Mendalam: Memahami {theme}",
      "tujuan_pembelajaran": [
        "Tujuan 1 (kualitatif dan konseptual)",
        "Tujuan 2",
        "Tujuan 3"
      ],
      "materi_singkat": "Penjelasan konsep inti secara naratif, tanpa rumus atau perhitungan.",
      "tahapan_pembelajaran": [
        {{
          "tahap": "Memahami",
          "deskripsi_tujuan": "Menelusuri konsep dasar dan makna utama dari materi.",
          "bagian_inti": "Penjelasan inti dari konsep.",
          "petunjuk": "Petunjuk singkat tentang apa yang harus dipahami siswa.",
          "pertanyaan_pemantik": [
            {{"pertanyaan": "Apa konsep utama dari {theme}?"}},
            {{"pertanyaan": "Mengapa konsep ini penting dalam kehidupan sehari-hari?"}},
            {{"pertanyaan": "Bagaimana kamu menjelaskan konsep ini dengan bahasa sederhana?"}}
          ]
        }},
        {{
          "tahap": "Mengaplikasikan",
          "deskripsi_tujuan": "Menerapkan konsep dalam konteks hipotetis atau percobaan pikiran.",
          "bagian_inti": "Skenario hipotetis untuk menguji pemahaman siswa.",
          "petunjuk": "Analisis setiap skenario secara konseptual tanpa perhitungan angka.",
          "skenario": [
            {{
              "judul": "Skenario 1",
              "deskripsi": "Deskripsikan situasi hipotetis yang relevan dengan {theme}.",
              "pertanyaan": "Bagaimana konsep ini menjelaskan fenomena tersebut?"
            }},
            {{
              "judul": "Skenario 2",
              "deskripsi": "Skenario hipotetis lain yang menantang pemahaman konsep.",
              "pertanyaan": "Apa hubungan antara konsep dan hasil yang terjadi?"
            }},
            {{
              "judul": "Skenario 3",
              "deskripsi": "Skenario reflektif yang melibatkan penerapan konsep pada konteks baru.",
              "pertanyaan": "Bagaimana kamu akan memecahkan masalah ini dengan konsep {theme}?"
            }}
          ]
        }},
        {{
          "tahap": "Merefleksi",
          "deskripsi_tujuan": "Mengajak siswa merenungkan pemahaman dan penerapan konsep.",
          "bagian_inti": "Refleksi konseptual terhadap makna dan implikasi materi.",
          "petunjuk": "Jawablah dengan jujur berdasarkan pemahaman pribadi.",
          "pertanyaan_pemantik": [
            {{"pertanyaan": "Apa yang kamu pelajari dari proses memahami konsep ini?"}},
            {{"pertanyaan": "Bagaimana penerapan konsep ini dapat mengubah cara pandangmu?"}},
            {{"pertanyaan": "Bagian mana dari materi ini yang paling bermakna bagimu?"}}
          ]
        }}
      ],
      "jawaban_benar": ["Contoh jawaban umum yang menunjukkan pemahaman konseptual."],
      "format_akhir": "Jawaban Siswa (Nama Siswa: …)"
    }}

    ⚠️ Catatan penting:
    - Hanya gunakan teks naratif dan pertanyaan reflektif.
    - Jangan membuat atau menyebut grafik, diagram, tabel, gambar, atau bentuk visual lainnya.
    - Semua penjelasan dan pertanyaan harus bersifat konseptual dan kualitatif, tanpa angka atau rumus.
    - Hasilkan HANYA JSON valid sesuai format di atas (tanpa tambahan teks lain).
    """

    attempt = 0
    while attempt <= max_retry:
        try:
            response = model.generate_content(prompt)
            raw = getattr(response, "text", str(response))
            debug["raw_response"] = raw[:4000]
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
def analyze_answer_with_ai(answer_text: str) -> Dict[str, Any]:
    """
    AI memberikan penilaian semi-otomatis:
    - Skor numerik 0–100
    - Analisis singkat terhadap pemahaman siswa
    - Jika jawaban kosong → skor 0, feedback "Siswa tidak menjawab."
    """
    model = get_model()
    if not model:
        return {"score": 0, "feedback": "Model belum siap."}

    if not answer_text or not answer_text.strip():
        return {"score": 0, "feedback": "Siswa tidak menjawab."}

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
