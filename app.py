import streamlit as st
from datetime import datetime
from gemini_config import (
    LKPD_DIR, ANSWERS_DIR, init_model, load_json, save_json,
    analyze_answer_with_ai, analyze_student_overall, export_rekap_to_excel
)

st.set_page_config(page_title="EduAI LKPD", page_icon="🎓", layout="wide")
st.title("📘 EduAI – Sistem LKPD Semi-Otomatis")

api_key = st.text_input("Masukkan API Key Gemini 🔑", type="password")
if api_key:
    ok, msg, _ = init_model(api_key)
    if ok:
        st.success(msg)
    else:
        st.error(msg)
else:
    st.warning("Masukkan API key untuk mulai menggunakan sistem.")
    st.stop()

mode = st.sidebar.selectbox("Pilih Mode", ["Guru", "Siswa"])

# =========================================
# MODE GURU
# =========================================
if mode == "Guru":
    st.header("👩‍🏫 Mode Guru – Pemantauan LKPD")

    lkpd_id = st.text_input("Masukkan ID LKPD yang ingin dipantau")
    if lkpd_id:
        lkpd = load_json(LKPD_DIR, lkpd_id)
        if not lkpd:
            st.error("LKPD tidak ditemukan.")
        else:
            st.success(f"Memantau LKPD: {lkpd.get('judul', 'Tanpa Judul')}")
            answers = load_json(ANSWERS_DIR, lkpd_id) or {}

            if not answers:
                st.info("Belum ada jawaban siswa.")
            else:
                for nama, record in answers.items():
                    st.subheader(f"🧑‍🎓 {nama}")
                    for idx, q in enumerate(record.get("jawaban", []), 1):
                        st.markdown(f"**{idx}. {q.get('pertanyaan')}**")
                        st.markdown(f"✏️ Jawaban siswa: {q.get('jawaban')}")
                        ai_analysis = analyze_answer_with_ai(q.get('jawaban'))
                        st.info(f"💬 Analisis AI: {ai_analysis['penjelasan']}")
                        st.markdown(f"📊 Saran Nilai AI: **{ai_analysis['skor']} / 100**")

                        st.number_input(
                            f"Nilai akhir guru untuk {nama} – pertanyaan {idx}",
                            0, 100, int(ai_analysis['skor'] or 0), key=f"nilai_{nama}_{idx}"
                        )
                    st.divider()

                st.markdown("### 📊 Rekapan Nilai & Analisis Pemahaman")

                if st.button("📈 Lihat Rekapan Nilai & Analisis AI"):
                    rekap_list = []
                    for nama, record in answers.items():
                        hasil = analyze_student_overall(nama, record.get("jawaban", []))
                        rekap_list.append(hasil)

                    st.dataframe(rekap_list)

                    if st.button("⬇️ Ekspor ke Excel"):
                        filepath = export_rekap_to_excel(lkpd_id, rekap_list)
                        st.success(f"Rekapan nilai berhasil disimpan: `{filepath}`")

# =========================================
# MODE SISWA
# =========================================
else:
    st.header("🧑‍🎓 Mode Siswa – Pengisian LKPD")

    lkpd_id = st.text_input("Masukkan ID LKPD dari guru")
    nama = st.text_input("Nama lengkap siswa")

    if lkpd_id and nama:
        lkpd = load_json(LKPD_DIR, lkpd_id)
        if not lkpd:
            st.error("LKPD tidak ditemukan.")
        else:
            st.success(f"Mengisi LKPD: {lkpd.get('judul', 'Tanpa Judul')}")
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
                            "pertanyaan": q.get("pertanyaan"),
                            "jawaban": ans
                        })

            if st.button("📤 Submit Jawaban"):
                existing = load_json(ANSWERS_DIR, lkpd_id) or {}
                existing[nama] = {
                    "jawaban": jawaban_list,
                    "submitted_at": str(datetime.now())
                }
                save_json(ANSWERS_DIR, lkpd_id, existing)
                st.success("Jawaban berhasil dikirim ke guru!")
    else:
        st.info("Masukkan ID LKPD dan nama siswa untuk mulai mengerjakan.")
