import google.generativeai as genai
import streamlit as st

def setup_gemini():
    try:
        # Ambil API key dari secrets
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

        # Gunakan model yang benar dan stabil
        model = genai.GenerativeModel("models/gemini-1.5-flash-latest")

        return model

    except KeyError:
        st.error("❌ Kunci API belum diset di Streamlit Secrets.")
        return None
    except Exception as e:
        st.error(f"⚠️ Terjadi kesalahan konfigurasi model: {e}")
        return None
