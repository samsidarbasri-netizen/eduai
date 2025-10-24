import streamlit as st
import google.generativeai as genai
import os
import json

# =========================
# INIT GEMINI
# =========================
@st.cache_resource
def get_model():
    try:
        if "GEMINI_API_KEY" not in st.secrets:
            st.error("❌ GEMINI_API_KEY belum diset di Secrets.")
            st.stop()
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        return genai.GenerativeModel("gemini-2.5-flash")
    except Exception as e:
        st.error(f"❌ Gagal inisialisasi Gemini: {e}")
        st.stop()

model = get_model()

# =========================
# GENERATE LKPD
# =========================
@st.cache_data
def generate_lkpd(theme):
    prompt = f"""
    Buat LKPD interaktif untuk tema "{theme}" dalam format JSON (tanpa markdown):
    {{
      "judul": "Judul LKPD",
      "tujuan_pembelajaran": ["Tujuan 1", "Tujuan 2"],
      "materi_singkat": "Penjelasan singkat 1 paragraf",
      "kegiatan": [
        {{
          "nama": "Kegiatan 1",
          "petunjuk": "Petunjuk langkah kegiatan",
          "tugas_interaktif": ["Tugas 1", "Tugas 2"],
          "pertanyaan_pemantik": [
            {{"pertanyaan": "Pertanyaan 1"}},
            {{"pertanyaan": "Pertanyaan 2"}}
          ]
        }}
      ]
    }}
    """
    try:
        response = model.generate_content(prompt)
        text = response.text.strip().replace("```json", "").replace("```", "")
        return json.loads(text)
    except json.JSONDecodeError:
        st.error("❌ Format JSON dari AI tidak valid.")
        return None
    except Exception as e:
        st.error(f"❌ Gagal generate LKPD: {e}")
        return None

# =========================
# FILE STORAGE (VOLATILE)
# =========================
LKPD_DIR = "lkpd_outputs"

def save_lkpd(lkpd_id, data):
    os.makedirs(LKPD_DIR, exist_ok=True)
    path = os.path.join(LKPD_DIR, f"{lkpd_id}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return True

def load_lkpd(lkpd_id):
    path = os.path.join(LKPD_DIR, f"{lkpd_id}.json")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None
