import streamlit as st
import google.generativeai as genai

def setup_gemini():
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
        genai.configure(api_key=api_key)

        # Model stabil dan sudah support generate_content di v1
        model = genai.GenerativeModel("gemini-1.5-flash")

        return model

    except KeyError:
        st.error("❌ Kunci API belum ditemukan di Streamlit Secrets.")
        return None
    except Exception as e:
        st.error(f"⚠️ Gagal memuat model Gemini: {e}")
        return None
