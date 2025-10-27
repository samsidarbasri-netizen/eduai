import streamlit as st
import pandas as pd
from gemini_config import setup_gemini, analyze_answer, analyze_class_summary

# ====== Inisialisasi ======
st.set_page_config(page_title="EduAI LKPD Analyzer", layout="wide")

if "lkpd_list" not in st.session_state:
    st.session_state.lkpd_list = {}
if "answers" not in st.session_state:
    st.session_state.answers = []
if "rekap_done" not in st.session_state:
    st.session_state.rekap_done = False

# ====== Sidebar ======
st.sidebar.title("EduAI LKPD System")
menu = st.sidebar.radio("Navigasi", ["👩‍🏫 Mode Guru", "👨‍🎓 Mode Siswa", "📊 Rekapan Nilai"])

# ====== API Key ======
api_key = st.sidebar.text_input("Masukkan API Key Gemini:", type="password")
if api_key:
    model = setup_gemini(api_key)
else:
    st.warning("Masukkan API Key Gemini terlebih dahulu.")
    st.stop()

# ====== MODE GURU ======
if menu == "👩‍🏫 Mode Guru":
    st.header("👩‍🏫 Mode Guru — Buat & Pantau LKPD")

    tab1, tab2 = st.tabs(["🧾 Buat LKPD", "📖 Pemantauan Jawaban Siswa"])

    with tab1:
        st.subheader("Buat LKPD Baru")
        theme = st.text_input("Masukkan Tema LKPD:")
        if st.button("Generate LKPD"):
            if theme:
                st.session_state.lkpd_list[theme] = f"LKPD tentang {theme}. Lengkapi pertanyaan dan pembahasan."
                st.success(f"LKPD '{theme}' berhasil dibuat!")
            else:
                st.warning("Masukkan tema terlebih dahulu.")

        if st.session_state.lkpd_list:
            st.subheader("Daftar LKPD")
            for tema, konten in st.session_state.lkpd_list.items():
                with st.expander(tema):
                    st.write(konten)

    with tab2:
        st.subheader("📖 Pemantauan Jawaban Siswa")
        if len(st.session_state.answers) == 0:
            st.info("Belum ada jawaban siswa masuk.")
        else:
            df = pd.DataFrame(st.session_state.answers)
            st.dataframe(df, use_container_width=True)

            if st.button("Analisis Tingkat Pemahaman Kelas"):
                summary = analyze_class_summary(model, st.session_state.answers)
                st.session_state.rekap_done = True
                st.markdown("### 🧠 Analisis Kelas:")
                st.write(summary)

# ====== MODE SISWA ======
elif menu == "👨‍🎓 Mode Siswa":
    st.header("👨‍🎓 Mode Siswa — Kerjakan LKPD")

    if not st.session_state.lkpd_list:
        st.warning("Belum ada LKPD yang dibuat guru.")
    else:
        name = st.text_input("Nama Siswa:")
        selected_lkpd = st.selectbox("Pilih LKPD:", list(st.session_state.lkpd_list.keys()))
        question = st.session_state.lkpd_list[selected_lkpd]
        st.info(f"**Soal:** {question}")

        answer = st.text_area("Tuliskan Jawabanmu di sini:")
        if st.button("Kirim Jawaban"):
            if name and answer:
                ai_feedback = analyze_answer(model, question, answer)
                st.success("Jawaban berhasil dikirim dan dianalisis AI!")

                # Simpan hasil
                nilai = 0
                for line in ai_feedback.splitlines():
                    if "nilai" in line.lower():
                        import re
                        match = re.search(r'(\d+)', line)
                        if match:
                            nilai = int(match.group(1))
                            break

                st.session_state.answers.append({
                    "Nama": name,
                    "LKPD": selected_lkpd,
                    "Jawaban": answer,
                    "Analisis": ai_feedback,
                    "Nilai": nilai
                })

                st.subheader("💬 Hasil Analisis AI")
                st.write(ai_feedback)
            else:
                st.warning("Isi nama dan jawaban terlebih dahulu!")

# ====== MODE REKAP ======
elif menu == "📊 Rekapan Nilai":
    st.header("📊 Rekapan Nilai & Analisis Pemahaman")

    if len(st.session_state.answers) == 0:
        st.info("Belum ada data siswa.")
    else:
        df = pd.DataFrame(st.session_state.answers)
        st.dataframe(df, use_container_width=True)

        if st.session_state.rekap_done:
            st.markdown("### 🧩 Analisis Umum Kelas telah tersedia di Mode Guru.")
        else:
            st.info("Analisis umum kelas belum dilakukan oleh guru.")
