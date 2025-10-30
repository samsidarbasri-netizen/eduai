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
def generate_lkpd(theme: str, readiness_instruction: str, max_retry: int = 1) -> Tuple[Optional[Dict[str, Any]], Dict[str, Any]]:
    """
    Menghasilkan LKPD format Pembelajaran Mendalam, menyesuaikan materi
    berdasarkan tema dan instruksi kesiapan (readiness_instruction).
    """
    debug = {"chosen_model": _CHOSEN_MODEL_NAME}
    model = get_model()
    if not model:
        debug["error"] = "Model not initialized"
        return None, debug

    # Prompt yang diperbarui
    prompt = f"""
    Buatkan saya Lembar Kerja Peserta Didik (LKPD) untuk materi: {theme}.

    Instruksi Kesiapan Siswa (Readiness Level): **{readiness_instruction}**.
    
    Tugas utama Anda terbagi dua:
    1.  **PENYESUAIAN MATERI AWAL (Kesiapan):** Anda harus menyesuaikan kedalaman, detail, dan tingkat scaffolding pada bagian "materi_singkat" di tahap 'Memahami' LKPD agar sesuai dengan instruksi kesiapan di atas.
        * Jika kesiapan rendah (Skala 1-2), berikan penjelasan yang sangat rinci dan banyak scaffolding.
        * Jika kesiapan tinggi (Skala 4-5), berikan ringkasan singkat atau langsung ke konsep kompleks dan detail.
    
    2.  **PENYESUAIAN BOBOT PERTANYAAN (Kognitif):** Setiap pertanyaan (baik pemantik maupun skenario) harus memiliki field 'level_kognitif' (dari 1 sampai 5) dan 'bobot' (poin maksimumnya). Gunakan bobot poin tetap berikut berdasarkan level kognitif (Taksonomi Bloom):
        * **Level 1 (Mengingat):** Bobot 10
        * **Level 2 (Memahami):** Bobot 15
        * **Level 3 (Mengaplikasikan):** Bobot 20
        * **Level 4 (Menganalisis):** Bobot 25
        * **Level 5 (Mencipta/Evaluasi):** Bobot 30

    LKPD harus menggunakan format Pembelajaran Mendalam (Teoritis Tanpa Perhitungan),
    dengan struktur dan format JSON **yang sama persis dengan contoh berikut**:

    {{
      "judul": "LKPD Pembelajaran Mendalam: Memahami {theme}",
      "tujuan_pembelajaran": [
        "Tujuan 1 (kualitatif dan konseptual)",
        "Tujuan 2",
        "Tujuan 3"
      ],
      "materi_singkat": "Penjelasan konsep inti secara naratif, disesuaikan berdasarkan Kesiapan Siswa, tanpa rumus atau perhitungan.",
      "tahapan_pembelajaran": [
        {{
          "tahap": "Memahami",
          "deskripsi_tujuan": "Menelusuri konsep dasar dan makna utama dari materi.",
          "bagian_inti": "Penjelasan inti dari konsep, disesuaikan dengan kesiapan siswa.",
          "petunjuk": "Petunjuk singkat tentang apa yang harus dipahami siswa.",
          "pertanyaan_pemantik": [
            {{"pertanyaan": "Apa konsep utama dari {theme}?", "level_kognitif": 1, "bobot": 10}},
            {{"pertanyaan": "Mengapa konsep ini penting dalam kehidupan sehari-hari?", "level_kognitif": 2, "bobot": 15}},
            {{"pertanyaan": "Bagaimana kamu menjelaskan konsep ini dengan bahasa sederhana?", "level_kognitif": 2, "bobot": 15}}
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
              "pertanyaan": "Bagaimana konsep ini menjelaskan fenomena tersebut?",
              "level_kognitif": 3, "bobot": 20
            }},
            {{
              "judul": "Skenario 2",
              "deskripsi": "Skenario hipotetis lain yang menantang pemahaman konsep.",
              "pertanyaan": "Apa hubungan antara konsep dan hasil yang terjadi?",
              "level_kognitif": 4, "bobot": 25
            }},
            {{
              "judul": "Skenario 3",
              "deskripsi": "Skenario reflektif yang melibatkan penerapan konsep pada konteks baru.",
              "pertanyaan": "Bagaimana kamu akan memecahkan masalah ini dengan konsep {theme}?",
              "level_kognitif": 4, "bobot": 25
            }}
          ]
        }},
        {{
          "tahap": "Merefleksi",
          "deskripsi_tujuan": "Mengajak siswa merenungkan pemahaman dan penerapan konsep.",
          "bagian_inti": "Refleksi konseptual terhadap makna dan implikasi materi.",
          "petunjuk": "Jawablah dengan jujur berdasarkan pemahaman pribadi.",
          "pertanyaan_pemantik": [
            {{"pertanyaan": "Apa yang kamu pelajari dari proses memahami konsep ini?", "level_kognitif": 3, "bobot": 20}},
            {{"pertanyaan": "Bagaimana penerapan konsep ini dapat mengubah cara pandangmu?", "level_kognitif": 5, "bobot": 30}},
            {{"pertanyaan": "Bagian mana dari materi ini yang paling bermakna bagimu?", "level_kognitif": 5, "bobot": 30}}
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
def analyze_answer_with_ai(question_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    AI memberikan penilaian semi-otomatis (Skor 0-100)
    dengan konteks pertanyaan dan bobot yang tersedia di question_data.
    """
    model = get_model()
    if not model:
        return {"score": 0, "feedback": "Model belum siap."}

    question_text = question_data.get("pertanyaan", "")
    answer_text = question_data.get("jawaban", "")
    bobot = question_data.get("bobot", 10)
    level = question_data.get("level_kognitif", 1)

    if not answer_text or not answer_text.strip():
        return {"score": 0, "feedback": "Siswa tidak menjawab."}

    prompt = f"""
    Anda adalah seorang penilai ahli. Analisis kualitas jawaban siswa berikut berdasarkan ketepatan konsep dan kedalaman pemahaman.
    
    Tingkat Kognitif Pertanyaan: Level {level} (Bobot Maks: {bobot} Poin)

    **Pertanyaan:**
    \"\"\"{question_text}\"\"\"

    **Jawaban Siswa:**
    \"\"\"{answer_text}\"\"\" 

    Berikan skor dalam skala 0–100 (persentase ketepatan) dan analisis singkat.
    Format output HARUS JSON valid:
    {{
      "score": <angka_integer_0_hingga_100>,
      "feedback": "<analisis singkat dan konstruktif, kurang dari 20 kata>"
    }}
    """
    try:
        resp = model.generate_content(prompt)
        text = getattr(resp, "text", str(resp))
        js = _extract_json_from_text(text)
        
        try:
            data = json.loads(js)
            # Pastikan score adalah int
            data["score"] = int(data.get("score", 0))
            return data
        except (json.JSONDecodeError, ValueError):
            return {"score": 0, "feedback": f"Analisis gagal parsing JSON. Jawaban: {js[:50]}..."}

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
