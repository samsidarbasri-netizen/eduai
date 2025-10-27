import streamlit as st
import uuid
import json
import os
from datetime import datetime
from gemini_config import (
    init_model,
    generate_lkpd,
    save_json,
    load_json,
    LKPD_DIR,
    ANSWERS_DIR,
    analyze_answer_with_ai
)

# ---------------------------------------------------------
# Setup & Direktori
# ---------------------------------------------------------
st.set_page_config(page_title="EduAI LKPD", layout="wide", page_icon="🎓")

os.makedirs(LKPD_DIR, exist_ok=True)
os.makedirs(ANSWERS_DIR, exist_ok=True)

# ---------------------------------------------------------
# Inisialisasi Model
# ---------------------------------------------------------
api_key = st.secrets.get("GEMINI_API_KEY", None)
ok, msg, _ = init_model(api_key)
if not ok:
    st.error(f"❌ Gagal inisialisasi model: {msg}")
    st.stop()
else:
    st.success(msg)

# ---------------------------------------------------------
# Navigasi
# ---------------------------------------------------------
st.sidebar.header("🔍 Navigasi")
mode = st.sidebar.radio("Pilih Mode", ["👨🏫 Guru", "👩‍🎓 Siswa"])

# ---------------------------------------------------------
# MODE GURU
# ---------------------------------------------------------
if mode == "👨🏫 Guru":
    st.title("👨🏫 Mode Guru — Membuat & Menilai LKPD")
    tab_create, tab_monitor = st.tabs(["✏️ Buat LKPD", "📊 Pantau Jawaban Siswa"])

    # --------- TAB 1: BUAT LKPD ----------
    with tab_create:
        st.subheader("Buat LKPD Baru")
        tema = st.text_input("Masukkan Tema atau Topik Pembelajaran")

        if st.button("🚀 Generate LKPD (AI)"):
            if not tema.strip():
                st.warning("Masukkan tema terlebih dahulu.")
            else:
                with st.spinner("AI sedang membuat LKPD..."):
                    data, dbg = generate_lkpd(tema)
                    if data:
                        lkpd_id = str(uuid.uuid4())[:8]
                        save_json(LKPD_DIR, lkpd_id, data)
                        st.success(f"✅ LKPD berhasil dibuat! (ID: {lkpd_id})")
                        st.json(data)
                    else:
                        st.error("❌ Gagal membuat LKPD.")
                        st.json(dbg)

    # --------- TAB 2: PANTAU SISWA ----------
    with tab_monitor:
        st.subheader("Pantau Jawaban Siswa")
        lkpd_id = st.text_input("Masukkan ID LKPD untuk dipantau")

        if lkpd_id:
            lkpd = load_json(LKPD_DIR, lkpd_id)
            if not lkpd:
                st.error("LKPD tidak ditemukan.")
            else:
                st.success(f"📄 Memantau LKPD: {lkpd.get('judul', 'Tanpa Judul')}")
                answers = load_json(ANSWERS_DIR, lkpd_id) or {}

                if not answers:
                    st.info("Belum ada jawaban siswa.")
                else:
                    for nama, record in answers.items():
                        st.markdown(f"### 🧑‍🎓 {nama}")
                        for idx, q in enumerate(record.get("jawaban", []), 1):
                            st.markdown(f"**{idx}. {q.get('pertanyaan')}**")
                            st.markdown(f"✏️ Jawaban siswa: {q.get('jawaban')}")

                            # Analisis AI (semi-otomatis)
                            ai_analysis = analyze_answer_with_ai(q.get('jawaban'))
                            st.info(f"💬 Analisis AI: {ai_analysis['penjelasan']}")
                            st.markdown(f"📊 Saran Nilai AI: **{ai_analysis['skor']} / 100**")

                            nilai_guru = st.number_input(
                                f"Nilai akhir (guru menyesuaikan)",
                                0, 100, int(ai_analysis['skor'] or 0),
                                key=f"nilai_{nama}_{idx}"
                            )
                        st.divider()

# ---------------------------------------------------------
# MODE SISWA
# ---------------------------------------------------------
else:
    st.title("👩‍🎓 Mode Siswa — Kerjakan LKPD")
    lkpd_id = st.text_input("Masukkan ID LKPD dari guru")
    nama = st.text_input("Nama lengkap siswa")

    if lkpd_id and nama:
        lkpd = load_json(LKPD_DIR, lkpd_id)
        if not lkpd:
            st.error("LKPD tidak ditemukan.")
        else:
            st.success(f"📘 Mengisi LKPD: {lkpd.get('judul', 'Tanpa Judul')}")

            st.markdown("### 🎯 Tujuan Pembelajaran")
            st.write("\n".join(lkpd.get("tujuan_pembelajaran", [])))

            st.markdown("### 📚 Materi Singkat")
            st.info(lkpd.get("materi_singkat", "(Belum ada materi)"))

            jawaban_list = []
            for i, kegiatan in enumerate(lkpd.get("kegiatan", []), 1):
                with st.expander(f"📘 Kegiatan {i}: {kegiatan.get('nama')}"):
                    st.write(kegiatan.get("petunjuk", ""))
                    for j, q in enumerate(kegiatan.get("pertanyaan_pemantik", []), 1):
                        ans = st.text_area(
                            f"{i}.{j} {q.get('pertanyaan')}",
                            height=120,
                            key=f"{lkpd_id}_{nama}_{i}_{j}"
                        )
                        jawaban_list.append({
                            "pertanyaan": q.get('pertanyaan'),
                            "jawaban": ans
                        })

            if st.button("📤 Submit Jawaban"):
                existing = load_json(ANSWERS_DIR, lkpd_id) or {}
                existing[nama] = {
                    "jawaban": jawaban_list,
                    "submitted_at": str(datetime.now())
                }
                save_json(ANSWERS_DIR, lkpd_id, existing)
                st.success("✅ Jawaban berhasil dikirim ke guru!")
    else:
        st.info("Masukkan ID LKPD dan nama siswa untuk mulai mengerjakan.")
