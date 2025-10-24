"""
gemini_config.py
Modul konfigurasi dan utilitas untuk berinteraksi dengan Google Gemini (genai).
Dirancang agar aman untuk diimport oleh app.py (tidak memanggil st.stop() di top-level).
Ekspor fungsi/fasilitas:
- init_model() -> menginisialisasi model (dipanggil sekali oleh app)
- get_model() -> mengembalikan instance model bila telah diinisialisasi
- generate_lkpd(theme) -> generate LKPD (mengembalikan dict atau None)
- evaluate_answer_with_ai(answer_text, question_text="") -> struktur hasil evaluasi
- save_lkpd(lkpd_id, data), load_lkpd(lkpd_id)
"""

import os
import json
import re
import traceback
from typing import Optional, Dict, Any, Tuple

# Late imports to avoid heavy side-effects at import-time in some environments
import google.generativeai as genai

# Local storage dir (volatile in Streamlit Cloud)
LKPD_DIR = "lkpd_outputs"
EVAL_CSV = "evaluations.csv"

# Internal model holder
_MODEL = None

def init_model(api_key: Optional[str]) -> Tuple[bool, str]:
    """
    Initialize the Gemini model. Returns (success, message).
    - api_key: supply API key (string). If None, caller should handle.
    This function does NOT call streamlit; app.py handles secrets and UI messages.
    """
    global _MODEL
    try:
        if not api_key or not isinstance(api_key, str) or api_key.strip() == "":
            return False, "API key is empty or invalid."

        genai.configure(api_key=api_key)
        # Use model compatible with google-generativeai==0.8.5
        _MODEL = genai.GenerativeModel("models/gemini-1.5-flash")
        return True, "Model initialized."
    except Exception as e:
        return False, f"Model init error: {type(e).__name__}: {e}"

def get_model():
    """Return model instance or None."""
    return _MODEL

# ---------- Utility: safe JSON extraction ----------
def _extract_json_from_text(text: str) -> Optional[str]:
    if not text:
        return None
    cleaned = text.replace("```json", "").replace("```", "").strip()
    m = re.search(r'\{.*\}', cleaned, re.DOTALL)
    return m.group(0) if m else cleaned

# ---------- Generate LKPD ----------
def generate_lkpd(theme: str) -> Optional[Dict[str, Any]]:
    """
    Generate LKPD as Python dict. Returns None on failure.
    This function assumes model has been initialized.
    """
    model = get_model()
    if model is None:
        return None

    prompt = f"""
    Buat LKPD interaktif untuk tema "{theme}".
    Output **HANYA** JSON valid.
    Format contoh:
    {{
      "judul": "Judul LKPD",
      "tujuan_pembelajaran": ["Tujuan 1","Tujuan 2"],
      "materi_singkat": "Ringkasan 1 paragraf.",
      "kegiatan": [
        {{
          "nama":"Kegiatan 1",
          "petunjuk":"Petunjuk singkat",
          "tugas_interaktif":["Tugas A"],
          "pertanyaan_pemantik":[{{"pertanyaan":"Pertanyaan 1"}}]
        }}
      ]
    }}
    """

    try:
        response = model.generate_content(prompt)
        raw = getattr(response, "text", str(response))
        json_part = _extract_json_from_text(raw)
        if not json_part:
            return None
        start = json_part.find("{")
        end = json_part.rfind("}")
        if start == -1 or end == -1:
            return None
        json_str = json_part[start:end+1]
        data = json.loads(json_str)
        return data
    except Exception:
        # Do not raise; return None for app to display friendly message
        return None

# ---------- Evaluate answer semi-structured ----------
def evaluate_answer_with_ai(answer_text: str, question_text: str = "") -> Dict[str, Any]:
    """
    Returns dict with keys:
    - overall_score (int)
    - score_breakdown (dict)
    - feedback (str)
    - recommendation (str)
    - raw (raw model text)
    - error (optional)
    """
    model = get_model()
    if model is None:
        return {"error": "Model not initialized."}

    prompt = f"""
    You are an expert teacher evaluator. Output JSON only.
    Fields:
      - overall_score: integer 0-100
      - score_breakdown: {{ "concept":int, "analysis":int, "context":int, "reflection":int }}
      - feedback: short constructive feedback (1-3 sentences)
      - recommendation: 1-2 actionable tips

    Question: {question_text}
    Student Answer: {answer_text}
    """

    try:
        response = model.generate_content(prompt)
        raw = getattr(response, "text", str(response))
        json_part = _extract_json_from_text(raw)
        if not json_part:
            return {"error": "No JSON found in model response", "raw": raw}

        parsed = json.loads(json_part)
        overall = int(parsed.get("overall_score", parsed.get("overall", 0) or 0))
        breakdown = parsed.get("score_breakdown", parsed.get("breakdown", {}))
        score_breakdown = {
            "concept": int(breakdown.get("concept", 0)),
            "analysis": int(breakdown.get("analysis", 0)),
            "context": int(breakdown.get("context", 0)),
            "reflection": int(breakdown.get("reflection", 0))
        }
        feedback = parsed.get("feedback", "")
        recommendation = parsed.get("recommendation", "")

        return {
            "overall_score": max(0, min(100, overall)),
            "score_breakdown": score_breakdown,
            "feedback": feedback,
            "recommendation": recommendation,
            "raw": raw
        }
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "raw": str(e)}

# ---------- File storage (volatile) ----------
def _ensure_dir():
    os.makedirs(LKPD_DIR, exist_ok=True)

def save_lkpd(lkpd_id: str, data: Dict[str, Any]) -> bool:
    try:
        _ensure_dir()
        path = os.path.join(LKPD_DIR, f"{lkpd_id}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False

def load_lkpd(lkpd_id: str) -> Optional[Dict[str, Any]]:
    path = os.path.join(LKPD_DIR, f"{lkpd_id}.json")
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None
    return None
