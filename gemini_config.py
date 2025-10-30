"""
gemini_config.py — FINAL INTERACTIVE-COMPATIBLE VERSION
-----------------------------------------------------
✅ Kompatibel penuh dengan app.py (Streamlit)
✅ Generate LKPD dengan opsi difficulty (mudah/sedang/sulit)
✅ Memperbaiki/menormalkan struktur JSON keluaran model supaya app.py selalu bisa render input siswa
✅ Penilaian AI kompatibel dengan app.py (mengembalikan dict {"score":..,"feedback":..})
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
os.makedirs(LKPD_DIR, exist_ok=True)
os.makedirs(ANSWERS_DIR, exist_ok=True)

_MODEL = None
_CHOSEN_MODEL_NAME = None

# ------------------ Utility ------------------
def _extract_json_from_text(text: str) -> Optional[str]:
    """Ambil blok JSON dari teks mentah hasil model Gemini."""
    if not text:
        return None
    cleaned = text.replace("```json", "").replace("```", "").strip()
    # Cari blok JSON pertama yang tampak valid
    match = re.search(r"\{(?:[^{}]|(?R))*\}", cleaned, re.DOTALL)
    if match:
        return match.group(0)
    # fallback: coba cari kurung kurawal paling luar dengan cara sederhana
    match2 = re.search(r"\{.*\}", cleaned, re.DOTALL)
    return match2.group(0) if match2 else None

def _normalize_lkpd_structure(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Pastikan struktur LKPD sesuai dengan yang diharapkan app.py:
    - tahapan_pembelajaran -> setiap tahap mempunyai:
      - 'pertanyaan_pemantik': list[{"pertanyaan": str}] OR
      - 'skenario': list[{"judul", "deskripsi", "pertanyaan"}]
    Jika model menghasilkan 'pertanyaan' sebagai list of strings, konversi otomatis.
    """
    if not isinstance(data, dict):
        return data

    tahapan = data.get("tahapan_pembelajaran", [])
    if not isinstance(tahapan, list):
        return data

    for tahap in tahapan:
        # Normalisasi pertanyaan pemantik
        if "pertanyaan_pemantik" not in tahap:
            # jika ada 'pertanyaan' berupa list of strings -> ubah ke pertanyaan_pemantik
            if "pertanyaan" in tahap and isinstance(tahap["pertanyaan"], list):
                pemantik = []
                for p in tahap["pertanyaan"]:
                    if isinstance(p, dict) and "pertanyaan" in p:
                        pemantik.append({"pertanyaan": p.get("pertanyaan")})
                    else:
                        pemantik.append({"pertanyaan": str(p)})
                tahap["pertanyaan_pemantik"] = pemantik
                # optional: hapus kunci lama
                try:
                    del tahap["pertanyaan"]
                except KeyError:
                    pass

        else:
            # ensure items are dicts with key 'pertanyaan'
            normalized = []
            for item in tahap.get("pertanyaan_pemantik", []):
                if isinstance(item, dict) and "pertanyaan" in item:
                    normalized.append({"pertanyaan": str(item.get("pertanyaan") or "")})
                else:
                    normalized.append({"pertanyaan": str(item)})
            tahap["pertanyaan_pemantik"] = normalized

        # Normalisasi skenario (untuk tahap Mengaplikasikan)
        if "skenario" in tahap and isinstance(tahap["skenario"], list):
            normalized_sken = []
            for s in tahap["skenario"]:
                if isinstance(s, dict):
                    titulo = s.get("judul", "") or s.get("title", "")
                    deskrip = s.get("deskripsi", "") or s.get("description", "")
                    pert = s.get("pertanyaan", "") or s.get("question", "")
                    normalized_sken.append({
                        "judul": str(titulo),
                        "deskripsi": str(deskrip),
                        "pertanyaan": str(pert)
                    })
                else:
                    # jika hanya string, jadikan sebagai deskripsi dan pertanyaan generik
                    normalized_sken.append({
                        "judul": "",
                        "deskripsi": str(s),
                        "pertanyaan": ""
                    })
            tahap["skenario"] = normalized_sken

    data["tahapan_pembelajaran"] = tahapan
    return data

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
    Menghasilkan LKPD format Pembelajaran Mendalam (Memahami-Mengaplikasikan-Merefleksi)
    dengan parameter difficulty: 'mudah'|'sedang'|'sulit'.
    Keluaran dijamin memiliki struktur yang kompatibel dengan app.py.
    """
    debug = {"chosen_model": _CHOSEN_MODEL_NAME, "difficulty": difficulty}
    model = get_model()
    if not model:
        debug["error"] = "Model not initialized"
        return None, debug

    difficulty_note = {
        "mudah": "Gunakan bahasa sederhana, pertanyaan konsep dasar, contoh sehari-hari.",
        "sedang": "Gunakan bahasa semi-akademik dengan penerapan konsep dan refleksi moderat.",
        "sulit": "Gunakan bahasa analitis, pertanyaan yang memerlukan sintesis dan argumentasi."
    }.get(difficulty.lower(), "Gunakan bahasa semi-akademik (sedang).")

    prompt = f"""
    Buatkan Lembar Kerja Peserta Didik (LKPD) untuk materi: {theme}.
    Tingkat kesulitan: {difficulty.upper()}.
    {difficulty_note}

    Output HARUS berupa JSON valid dengan struktur:
    {{
      "judul":"LKPD Pembelajaran Mendalam: Memahami {theme} ({difficulty.upper()})",
      "tujuan_pembelajaran": ["..."],
      "materi_singkat": "...",
      "tahapan_pembelajaran": [
        {{
          "tahap":"Memahami",
          "deskripsi_tujuan":"...",
          "bagian_inti":"...",
          "petunjuk":"...",
          "pertanyaan_pemantik":[{{"pertanyaan":"..."}}, ...]
        }},
        {{
          "tahap":"Mengaplikasikan",
          "deskripsi_tujuan":"...",
          "bagian_inti":"...",
          "petunjuk":"...",
          "skenario":[{{"judul":"...","deskripsi":"...","pertanyaan":"..."}}, ...]
        }},
        {{
          "tahap":"Merefleksi",
          "deskripsi_tujuan":"...",
          "bagian_inti":"...",
          "petunjuk":"...",
          "pertanyaan_pemantik":[{{"pertanyaan":"..."}}, ...]
        }}
      ],
      "jawaban_benar":["..."],
      "format_akhir":"Jawaban Siswa (Nama Siswa: ...)"
    }}

    HANYA kembalikan JSON. Jangan sertakan teks penjelas lain.
    """

    attempt = 0
    while attempt <= max_retry:
        try:
            resp = model.generate_content(prompt)
            raw = getattr(resp, "text", str(resp)) or ""
            debug["raw_response"] = raw[:4000]
            json_block = _extract_json_from_text(raw)
            if not json_block:
                raise ValueError("Tidak ditemukan blok JSON pada respons model.")
            data = json.loads(json_block)

            # Normalisasi dan perbaikan struktur agar app.py dapat merender
            data = _normalize_lkpd_structure(data)

            # Tambahan: jika tahap ada tetapi tidak memiliki pertanyaan_pemantik/skenario, buat placeholder
            for tahap in data.get("tahapan_pembelajaran", []):
                if "pertanyaan_pemantik" not in tahap:
                    tahap["pertanyaan_pemantik"] = []
                if "skenario" not in tahap:
                    tahap["skenario"] = []

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
    Mengembalikan dict {"score": int, "feedback": str}.
    Jika jawaban kosong -> score 0, feedback "Siswa tidak menjawab."
    """
    model = get_model()
    if not model:
        return {"score": 0, "feedback": "Model belum siap."}

    # backward compatibility for positional args
    if question is None and len(args) > 0:
        question = args[0]
    if student_answer is None and len(args) > 1:
        student_answer = args[1]
    if lkpd_context is None and len(args) > 2:
        lkpd_context = args[2]

    if not student_answer or not str(student_answer).strip():
        return {"score": 0, "feedback": "Siswa tidak menjawab."}

    # prompt yang memaksa keluaran SKOR/FEEDBACK secara sederhana
    prompt = f"""
    Anda adalah sistem penilai otomatis. Beri penilaian terhadap jawaban siswa ini.

    Konteks LKPD: {json.dumps(lkpd_context, ensure_ascii=False) if lkpd_context else 'Tidak ada konteks.'}
    Pertanyaan: {question}
    Jawaban siswa: {student_answer}

    Instruksi:
    - Berikan skor antara 0 dan 100 berdasarkan ketepatan konsep dan kedalaman pemahaman.
    - Berikan umpan balik singkat, jelas, dan mendidik.
    FORMAT KELUARAN HARUS persis:
    SKOR: <angka>
    FEEDBACK: <teks>
    """

    try:
        resp = model.generate_content(prompt)
        text = getattr(resp, "text", str(resp)) or ""
        # cari SKOR dan FEEDBACK
        score = 0
        feedback = "Siswa tidak menjawab."

        if "SKOR:" in text:
            try:
                score_line = text.split("SKOR:")[1].splitlines()[0]
                score = int(''.join(ch for ch in score_line if ch.isdigit()) or "0")
            except Exception:
                score = 0

        if "FEEDBACK:" in text:
            try:
                feedback = text.split("FEEDBACK:")[1].strip()
            except Exception:
                feedback = feedback

        return {"score": score, "feedback": feedback}
    except Exception as e:
        return {"score": 0, "feedback": f"Analisis gagal: {e}"}

# ------------------ File Helpers ------------------
def save_json(folder: str, file_id: str, data: dict):
    """Simpan file JSON secara aman."""
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, f"{file_id}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_json(folder: str, file_id: str):
    """Membaca file JSON bila tersedia."""
    path = os.path.join(folder, f"{file_id}.json")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None
