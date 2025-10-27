"""
gemini_config.py (defensive version with semi-automatic evaluator)

Exports:
 - init_model(api_key) -> (ok:bool, message:str, debug:dict)
 - list_available_models() -> dict
 - get_model()
 - generate_lkpd(theme, max_retry=1) -> (data_or_none, debug)
 - evaluate_answer_with_ai(answer_text, question_text="", max_retry=1) -> dict
 - save_json / load_json helpers

This module does NOT import streamlit at top-level (safe to import).
"""

import os
import json
import re
import time
from typing import Optional, Dict, Any, Tuple

import google.generativeai as genai

# Local storage (volatile on Streamlit Cloud)
LKPD_DIR = "lkpd_outputs"
ANSWERS_DIR = "answers"

_MODEL = None
_CHOSEN_MODEL_NAME = None

def _extract_json_from_text(text: str) -> Optional[str]:
    """Extract first JSON object from text. Return string or None."""
    if not text:
        return None
    cleaned = text.replace("```json", "").replace("```", "").strip()
    # Try to find the outermost JSON object using simple heuristics.
    # This is robust for usual responses where model returns a single {...}.
    m = re.search(r'\{(?:[^{}]|(?R))*\}', cleaned, re.DOTALL)
    if m:
        return m.group(0)
    # fallback: find first { ... last }
    m2 = re.search(r'\{.*\}', cleaned, re.DOTALL)
    return m2.group(0) if m2 else None

