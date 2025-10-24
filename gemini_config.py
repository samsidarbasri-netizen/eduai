import streamlit as st
import google.generativeai as genai

def setup_gemini():
    """Konfigurasi Gemini API dengan aman"""
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        model = genai.GenerativeModel("gemini-1.5-flash")
        return model
    except Exception as e:
        st.error(f"Gagal konfigurasi Gemini API: {e}")
        return None
