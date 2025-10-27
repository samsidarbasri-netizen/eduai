import os
import json
import re
import time
from typing import Optional, Dict, Any, Tuple
import google.generativeai as genai


LKPD_DIR = "lkpd_outputs"
ANSWERS_DIR = "answers"
_MODEL = None
_CHOSEN_MODEL_NAME = None


def _extract_json_from_text(text: str) -> Optional[str]:
if not text:
return None
cleaned = text.replace("```json", "").replace("```", "").strip()
m = re.search(r'\{.*\}', cleaned, re.DOTALL)
return m.group(0) if m else cleaned


def init_model(api_key: Optional[str]) -> Tuple[bool, str, Dict[str, Any]]:
global _MODEL, _CHOSEN_MODEL_NAME
debug = {}
try:
if not api_key or not isinstance(api_key, str) or api_key.strip() == "":
return False, "API key kosong atau tidak valid.", debug


genai.configure(api_key=api_key)


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


_MODEL = genai.GenerativeModel(chosen)
_CHOSEN_MODEL_NAME = chosen
debug['chosen_model'] = chosen
return True, f"Model initialized: {chosen}", debug


except Exception as e:
return False, f"Unexpected init error: {type(e).__name__}: {e}", debug


def get_model():
