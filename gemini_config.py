"""
gemini_config.py (versi final — stabil & berbobot)

Fungsi utama:
- init_model(api_key): inisialisasi koneksi Gemini
- list_available_models(): memeriksa model
- generate_lkpd(theme): menghasilkan LKPD berbobot berbasis HOTS
- save_json() & load_json(): penyimpanan aman lokal

Struktur LKPD yang dihasilkan:
{
  "judul": "Judul LKPD",
  "kompetensi_dasar": "KD terkait",
  "tujuan_pembelajaran": ["Tujuan 1", "Tujuan 2"],
  "materi_singkat": "Ringkasan 1 paragraf",
  "kegiatan": [
    {"nama": "...", "petunjuk": "...", "pertanyaan_pemantik": [{"pertanyaan": "..."}]}
  ],
  "jawaban_benar": ["Contoh jawaban 1", "Contoh jawaban 2"]
}
"""

import os
import json
import re
import time
from typing import Optional, Dict, Any, Tuple
import google.generativeai as genai

# Folder lokal untuk simpan data
LKPD_DIR = "lkpd_outputs"
ANSWERS_DIR = "answers"

# Variabel global model
_MODEL = None
_CHOSEN_MODEL_NAME = None


# -------------------------------------------------------------
# Utilitas internal
# -------------------------------------------------------------
def _extract_json_from_text(text: str) -> Optional[str]:
    """Ambil blok JSON dari teks balasan Gemini."""
    if not text:
        return None
    cleaned = text.replace("```json", "").replace("```", "").strip()
    m = re.search(r'\{.*\}', cleaned, re.DOTALL)
    return m.group(0) if m else cleaned


# -------------------------------------------------------------
# Inisialisasi model
# -------------------------------------------------------------
def init_model(api_key: Optional[str]) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Inisialisasi Gemini model. Mengembalikan (ok, pesan, debug).
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
            debug["available_models"] = model_names
        except Exception as e:
            debug["list_models_error"] = f"{type(e).__name__}: {e}"
            model_names = []

        # Pilih model terbaik yang tersedia
        candidates = [
            "models/gemini-2.5-flash",
            "gemini-2.5-flash",
            "models/gemini-1.5-flash",
            "gemini-1.5-flash",
            "gemini-1.5"
        ]
        chosen = None
        for c in candidates:
            if not model_names or c in model_names:
                chosen = c
                break
        if not chosen:
            chosen = "models/gemini-1.5-flash"

        # Buat model instance
        try:
            _MODEL = genai.GenerativeModel(chosen)
            _CHOSEN_MODEL_NAME = chosen
            debug["chosen_model"] = chosen
            return True, f"Model diinisialisasi: {chosen}", debug
        except Exception as e:
            debug["init_model_error"] = f"{type(e).__name__}: {e}"
            _MODEL = genai.GenerativeModel("gemini-1.5-flash")
            _CHOSEN_MODEL_NAME = "gemini-1.5-flash"
            debug["fallback_used"] = "gemini-1.5-flash"
            return True, "Model fallback gemini-1.5-flash digunakan.", debug

    except Exception as e:
        return False, f"Error inisialisasi: {type(e).__name__}: {e}", debug


# -------------------------------------------------------------
# Dapatkan model aktif
# -------------------------------------------------------------
def get_model():
    return _MODEL


# -------------------------------------------------------------
# List model
# -------------------------------------------------------------
def list_available_models() -> Dict[str, Any]:
    try:
        models = genai.list_models()
        return {"ok": True, "count": len(models), "names": [m.name for m in models]}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


