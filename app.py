import streamlit as st
from gemini_config import setup_gemini

# -------------------------------
# KONFIGURASI HALAMAN
# -------------------------------
st.set_page_config(
    page_title="📘 Generator LKPD/LMS Berbasis AI",
    page_icon="🤖",
    layout="wide"
)

# -------------------------------
# HEADER APLIKASI
# -------------------------------
st.title("📘 Generator LKPD / LMS Berbasis AI (Gemini + Streamlit)")
st.caption("Dibuat untuk membantu guru menyusun LKPD/LMS otomatis berbasis topik pembelajaran menggunakan Gemini AI.")

st.markdown("---")

# -------------------------------
# INPUT TOPIK PEMBELAJARAN
# -------------------------------
st.subheader("🎯 Masukkan Topik Pembelajaran")
topic = st.text_input(
    "Contoh: Sosialisasi dalam Masyarakat",
    placeholder="Tulis topik pembelajaran di sini..."
)

# -------------------------------
# TOMBOL TES KONEKSI API
# -------------------------------
with st.expander("🧠 Tes Koneksi API (opsional)"):
    if st.button("Tes Koneksi Model Gemini"):
        model = setup_gemini()
        if model:
            st.success("✅ Model Gemini terhubung dan siap digunakan!")
        else:
            st.error("❌ Model belum bisa diakses. Periksa kunci API di Streamlit Secrets.")

# -------------------------------
# TOMBOL GENERATE LKPD
# -------------------------------
if st.button("✨ Generate LKPD / LMS"):
    if not topic.strip():
        st.warning("⚠️ Silakan isi topik terlebih dahulu.")
    else:
        st.info("⏳ Sedang membuat LKPD berbasis AI... Mohon tunggu beberapa saat.")

        model = setup_gemini()
        if model:
            try:
                # PROMPT INTELIJEN UNTUK GEMINI
                prompt = f"""
                Buatkan LKPD (Lembar Kerja Peserta Didik) mata pelajaran Sosiologi dengan topik "{topic}".
                LKPD harus memuat komponen berikut:
                1. Tujuan Pembelajaran yang selaras dengan Profil Pelajar Pancasila.
                2. Pengantar Materi (dengan bahasa komunikatif dan kontekstual).
                3. Studi Kasus aktual yang relevan.
                4. Pertanyaan Diskusi analitis (minimal 5).
                5. Refleksi Diri Peserta Didik.
                6. Rekomendasi aktivitas kolaboratif (guru + siswa).
                Gunakan bahasa Indonesia yang jelas, ringkas, dan mendorong berpikir kritis.
                """

                response = model.generate_content(prompt)

                st.success("✅ LKPD berhasil dibuat!")
                st.markdown("### 📄 Hasil LKPD / LMS")
                st.markdown("---")
                st.write(response.text)

                # Tombol simpan hasil
                st.download_button(
                    label="💾 Unduh LKPD sebagai TXT",
                    data=response.text,
                    file_name=f"LKPD_{topic.replace(' ', '_')}.txt",
                    mime="text/plain"
                )

            except Exception as e:
                st.error(f"🚨 Terjadi kesalahan saat memanggil Gemini API: {e}")
        else:
            st.error("❌ Model tidak berhasil dikonfigurasi. Periksa kunci API di .streamlit/secrets.toml")

# -------------------------------
# FOOTER
# -------------------------------
st.markdown("---")
st.caption("💡 Dibangun dengan Streamlit + Gemini API | Aman & bebas pemanggilan berulang otomatis")
