import streamlit as st
import uuid
import json
from gemini_config import (
    init_model, get_model, generate_lkpd,
    save_json, load_json, LKPD_DIR, ANSWERS_DIR
)

st.set_page_config(page_title="EduAI LKPD", page_icon="🎓", layout="wide")

# -------- Inisialisasi model ----------
api_key = st.secrets.get("GEMINI_API_KEY") if "GEMINI_API_KEY" in st.secrets else None
ok, msg = init_model(api_key)
if not ok:
    st.error(msg)
    st.stop()

# -------- Pilih mode ----------
role = st.sidebar.radio("Pilih Mode:", ["👨🏫 Guru", "👩🎓 Siswa"])

# ===================================
# 👨🏫 MODE GURU
# ===================================
if role == "👨🏫 Guru":
    st.header("👨🏫 Mode Guru — Pembuatan & Pemantauan LKPD")

    tab1, tab2 = st.tabs(["✏️ Buat LKPD", "📊 Pemantauan Jawaban"])

    # ------------------ TAB 1: Generate LKPD ------------------
    with tab1:
        theme = st.text_input("Masukkan tema/topik LKPD:")
        if st.button("Generate LKPD (AI)"):
            if not theme.strip():
                st.warning("Masukkan tema terlebih dahulu.")
            else:
                with st.spinner("Menghasilkan LKPD..."):
                    lkpd_data = generate_lkpd(theme)
                    if lkpd_data:
                        lkpd_id = str(uuid.uuid4())[:8]
                        save_json(LKPD_DIR, lkpd_id, lkpd_data)
                        st.success(f"✅ LKPD berhasil dibuat (ID: {lkpd_id})")
                        st.json(lkpd_data)
                    else:
                        st.error("Gagal membuat LKPD. Coba lagi nanti.")

    # ------------------ TAB 2: Pemantauan ------------------
    with tab2:
        lkpd_id = st.text_input("Masukkan ID LKPD untuk dipantau:")
        if lkpd_id:
            lkpd = load_json(LKPD_DIR, lkpd_id)
            if lkpd:
                st.subheader(f"Pemantauan LKPD: {lkpd.get('judul','')}")
                answers = load_json(ANSWERS_DIR, lkpd_id) or {}

                if not answers:
                    st.info("Belum ada siswa yang mengumpulkan jawaban.")
                else:
                    for student, data in answers.items():
                        st.markdown(f"### 🧑‍🎓 {student}")
                        for i, q in enumerate(data["jawaban"], 1):
                            st.write(f"**Pertanyaan {i}:** {q['pertanyaan']}")
                            st.write(f"**Jawaban Siswa:** {q['jawaban']}")
                            correct = lkpd.get("jawaban_benar", [])
                            if i <= len(correct):
                                st.success(f"✅ Contoh Jawaban Benar (AI): {correct[i-1]}")
                            nilai = st.number_input(f"Nilai untuk pertanyaan {i}", 0, 100, 0, key=f"{student}_{i}")
                            catatan = st.text_area(f"Catatan guru untuk pertanyaan {i}", key=f"note_{student}_{i}")
                        st.markdown("---")
            else:
                st.error("LKPD tidak ditemukan.")

# ===================================
# 👩🎓 MODE SISWA
# ===================================
elif role == "👩🎓 Siswa":
    st.header("👩🎓 Mode Siswa — Pengerjaan LKPD")

    lkpd_id = st.text_input("Masukkan ID LKPD:")
    nama = st.text_input("Nama Lengkap:")
    if lkpd_id and nama:
        lkpd = load_json(LKPD_DIR, lkpd_id)
        if lkpd:
            st.success(f"LKPD: {lkpd.get('judul','')}")
            st.write(lkpd.get("materi_singkat", ""))
            jawaban_siswa = []
            for i, keg in enumerate(lkpd.get("kegiatan", []), 1):
                with st.expander(f"Kegiatan {i}: {keg.get('nama','')}"):
                    st.write(keg.get("petunjuk", ""))
                    for j, q in enumerate(keg.get("pertanyaan_pemantik", []), 1):
                        t = st.text_area(f"{i}.{j} {q['pertanyaan']}", key=f"{i}_{j}_{nama}")
                        jawaban_siswa.append({"pertanyaan": q["pertanyaan"], "jawaban": t})
            if st.button("Submit Jawaban"):
                save_json(ANSWERS_DIR, lkpd_id, {**(load_json(ANSWERS_DIR, lkpd_id) or {}), nama: {"jawaban": jawaban_siswa}})
                st.success("Jawaban berhasil dikirim ke guru.")
        else:
            st.error("LKPD tidak ditemukan.")
    else:
        st.info("Masukkan ID LKPD dan nama terlebih dahulu.")
