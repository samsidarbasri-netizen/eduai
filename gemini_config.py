# Tambahkan ke gemini_config.py (di bawah inisialisasi model)
import re
import json
from typing import Dict, Any, Optional

def _extract_json_from_text(text: str) -> Optional[str]:
    """
    Ambil blok JSON dari text (menghapus ```json fences, teks di depan/akhir).
    """
    if not text:
        return None
    # bersihkan fences
    cleaned = text.replace("```json", "").replace("```", "").strip()
    # ambil substring pertama yang berbentuk {...}
    m = re.search(r'\{.*\}', cleaned, re.DOTALL)
    return m.group(0) if m else cleaned

def evaluate_answer_with_ai(answer_text: str, question_text: str = "") -> Dict[str, Any]:
    """
    Minta Gemini menilai jawaban siswa secara terstruktur.
    Mengembalikan dict: {
        "overall_score": int,
        "score_breakdown": {"concept":int,"analysis":int,"context":int,"reflection":int},
        "feedback": str,
        "recommendation": str,
        "raw": raw_response_text
    }
    """
    if not answer_text:
        return {"error": "Empty answer_text provided."}

    # Pastikan model tersedia (global model variable dari file)
    global model
    if model is None:
        return {"error": "Model not initialized."}

    # Prompt: meminta output JSON yang jelas
    prompt = f"""
You are an expert teacher evaluator. Given a student's answer, produce a JSON object only (no other text)
with the following fields:
- overall_score: integer from 0 to 100 (rounded)
- score_breakdown: object with integers 0-100 for keys: "concept", "analysis", "context", "reflection"
- feedback: short constructive feedback (1-3 sentences)
- recommendation: 1-2 actionable tips for student improvement

Input:
Question: {question_text}
Student Answer: {answer_text}

Provide JSON only.
"""

    try:
        # Panggil model sekali, button-triggered
        response = model.generate_content(prompt)
        raw_text = getattr(response, "text", str(response))
        json_part = _extract_json_from_text(raw_text)
        if not json_part:
            return {"error": "No JSON found in model response", "raw": raw_text}

        try:
            parsed = json.loads(json_part)
        except json.JSONDecodeError:
            # coba lagi membersihkan (fallback)
            json_part2 = json_part.strip().strip('`').strip()
            parsed = json.loads(json_part2)

        # Normalize: pastikan keys & types
        overall = int(parsed.get("overall_score", parsed.get("overall", 0) or 0))
        breakdown = parsed.get("score_breakdown", parsed.get("breakdown", {}))
        # coerce breakdown values
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
            "raw": raw_text
        }

    except Exception as e:
        return {"error": f"Exception during evaluation: {type(e).__name__}: {e}"}
