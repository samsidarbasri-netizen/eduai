import streamlit as st
from gemini_config import setup_gemini

# -------------------------------
# KONFIGURASI HALAMAN
# -------------------------------
st.set_page_config(
    page_title="📘 Generator & Evaluator LKPD AI",
    page_icon="🤖",
    layout="wide"
)

# -------------------------------
# HEADER APLIKASI
# -------------------------------
st.title("📘 Generator & Evaluator LKPD / LMS Berbasis AI")
st.caption("Guru dapat membuat LKPD otomatis dan mengevaluasi jawaban siswa secara semi-otomatis dengan bantuan Gemini AI.")
st.markdown("---")

# -------------------------------
# PILIH PERAN
# -------------------------------
st.sidebar.header("🔐 Pilih Mode Pengguna")
role = st.sidebar.radio("Pilih peran Anda:", ["👨🏫 Guru", "👩‍🎓 Siswa"])

model = setup_gemini()

# ==========================================================
# MODE SISWA
# ==========================================================
if role == "👩‍🎓 Siswa":
    st.subheader("🎯 Pengisian LKPD / LMS oleh Siswa")
    st.caption("Isi topik yang diberikan guru, lalu kirim jawaban Anda di bawah.")
    
    topic = st.text_input("Topik LKPD dari Guru", placeholder="Contoh: Sosialisasi dalam masyarakat")
    answer = st.text_area("✏️ Jawaban Anda", placeholder="Tulis jawaban lengkap Anda di sini...", height=200)

    if st.button("📤 Kirim Jawaban"):
        if not topic or not answer.strip():
            st.warning("⚠️ Lengkapi topik dan jawaban terlebih dahulu.")
        else:
            st.success("✅ Jawaban Anda sudah dikirim. Guru akan menilai secara semi-otomatis.")

# ==========================================================
# MODE GURU
# ==========================================================
elif role == "👨🏫 Guru":
    st.subheader("🧩 Pembuatan LKPD / LMS Otomatis")
    topic = st.text_input("Masukkan Topik Pembelajaran", placeholder="Contoh: Sosialisasi dalam masyarakat")

    if st.button("✨ Generate LKPD / LMS"):
        if not topic.strip():
            st.warning("⚠️ Silakan isi topik terlebih dahulu.")
        else:
            st.info("⏳ Sedang membuat LKPD berbasis AI... Mohon tunggu sebentar.")
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
                    st.success("✅ LKPD berhasil dibuat!")
                    st.markdown("### 📄 Hasil LKPD / LMS")
                    st.markdown("---")
                    st.write(response.text)
                    st.download_button(
                        label="💾 Unduh LKPD sebagai TXT",
                        data=response.text,
                        file_name=f"LKPD_{topic.replace(' ', '_')}.txt",
                        mime="text/plain"
                    )
                except Exception as e:
                    st.error(f"🚨 Terjadi kesalahan saat memanggil Gemini API: {e}")
            else:
                st.error("❌ Model belum terkonfigurasi dengan benar. Periksa API key Anda.")

    st.markdown("---")
    st.subheader("🧾 Evaluasi Jawaban (Semi-Otomatis)")
    st.caption("Tempel jawaban siswa di bawah, lalu klik **AI Evaluate** untuk analisis otomatis. Guru tetap dapat menyesuaikan skor akhir.")

    # Input jawaban siswa untuk evaluasi
    student_answer = st.text_area("📋 Tempel Jawaban Siswa di Sini", height=200, placeholder="Salin jawaban siswa...")

    if st.button("🤖 AI Evaluate"):
        if not student_answer.strip():
            st.warning("⚠️ Tempel jawaban siswa terlebih dahulu.")
        else:
            st.info("⏳ AI sedang menganalisis jawaban siswa...")
            if model:
                try:
                    eval_prompt = f"""
                    Analisis jawaban siswa berikut untuk topik pembelajaran Sosiologi.
                    Berikan hasil dalam format berikut:
                    - **Analisis Kualitas Jawaban**
                    - **Aspek yang Sudah Baik**
                    - **Aspek yang Perlu Diperbaiki**
                    - **Skor Sementara (0–100)**
                    - **Saran untuk Guru**
                    Jawaban siswa:
                    {student_answer}
                    """
                    eval_response = model.generate_content(eval_prompt)
                    st.success("✅ Analisis selesai!")
                    st.markdown("### 📊 Hasil Evaluasi AI")
                    st.write(eval_response.text)

                    st.markdown("### ✍️ Penyesuaian Guru (Opsional)")
                    final_score = st.slider("Sesuaikan skor akhir (0–100):", 0, 100, 80)
                    st.text_area("Catatan Guru (opsional):", placeholder="Tulis masukan atau koreksi Anda di sini...")
                    st.button("💾 Simpan Penilaian")
                except Exception as e:
                    st.error(f"🚨 Terjadi kesalahan saat analisis AI: {e}")
            else:
                st.error("❌ Model Gemini belum siap digunakan. Periksa API key Anda.")

# -------------------------------
# FOOTER
# -------------------------------
st.markdown("---")
st.caption("💡 Dibangun dengan Streamlit + Gemini API | Mode Guru & Siswa | Evaluasi Semi-Otomatis Aman")
