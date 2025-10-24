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
st.caption("Aplikasi ini membantu guru menyusun LKPD/LMS otomatis berbasis topik pembelajaran menggunakan Gemini AI.")
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
# TES KONEKSI API (Opsional)
# -------------------------------
with st.expander("🧠 Tes Koneksi API (opsional)"):
    if st.button("Tes Koneksi Model Gemini"):
        model = setup_gemini()
        if model:
            st.success("✅ Model Gemini terhubung dan siap digunakan!")
        else:
            st.error("❌ Model belum bisa diakses. Periksa kunci API di Streamlit Secrets.")

# -------------------------------
# GENERATE LKPD / LMS
# -------------------------------
if st.button("✨ Generate LKPD / LMS"):
    if not topic.strip():
        st.warning("⚠️ Silakan isi topik terlebih dahulu.")
    else:
        st.info("⏳ Sedang membuat LKPD berbasis AI... Mohon tunggu beberapa saat.")

        model = setup_gemini()
        if model:
            try:
                prompt = f"""
                Buatkan LKPD (Lembar Kerja Peserta Didik) mata pelajaran Sosiologi dengan topik "{topic}".
                LKPD harus memuat:
                1. Tujuan Pembelajaran (terkait Profil Pelajar Pancasila)
                2. Pengantar Materi
                3. Studi Kasus aktual dan relevan
                4. Pertanyaan Diskusi analitis (5 soal)
                5. Refleksi Diri Peserta Didik
                Gunakan bahasa Indonesia yang komunikatif dan dorong siswa berpikir kritis.
                """

                response = model.generate_content(prompt)
                hasil = response.text.strip() if hasattr(response, "text") else str(response)

                st.success("✅ LKPD berhasil dibuat!")
                st.markdown("### 📄 Hasil LKPD / LMS")
                st.markdown("---")
                st.write(hasil)

                st.download_button(
                    label="💾 Unduh LKPD sebagai TXT",
                    data=hasil,
                    file_name=f"LKPD_{topic.replace(' ', '_')}.txt",
                    mime="text/plain"
                )

            except Exception as e:
                st.error(f"🚨 Terjadi kesalahan saat memanggil Gemini API: {e}")
        else:
            st.error("❌ Model tidak berhasil dikonfigurasi. Periksa API key di .streamlit/secrets.toml")

# -------------------------------
# FOOTER
# -------------------------------
st.markdown("---")
st.caption("💡 Dibangun dengan Streamlit + Gemini API | Aman dan efisien (tanpa pemanggilan berulang otomatis)")
