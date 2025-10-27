import streamlit as st
import pandas as pd
import os
import json
from gemini_config import setup_gemini, generate_lkpd, analyze_answer, analyze_class_summary

# ---------------------------------------------------------
# Setup dasar
# ---------------------------------------------------------
st.set_page_config(page_title="EduAI LKPD Analyzer", layout="wide")

if "lkpd_list" not in st.session_state:
    st.session_state.lkpd_list = {}
if "answers" not in st.session_state:
    st.session_state.answers = []
if "rekap_done" not in st.session_state:
    st.session_state.rekap_done = False

# ---------------------------------------------------------
# Sidebar
# ---------------------------------------------------------
st.sidebar.title("EduAI LKPD System")
menu = st.sidebar.radio("Navigasi", ["👩‍🏫 Mode Guru", "👨‍🎓 Mode Siswa", "📊 Rekapan Nilai"])

api_key = st.sidebar.text_input("Masukkan API Key Gemini:", type="password")
if not api_key:
    st.warning("Masukkan API Key Gemini terlebih dahulu.")
    st.stop()

model = setup_gemini(api_key)

# ---------------------------------------------------------
# MODE GURU
# ---------------------------------------------------------
if menu == "👩‍🏫 Mode Guru":
    st.header("👩‍🏫 Mode Guru — Buat & Pantau LKPD")

    tab1, tab2 = st.tabs(["🧾 Buat LKPD", "📖 Pantau Jawaban Siswa"])

    # ===== TAB BUAT LKPD =====
    with tab1:
        st.subheader("🧾 Buat LKPD (Otomatis dengan AI)")
        theme = st.text_input("Masukkan Tema LKPD:")
        if st.button("Generate LKPD (AI)"):
            if theme:
                with st.spinner("Sedang membuat LKPD..."):
                    data, info = generate_lkpd(model, theme)
                    if data:
                        st.session_state.lkpd_list[theme] = data
                        st.success(f"LKPD '{data.get('judul','Tanpa Judul')}' berhasil dibuat!")
                        st.json(data)
                    else:
                        st.error("Gagal membuat LKPD.")
            else:
                st.warning("Masukkan tema terlebih dahulu.")

        # Tampilkan daftar LKPD
        if st.session_state.lkpd_list:
            st.subheader("📚 Daftar LKPD")
            for tema, konten in st.session_state.lkpd_list.items():
                with st.expander(tema):
                    st.write(konten.get("materi_singkat", "Belum ada materi"))

    # ===== TAB PANTAU SISWA =====
    with tab2:
        st.subheader("📖 Pemantauan Jawaban Siswa")
        if len(st.session_state.answers) == 0:
            st.info("Belum ada jawaban siswa masuk.")
        else:
            df = pd.DataFrame(st.session_state.answers)
            st.dataframe(df, use_container_width=True)

            if st.button("Analisis Tingkat Pemahaman Kelas"):
                with st.spinner("AI menganalisis data siswa..."):
                    summary = analyze_class_summary(model, st.session_state.answers)
                    st.session_state.rekap_done = True
                    st.markdown("### 🧠 Analisis Kelas:")
                    st.write(summary)

# ---------------------------------------------------------
# MODE SISWA
# ---------------------------------------------------------
elif menu == "👨‍🎓 Mode Siswa":
    st.header("👨‍🎓 Mode Siswa — Kerjakan LKPD")

    if not st.session_state.lkpd_list:
        st.warning("Belum ada LKPD yang dibuat guru.")
    else:
        name = st.text_input("Nama Siswa:")
        selected_lkpd = st.selectbox("Pilih LKPD:", list(st.session_state.lkpd_list.keys()))
        lkpd = st.session_state.lkpd_list[selected_lkpd]

        st.markdown(f"### 📘 {lkpd.get('judul','Tanpa Judul')}")
        st.info(lkpd.get("materi_singkat", "Belum ada materi"))

        # Tampilkan pertanyaan
        all_questions = []
        for k in lkpd.get("kegiatan", []):
            for q in k.get("pertanyaan_pemantik", []):
                all_questions.append(q.get("pertanyaan"))

        answers = []
        for idx, q in enumerate(all_questions, 1):
            ans = st.text_area(f"{idx}. {q}", key=f"{name}_{idx}", height=100)
            answers.append((q, ans))

        if st.button("📤 Kirim Jawaban"):
            if not name.strip():
                st.warning("Isi nama terlebih dahulu!")
            else:
                total_score = 0
                full_analysis = []
                with st.spinner("AI sedang menganalisis jawabanmu..."):
                    for q, a in answers:
                        feedback = analyze_answer(model, q, a)
                        score = 0
                        for line in feedback.splitlines():
                            if "nilai" in line.lower():
                                import re
                                m = re.search(r'(\d+)', line)
                                if m:
                                    score = int(m.group(1))
                                    break
                        total_score += score
                        full_analysis.append(feedback)

                avg_score = round(total_score / len(answers)) if answers else 0
                record = {
                    "Nama": name,
                    "LKPD": selected_lkpd,
                    "Nilai": avg_score,
                    "Analisis": " | ".join(full_analysis)
                }
                st.session_state.answers.append(record)

                # Simpan otomatis ke CSV (tidak ada ekspor manual)
                pd.DataFrame(st.session_state.answers).to_csv("rekapan_nilai.csv", index=False, encoding="utf-8-sig")

                st.success("✅ Jawaban berhasil dikirim dan dianalisis!")
                st.markdown(f"**Nilai rata-rata:** {avg_score}")
                st.write("### 💬 Analisis AI:")
                for fb in full_analysis:
                    st.info(fb)

# ---------------------------------------------------------
# MODE REKAP
# ---------------------------------------------------------
elif menu == "📊 Rekapan Nilai":
    st.header("📊 Rekapan Nilai & Analisis Pemahaman")

    if len(st.session_state.answers) == 0:
        st.info("Belum ada data siswa.")
    else:
        df = pd.DataFrame(st.session_state.answers)
        st.dataframe(df, use_container_width=True)
        st.info("Rekapan otomatis tersimpan di file: rekapan_nilai.csv")
