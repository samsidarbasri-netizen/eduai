import google.generativeai as genai
import textwrap
import logging

# Setup logging untuk debugging profesional
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s — %(message)s"
)

# Konfigurasi API Gemini
def configure_api(api_key: str):
    if not api_key:
        raise ValueError("❌ API key Gemini belum diatur di secrets.toml")
    genai.configure(api_key=api_key)
    logging.info("✅ Gemini API dikonfigurasi dengan benar.")


# Fungsi utama untuk menghasilkan LKPD
def generate_lkpd(prompt: str, difficulty: str = "Sedang") -> str:
    """
    Generate LKPD (Lembar Kerja Peserta Didik) berbasis AI menggunakan Gemini.
    """

    # Pastikan parameter valid
    if not prompt or len(prompt.strip()) == 0:
        raise ValueError("Prompt tidak boleh kosong.")

    # Normalisasi difficulty agar tipe data konsisten
    difficulty_map = {"Mudah": 1, "Sedang": 2, "Sulit": 3}
    diff_value = difficulty_map.get(str(difficulty).capitalize(), 2)

    # Pilih model terbaru dan stabil
    model_name = "models/gemini-1.5-flash-latest"

    try:
        model = genai.GenerativeModel(model_name)

        # Prompt utama ke AI
        full_prompt = textwrap.dedent(f"""
        Anda adalah asisten guru profesional.
        Buatkan satu LKPD interaktif berbasis proyek dengan tingkat kesulitan {difficulty}
        sesuai topik berikut:

        🧩 Topik: {prompt}

        Sertakan:
        1. Tujuan Pembelajaran
        2. Langkah Kegiatan (literasi, diskusi, presentasi, refleksi)
        3. Pertanyaan Pemantik
        4. Lembar Kerja Siswa (dalam format tabel atau poin)
        5. Refleksi & Penilaian Diri

        Gunakan bahasa yang komunikatif, rapi, dan sesuai untuk jenjang SMA/SMK.
        """)

        response = model.generate_content(full_prompt)
        lkpd_text = response.text.strip()

        if not lkpd_text:
            raise ValueError("Respon model kosong. Coba ulang dengan prompt berbeda.")

        logging.info(f"✅ LKPD berhasil dihasilkan dengan tingkat kesulitan {difficulty}.")
        return lkpd_text

    except Exception as e:
        logging.error(f"❌ Terjadi kesalahan saat generate LKPD: {e}")
        raise RuntimeError(f"Gagal menghasilkan LKPD: {e}")
🎨 app.py — (versi final, siap deploy Streamlit)
python
Copy code
import streamlit as st
from gemini_config import configure_api, generate_lkpd

# Judul aplikasi
st.set_page_config(page_title="EduAI LMS - LKPD Generator", page_icon="🎓", layout="wide")

# Header
st.title("🎓 EduAI LKPD Generator")
st.write("Bangun **Lembar Kerja Peserta Didik (LKPD)** secara otomatis menggunakan **Google Gemini AI**.")

# Sidebar konfigurasi
st.sidebar.header("⚙️ Pengaturan")
api_key = st.sidebar.text_input("Masukkan API Key Gemini Anda:", type="password")

difficulty = st.sidebar.selectbox(
    "Tingkat Kesulitan LKPD:",
    ["Mudah", "Sedang", "Sulit"],
    index=1
)

# Input utama dari pengguna
st.subheader("🧩 Masukkan Topik atau Materi Pembelajaran")
prompt = st.text_area("Contoh: Hukum Newton II dalam kehidupan sehari-hari", height=120)

# Tombol generate
if st.button("🚀 Generate LKPD", use_container_width=True):
    if not api_key:
        st.error("❌ Masukkan API key terlebih dahulu di sidebar!")
    elif not prompt.strip():
        st.error("⚠️ Mohon isi topik pembelajaran terlebih dahulu.")
    else:
        try:
            with st.spinner("⏳ Sedang menghasilkan LKPD... harap tunggu sebentar..."):
                configure_api(api_key)
                lkpd_text = generate_lkpd(prompt, difficulty)
                st.success("✅ LKPD berhasil dibuat!")

                # Tampilkan hasilnya
                st.markdown("---")
                st.markdown("## 📘 Hasil LKPD")
                st.markdown(lkpd_text)

                # Tombol download
                st.download_button(
                    label="💾 Unduh LKPD (.txt)",
                    data=lkpd_text,
                    file_name=f"LKPD_{prompt[:30].replace(' ', '_')}.txt",
                    mime="text/plain"
                )

        except Exception as e:
            st.error(f"Terjadi kesalahan: {e}")