# -------------------------------------------------------------
# Generate LKPD berbobot
# -------------------------------------------------------------
def generate_lkpd(theme: str, max_retry: int = 1) -> Tuple[Optional[Dict[str, Any]], Dict[str, Any]]:
    """
    Generate LKPD yang relevan, berbasis HOTS & KD.
    Mengembalikan (data_dict_or_None, debug_info)
    """
    debug = {"chosen_model": _CHOSEN_MODEL_NAME}
    model = get_model()
    if model is None:
        debug["error"] = "Model belum diinisialisasi."
        return None, debug

    prompt = f"""
    Kamu adalah asisten edukatif profesional yang membantu guru membuat LKPD berkualitas tinggi.
    Buat LKPD tematik berbasis HOTS (Higher Order Thinking Skills) untuk tema: "{theme}".
    LKPD harus relevan dengan Kurikulum Merdeka SMA dan mencakup KD, tujuan pembelajaran, kegiatan analitis, dan refleksi nilai sosial.

    OUTPUT hanya JSON valid (tanpa penjelasan tambahan) dengan format berikut:
    {{
      "judul": "LKPD {theme}",
      "kompetensi_dasar": "KD yang paling relevan dengan tema ini.",
      "tujuan_pembelajaran": [
        "Dirumuskan dengan kata kerja operasional (mis. menganalisis, mengevaluasi, mencipta)"
      ],
      "materi_singkat": "Ringkasan konseptual singkat (1 paragraf) yang relevan dan komunikatif.",
      "kegiatan": [
        {{
          "nama": "Kegiatan 1 — Analisis Kasus Sosial",
          "petunjuk": "Baca kasus yang disajikan lalu jawab pertanyaan analisisnya.",
          "pertanyaan_pemantik": [
            {{"pertanyaan": "Apa penyebab utama fenomena ini?"}},
            {{"pertanyaan": "Bagaimana dampaknya terhadap masyarakat?"}},
            {{"pertanyaan": "Solusi apa yang dapat diterapkan?"}}
          ]
        }},
        {{
          "nama": "Kegiatan 2 — Refleksi Nilai Sosial",
          "petunjuk": "Tuliskan pandangan pribadimu berdasarkan nilai sosial dan kemanusiaan.",
          "pertanyaan_pemantik": [
            {{"pertanyaan": "Nilai apa yang dapat kamu pelajari dari kasus ini?"}},
            {{"pertanyaan": "Bagaimana nilai tersebut diterapkan dalam kehidupan sehari-hari?"}}
          ]
        }}
      ],
      "jawaban_benar": [
        "Contoh jawaban yang mencerminkan analisis mendalam, berpikir kritis, dan nilai sosial positif."
      ]
    }}
    Pastikan struktur JSON valid dan seluruh bagian relevan dengan tema "{theme}".
    """

    attempt = 0
    last_raw = None
    while attempt <= max_retry:
        try:
            response = model.generate_content(prompt)
            raw = getattr(response, "text", str(response))
            debug["raw_response"] = raw[:3000] if raw else ""
            last_raw = raw

            json_part = _extract_json_from_text(raw)
            if not json_part:
                debug["parse_error"] = "Tidak ditemukan blok JSON."
                raise ValueError("No JSON block found")

            start = json_part.find("{")
            end = json_part.rfind("}")
            if start == -1 or end == -1:
                debug["parse_error"] = "JSON rusak."
                raise ValueError("Malformed JSON block")

            json_str = json_part[start:end + 1]
            data = json.loads(json_str)
            debug["success"] = True
            return data, debug

        except Exception as e:
            debug.setdefault("attempts", []).append(
                {"attempt": attempt, "error": f"{type(e).__name__}: {e}"}
            )
            attempt += 1
            time.sleep(0.8 * attempt)
            if attempt > max_retry:
                if last_raw:
                    debug["last_raw"] = last_raw[:5000]
                return None, debug


# -------------------------------------------------------------
# Simpan & muat JSON
# -------------------------------------------------------------
def save_json(folder: str, file_id: str, data: dict):
    """Simpan JSON ke folder tertentu."""
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, f"{file_id}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_json(folder: str, file_id: str):
    """Muat JSON jika tersedia."""
    path = os.path.join(folder, f"{file_id}.json")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None
