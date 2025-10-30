"""
gemini_config.py — FINAL COMPLETE FIXED VERSION
-----------------------------------------------------
✅ Format Pembelajaran Mendalam (Memahami – Mengaplikasikan – Merefleksi)
✅ LKPD hanya berupa teks konseptual — tanpa grafik, tabel, diagram, atau gambar
✅ Skor otomatis 0 + feedback “Siswa tidak menjawab.”
✅ Kompatibel penuh dengan app.py (parameter question, student_answer, lkpd_context)
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
    # Menghapus blok kode Markdown
    cleaned = text.replace("```json", "").replace("```", "").strip()
    # Mencari pola JSON yang valid
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
        
        # Daftar model yang diutamakan
        candidates = [
            "models/gemini-2.5-flash",
            "gemini-2.5-flash",
            "models/gemini-1.5-flash",
            "gemini-1.5-flash",
        ]
        chosen = None
        
        try:
            # Cek model yang tersedia
            models = genai.list_models()
            names = [m.name for m in models]
            for c in candidates:
                if c in names:
                    chosen = c
                    break
        except Exception:
            # Fallback jika list_models gagal (misal: karena koneksi)
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

    prompt = f"""
    Buatkan saya Lembar Kerja Peserta Didik (LKPD) untuk materi: {theme}.

    LKPD harus menggunakan format Pembelajaran Mendalam (Teoritis Tanpa Perhitungan),
    dengan struktur JSON seperti berikut:
    {{
      "judul": "LKPD Pembelajaran Mendalam: Memahami {theme}",
      "tujuan_pembelajaran": ["...", "...", "..."],
      "materi_singkat": "...",
      "tahapan_pembelajaran": [
        {{
          "tahap": "Memahami Konsep Dasar",
          "deskripsi_tujuan": "...",
          "bagian_inti": "...",
          "petunjuk": "...",
          "pertanyaan_pemantik": [{{ "pertanyaan": "..." }}]
        }},
        {{
          "tahap": "Mengaplikasikan dan Menganalisis",
          "deskripsi_tujuan": "...",
          "bagian_inti": "...",
          "petunjuk": "...",
          "skenario": [
            {{
              "judul": "Skenario Kasus 1: ...",
              "deskripsi": "...",
              "pertanyaan": "Analisis skenario ini dan jelaskan konsep X"
            }}
          ]
        }},
        {{
          "tahap": "Merefleksi dan Menarik Kesimpulan",
          "deskripsi_tujuan": "...",
          "bagian_inti": "...",
          "petunjuk": "...",
          "pertanyaan_pemantik": [{{ "pertanyaan": "Refleksikan pemahaman Anda..." }}]
        }}
      ],
      "jawaban_benar": ["Contoh jawaban umum yang menunjukkan pemahaman konseptual."],
      "format_akhir": "Jawaban Siswa (Nama Siswa: …)"
    }}

    ⚠️ Catatan:
    - Gunakan teks naratif dan reflektif.
    - Tidak boleh ada grafik, tabel, diagram, gambar, atau visual.
    - Hasilkan **hanya** JSON valid sesuai format di atas.
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
def analyze_answer_with_ai(question=None, student_answer=None, lkpd_context=None, *args, **kwargs) -> Dict[str, Any]:
    """
    Fungsi penilaian otomatis AI yang kompatibel dengan app.py
    Mendukung parameter: question, student_answer, lkpd_context
    """
    model = get_model()
    if not model:
        return {"score": 0, "feedback": "Model belum siap."}

    # Backward compatibility for positional arguments
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

    Konteks LKPD (untuk referensi materi dan tujuan):
    {lkpd_context}

    Pertanyaan:
    {question}

    Jawaban siswa:
    {student_answer}

    Instruksi:
    1️⃣ Berikan skor objektif **integer** (0–100) berdasarkan ketepatan konsep dan kedalaman pemahaman.
    2️⃣ Berikan umpan balik singkat dan spesifik.
    
    Format output HARUS persis seperti ini:
    SKOR: [angka integer 0-100]
    FEEDBACK: [teks umpan balik spesifik]
    """

    try:
        resp = model.generate_content(prompt)
        text = getattr(resp, "text", str(resp)) or ""
        score = 0
        feedback = "Gagal memproses feedback dari AI."

        # Ekstraksi Skor
        if "SKOR:" in text:
            try:
                score_line = text.split("SKOR:")[1].split("\n")[0].strip()
                # Hanya ambil angka dari baris skor
                score = int(''.join(c for c in score_line if c.isdigit()) or "0")
            except:
                score = 0

        # Ekstraksi Feedback
        if "FEEDBACK:" in text:
            feedback = text.split("FEEDBACK:")[1].strip()

        return {"score": score, "feedback": feedback}
    
    except Exception as e:
        return {"score": 0, "feedback": f"Analisis gagal karena kesalahan AI: {e}"}


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
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            print(f"Error decoding JSON from {path}")
            return None
    return None
