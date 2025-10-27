"""
app.py — FINAL STABLE DEEP LEARNING VERSION
--------------------------------------------
✅ Menampilkan LKPD dengan 3 tahap pembelajaran mendalam:
   1. Memahami
   2. Mengaplikasikan
   3. Merefleksi
✅ Analisis jawaban siswa secara AI.
✅ Tidak ada ekspor Excel/CSV.
✅ Mengambil API key dari Streamlit secrets.
✅ Arsitektur lama dipertahankan.
"""

import streamlit as st
import json
import os
import time
from datetime import datetime

from gemini_config import (
    init_model,
    generate_lkpd,
    analyze_answer_with_ai,
    save_json,
    load_json,
    LKPD_DIR,
    ANSWERS_DIR,
)

# ------------------ SETTING STREAMLIT ------------------
st.set_page_config(page_title="EduAI LKPD Generator", layout="wide")

st.title("📘 EduAI LKPD Generator")
st.caption("Didesain untuk Pembelajaran Mendalam (Memahami – Mengaplikasikan – Merefleksi)")

# ------------------ INISIALISASI MODEL ------------------
api_key = st.secrets.get("GEMINI_API_KEY", "")
if not api_key:
    st.error("⚠️ API Key belum diatur di Streamlit secrets.")
    st.stop()

ok, msg, debug = init_model(api_key)
if not ok:
    st.error(f"Gagal inisialisasi model: {msg}")
    st.stop()
else:
    st.success(msg)

# ------------------ INPUT GURU ------------------
with st.expander("🧩 Buat LKPD Baru", expanded=True):
    theme = st.text_input("Masukkan tema/topik LKPD (contoh: Hukum II Newton atau Keadilan Sosial):")
    if st.button("🚀 Generate LKPD", use_container_width=True, type="primary"):
        if not theme.strip():
            st.warning("Masukkan tema LKPD terlebih dahulu.")
        else:
            with st.spinner("Membangun LKPD berbasis pembelajaran mendalam..."):
                lkpd, dbg = generate_lkpd(theme)
                if lkpd:
                    file_id = theme.strip().replace(" ", "_").lower()
                    save_json(LKPD_DIR, file_id, lkpd)
                    st.success(f"LKPD '{lkpd['judul']}' berhasil dibuat dan disimpan.")
                    st.session_state["current_lkpd_id"] = file_id
                    st.session_state["current_lkpd_data"] = lkpd
                else:
                    st.error("❌ Gagal menghasilkan LKPD. Silakan coba lagi.")
                    with st.expander("Debug Info"):
                        st.json(dbg)

# ------------------ MUAT LKPD ------------------
available_files = [f.replace(".json", "") for f in os.listdir(LKPD_DIR)] if os.path.exists(LKPD_DIR) else []
if available_files:
    selected_file = st.selectbox("📂 Pilih LKPD untuk ditampilkan:", available_files)
    if st.button("📖 Tampilkan LKPD"):
        data = load_json(LKPD_DIR, selected_file)
        if data:
            st.session_state["current_lkpd_id"] = selected_file
            st.session_state["current_lkpd_data"] = data

# ------------------ TAMPILKAN LKPD ------------------
if "current_lkpd_data" in st.session_state:
    lkpd = st.session_state["current_lkpd_data"]
    st.divider()
    st.header(f"🧾 {lkpd.get('judul', 'Tanpa Judul')}")

    st.subheader("🎯 Tujuan Pembelajaran")
    for t in lkpd.get("tujuan_pembelajaran", []):
        st.markdown(f"- {t}")

    st.subheader("📘 Materi Singkat")
    st.markdown(lkpd.get("materi_singkat", "_(Belum ada ringkasan)_"))

    st.divider()
    st.subheader("🧠 Tahapan Pembelajaran Mendalam")

    for tahap in lkpd.get("tahapan", []):
        st.markdown(f"### 🔹 {tahap['nama_tahap']}")
        st.markdown(f"**Deskripsi:** {tahap['deskripsi']}")
        for kegiatan in tahap.get("kegiatan", []):
            with st.expander(f"📍 {kegiatan['nama']}", expanded=False):
                st.markdown(f"**Petunjuk:** {kegiatan['petunjuk']}")
                st.markdown("**Pertanyaan Pemantik:**")
                for p in kegiatan.get("pertanyaan_pemantik", []):
                    st.markdown(f"- {p['pertanyaan']}")

    st.divider()
    st.subheader("📝 Jawaban Siswa")

    # Input identitas siswa
    student_name = st.text_input("Nama siswa:")
    student_answer = st.text_area("Tuliskan jawaban/refleksi kamu di sini...", height=180)

    if st.button("💡 Analisis Jawaban"):
        if not student_name or not student_answer:
            st.warning("Lengkapi nama dan jawaban terlebih dahulu.")
        else:
            with st.spinner("Menganalisis jawaban siswa..."):
                result = analyze_answer_with_ai(student_answer)
                file_id = f"{st.session_state['current_lkpd_id']}__{student_name.strip().replace(' ', '_')}"
                save_json(ANSWERS_DIR, file_id, {
                    "siswa": student_name,
                    "jawaban": student_answer,
                    "analisis": result,
                    "timestamp": datetime.now().isoformat()
                })
                st.success("✅ Analisis selesai.")
                st.markdown(f"**Skor:** {result.get('score', 0)} / 100")
                st.markdown(f"**Umpan balik:** {result.get('feedback', '')}")

    # Menampilkan hasil analisis sebelumnya
    if os.path.exists(ANSWERS_DIR):
        with st.expander("📊 Rekap Jawaban Siswa"):
            files = [f for f in os.listdir(ANSWERS_DIR) if f.startswith(st.session_state["current_lkpd_id"])]
            if not files:
                st.info("Belum ada jawaban yang dianalisis.")
            else:
                for f in files:
                    data = load_json(ANSWERS_DIR, f)
                    st.markdown(f"**👤 {data['siswa']}** — {data['analisis']['score']} / 100")
                    st.markdown(f"_Feedback:_ {data['analisis']['feedback']}")
                    st.markdown("---")

else:
    st.info("💡 Belum ada LKPD yang aktif. Buat atau pilih LKPD terlebih dahulu.")

# ------------------ FOOTER ------------------
st.divider()
st.caption("🚀 EduAI by Samsidar Basri & GPT-5 — Versi Deep Learning LKPD (Kemendikbud Aligned)")
