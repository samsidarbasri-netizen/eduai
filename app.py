import streamlit as st
import json
import os
import uuid
from gemini_config import model, generate_lkpd, save_lkpd, load_lkpd

# =========================
# STREAMLIT PAGE CONFIG
# =========================
st.set_page_config(
    page_title="LMS Interaktif EduAI",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =========================
# SESSION STATE INIT
# =========================
if 'role' not in st.session_state:
    st.session_state.role = None

# =========================
# SIDEBAR ROLE SELECTION
# =========================
with st.sidebar:
    st.title("🎓 Pilih Peran Anda")
    selected_role = st.radio("Saya adalah:", ["👨🏫 Guru", "👩🎓 Siswa"], key="role_radio")
    
    if selected_role and selected_role != st.session_state.role:
        st.session_state.role = selected_role
        st.rerun()

# =========================
# MAIN PAGE
# =========================
st.title("🚀 LMS Interaktif dengan Gemini AI 2.5")
st.markdown("Platform untuk membuat dan mengisi LKPD otomatis menggunakan **Gemini AI**.")

if not st.session_state.role:
    st.warning("👈 Silakan pilih peran Anda di sidebar untuk memulai.")
    st.stop()

# =========================
# MODE GURU
# =========================
if st.session_state.role == "👨🏫 Guru":
    st.header("👨🏫 Mode Guru: Buat LKPD Baru")

    theme = st.text_input("Masukkan Tema / Topik Pembelajaran (Contoh: Fotosintesis, Ekosistem)")
    if st.button("🚀 Generate LKPD", use_container_width=True):
        if not theme:
            st.warning("⚠️ Mohon isi tema terlebih dahulu.")
            st.stop()

        with st.spinner("🤖 AI sedang membuat LKPD..."):
            lkpd_data = generate_lkpd(theme)

            if lkpd_data:
                lkpd_id = str(uuid.uuid4())[:8]
                save_lkpd(lkpd_id, lkpd_data)
                st.session_state.lkpd_data = lkpd_data
                st.session_state.lkpd_id = lkpd_id

                st.success(f"✅ LKPD berhasil dibuat! ID: `{lkpd_id}`")
                st.markdown("---")

                st.subheader(f"📋 {lkpd_data['judul']}")
                st.info(lkpd_data['materi_singkat'])

                for i, kegiatan in enumerate(lkpd_data["kegiatan"], 1):
                    with st.expander(f"Kegiatan {i}: {kegiatan['nama']}"):
                        st.markdown(f"**Petunjuk:** {kegiatan['petunjuk']}")
                        st.markdown("**Tugas Interaktif:**")
                        for t in kegiatan["tugas_interaktif"]:
                            st.markdown(f"• {t}")
                        st.markdown("**Pertanyaan Pemantik:**")
                        for q in kegiatan["pertanyaan_pemantik"]:
                            st.markdown(f"❓ {q['pertanyaan']}")
            else:
                st.error("❌ Gagal membuat LKPD. Coba lagi nanti.")

    if 'lkpd_id' in st.session_state:
        st.markdown("---")
        st.subheader("📂 LKPD Terakhir")
        st.info(f"ID: {st.session_state.lkpd_id}")

# =========================
# MODE SISWA
# =========================
elif st.session_state.role == "👩🎓 Siswa":
    st.header("👩🎓 Mode Siswa: Isi LKPD")

    lkpd_id = st.text_input("Masukkan ID LKPD dari Guru:")
    if lkpd_id:
        lkpd_data = load_lkpd(lkpd_id)
        if lkpd_data:
            st.success(f"✅ LKPD '{lkpd_data['judul']}' dimuat!")
            st.info(lkpd_data['materi_singkat'])
            st.markdown("---")

            for i, kegiatan in enumerate(lkpd_data["kegiatan"], 1):
                with st.expander(f"Kegiatan {i}: {kegiatan['nama']}"):
                    st.markdown(f"**Petunjuk:** {kegiatan['petunjuk']}")
                    for tugas in kegiatan["tugas_interaktif"]:
                        st.markdown(f"• {tugas}")

                    st.markdown("**Pertanyaan Pemantik - Jawaban Anda:**")
                    for j, q in enumerate(kegiatan["pertanyaan_pemantik"]):
                        key = f"ans_{i}_{j}"
                        st.text_area(f"{j+1}. {q['pertanyaan']}", key=key, height=80)

            if st.button("✨ Kirim Jawaban & Minta Feedback", use_container_width=True):
                st.info("💡 Fitur feedback sedang dikembangkan.")
        else:
            st.error("❌ ID LKPD tidak ditemukan.")
    else:
        st.info("Masukkan ID LKPD untuk mulai.")

st.markdown("---")
st.caption("**Powered by Google Gemini 2.5 Flash — EduAI**")
