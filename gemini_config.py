import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()  # untuk lokal, Streamlit Cloud otomatis lewati ini

def setup_gemini():
    """
    Mengatur koneksi ke Gemini AI dan mengembalikan model generatif yang siap digunakan.
    """
    try:
        # Ambil API key dari .env atau Streamlit secrets
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            import streamlit as st
            api_key = st.secrets["GOOGLE_API_KEY"]

        if not api_key:
            raise ValueError("API key tidak ditemukan di secrets atau .env")

        # Konfigurasi Gemini
        genai.configure(api_key=api_key)

        # Gunakan model yang valid di v1 API
        model = genai.GenerativeModel("gemini-1.5-flash")
        return model

    except Exception as e:
        print(f"⚠️ Kesalahan konfigurasi Gemini: {e}")
        return None
