import streamlit as st
from gemini_config import setup_gemini

# --- Konfigurasi halaman utama ---
st.set_page_config(
    page_title="📘 Generator LKPD Berbasis AI",
    page_icon="📘",
    layout="wide"
)

# --- Header ---
st.title("📘 Generator LKPD Berbasis AI (Gemini + Streamlit)")
st.caption("Dibuat untuk membantu guru menyusun LKPD/LMS otomatis berbasis topik pembelajaran.")

# --- Input pengguna ---
st.subheader("🧩 Masukkan Topik Pembelajaran")
topic = st.text_input(
    "Contoh: Sosialisasi dalam Masyarakat",
    placeholder="Tulis topik pembelajaran di sini..."
)

# --- Tombol Generate ---
if st.button("🔮 Generate LKPD"):
    if topic.strip() == "":
        st.warning("⚠️ Silakan isi topik terlebih dahulu.")
    else:
        with st.spinner("Sedang membuat LKPD dengan bantuan AI..."):
            model = setup_gemini()
            if model:
                try:
                    prompt = f"""
                    Buatkan LKPD Sosiologi dengan topik "{topic}".
                    LKPD harus memuat:
                    1. Tujuan Pembelajaran
                    2. Pengantar Materi
                    3. Studi Kasus
                    4. Pertanyaan Diskusi
                    5. Refleksi Diri
                    Gunakan bahasa yang komunikatif, sesuai jenjang SMA,
                    dan dorong siswa berpikir kritis.
                    """

                    response = model.generate_content(prompt)
                    st.success("✅ LKPD berhasil dibuat!")
                    st.markdown("---")
                    st.markdown("### 📄 Hasil LKPD")
                    st.write(response.text)
                    
                except Exception as e:
                    st.error(f"Terjadi kesalahan saat memanggil Gemini API: {e}")
            else:
                st.error("Model tidak berhasil dikonfigurasi. Periksa kunci API kamu di .streamlit/secrets.toml")

# --- Footer ---
st.markdown("---")
st.caption("💡 Dibangun dengan Streamlit + Gemini API | Aman & bebas spam API calls")