def init_model(api_key: Optional[str]) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Initialize genai and select a model if available.
    Returns (ok, message, debug_info)
    """
    global _MODEL, _CHOSEN_MODEL_NAME
    debug = {}
    try:
        if not api_key or not isinstance(api_key, str) or api_key.strip() == "":
            return False, "API key kosong atau tidak valid.", debug

        genai.configure(api_key=api_key)

        # Try to list models once for debug (non-fatal)
        try:
            models = genai.list_models()
            model_names = [m.name for m in models]
            debug['available_models'] = model_names
        except Exception as e:
            debug['list_models_error'] = f"{type(e).__name__}: {e}"
            model_names = []

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

        try:
            _MODEL = genai.GenerativeModel(chosen)
            _CHOSEN_MODEL_NAME = chosen
            debug['chosen_model'] = chosen
            return True, f"Model initialized: {chosen}", debug
        except Exception as e:
            debug['init_model_error'] = f"{type(e).__name__}: {e}"
            # last resort fallback
            try:
                _MODEL = genai.GenerativeModel("gemini-1.5-flash")
                _CHOSEN_MODEL_NAME = "gemini-1.5-flash"
                debug['fallback_used'] = "gemini-1.5-flash"
                return True, "Model initialized with fallback gemini-1.5-flash", debug
            except Exception as e2:
                debug['fallback_error'] = f"{type(e2).__name__}: {e2}"
                return False, f"Failed to initialize model: {e} ; fallback failed: {e2}", debug

    except Exception as e:
        return False, f"Unexpected init error: {type(e).__name__}: {e}", debug

def list_available_models() -> Dict[str, Any]:
    """Return dict with available model names or error details."""
    try:
        models = genai.list_models()
        return {"ok": True, "count": len(models), "names": [m.name for m in models]}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}

def get_model():
    return _MODEL

def generate_lkpd(theme: str, max_retry: int = 1) -> Tuple[Optional[Dict[str, Any]], Dict[str, Any]]:
    """
    Generate LKPD; returns (data_dict_or_None, debug_info)
    """
    debug = {"chosen_model": _CHOSEN_MODEL_NAME}
    model = get_model()
    if model is None:
        debug['error'] = "Model not initialized"
        return None, debug

    prompt = f"""
    Anda adalah perancang bahan ajar. Buatkan sebuah LKPD (Lembar Kerja Peserta Didik)
    untuk tema \"{theme}\" jenjang SMA. OUTPUT HANYA: JSON valid tanpa penjelasan.
    Format contoh:
    {{
      "judul": "Judul LKPD",
      "tujuan_pembelajaran": ["Tujuan 1", "Tujuan 2"],
      "materi_singkat": "Ringkasan 1 paragraf.",
      "kegiatan": [
        {{
          "nama":"Kegiatan 1",
          "petunjuk":"Petunjuk singkat",
          "tugas_interaktif":["Tugas 1","Tugas 2"],
          "pertanyaan_pemantik":[{{"pertanyaan":"Pertanyaan 1"}}]
        }}
      ],
      "jawaban_benar": ["Contoh jawaban 1", "Contoh jawaban 2"]
    }}
    """

    attempt = 0
    last_raw = None
    while attempt <= max_retry:
        try:
            response = model.generate_content(prompt)
            raw = getattr(response, "text", str(response))
            debug['raw_response'] = raw[:8000] if raw else ""
            last_raw = raw

            json_part = _extract_json_from_text(raw)
            if not json_part:
                debug['parse_error'] = "No JSON block found"
                raise ValueError("No JSON block found")

            data = json.loads(json_part)
            debug['success'] = True
            return data, debug

        except Exception as e:
            debug.setdefault('attempts', []).append({"attempt": attempt, "error": f"{type(e).__name__}: {e}"})
            attempt += 1
            time.sleep(0.8 * attempt)
            if attempt > max_retry:
                if last_raw:
                    debug['last_raw'] = last_raw[:8000]
                return None, debug

def evaluate_answer_with_ai(answer_text: str, question_text: str = "", max_retry: int = 1) -> Dict[str, Any]:
    """
    Semi-automatic evaluator.
    Returns dict with keys:
      - overall_score (int 0-100) OR None
      - feedback (str)
      - recommendation (str)
      - breakdown (dict) optional
      - raw (raw model text)
      - error (optional)
    """
    debug = {"chosen_model": _CHOSEN_MODEL_NAME}
    model = get_model()
    if model is None:
        return {"error": "Model not initialized."}

    if not answer_text or not isinstance(answer_text, str):
        return {"error": "Empty or invalid answer_text."}

    prompt = f"""
    Anda adalah seorang guru dan penilai. Berikan penilaian awal untuk jawaban siswa berikut.
    Output: JSON only.
    Fields:
      - overall_score: integer antara 0 dan 100
      - breakdown: {{ "concept": int, "analysis": int, "context": int, "reflection": int }}
      - feedback: short constructive feedback (1-3 sentences)
      - recommendation: 1-2 actionable tips for student

    Question: {question_text}
    Student Answer: {answer_text}
    """

    attempt = 0
    last_raw = None
    while attempt <= max_retry:
        try:
            response = model.generate_content(prompt)
            raw = getattr(response, "text", str(response))
            debug['raw_response'] = raw[:8000] if raw else ""
            last_raw = raw

            json_part = _extract_json_from_text(raw)
            if not json_part:
                return {"error": "No JSON found in model response", "raw": raw}

            parsed = json.loads(json_part)
            # safe extraction with defaults
            overall = parsed.get("overall_score") or parsed.get("overall") or 0
            try:
                overall = int(overall)
            except Exception:
                overall = 0

            breakdown = parsed.get("breakdown") or parsed.get("score_breakdown") or {}
            # normalize
            bd = {
                "concept": int(breakdown.get("concept", 0)),
                "analysis": int(breakdown.get("analysis", 0)),
                "context": int(breakdown.get("context", 0)),
                "reflection": int(breakdown.get("reflection", 0))
            }

            feedback = parsed.get("feedback", "")
            recommendation = parsed.get("recommendation", parsed.get("tips",""))

            result = {
                "overall_score": max(0, min(100, overall)),
                "breakdown": bd,
                "feedback": feedback,
                "recommendation": recommendation,
                "raw": raw
            }
            debug['success'] = True
            result['debug'] = debug
            return result

        except Exception as e:
            debug.setdefault('attempts', []).append({"attempt": attempt, "error": f"{type(e).__name__}: {e}"})
            attempt += 1
            time.sleep(0.6 * attempt)
            if attempt > max_retry:
                if last_raw:
                    debug['last_raw'] = last_raw[:8000]
                return {"error": "Evaluation failed", "debug": debug}

# simple save/load
def save_json(folder: str, file_id: str, data: dict):
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, f"{file_id}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_json(folder: str, file_id: str):
    path = os.path.join(folder, f"{file_id}.json")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None
