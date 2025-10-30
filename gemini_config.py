"""
app.py — FINAL COMPLETE VERSION (v3)
-----------------------------------------------------
✅ Mode GURU dan SISWA
✅ Guru: input tema, tingkat kesulitan → generate LKPD otomatis
✅ Siswa: mengerjakan LKPD dan mendapatkan skor otomatis
✅ Rekapan nilai otomatis tersimpan di folder /answers
✅ Kompatibel dengan gemini_config.py (v3)
"""

import streamlit as st
import uuid
import json
import os
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

# =========================================================
# 🎨 Konfigurasi Halaman
# =========================================================
st.set_page_config(page_title="AI LKPD Generator", layout="wide")
st.title("🧠 Aplikasi LKPD Pembelajaran Mendalam (AI)")

# =========================================================
# 🔑 API Key Section
# =========================================================
st.sidebar.header("🔐 Konfigurasi API Gemini")
api_key = st.sidebar.text_input("Masukkan Gemini API Key:", type="password")

if st.sidebar.button("Inisialisasi Model"):
    ok, msg, debug = init_model(api_key)
    if ok:
        st.sidebar.success(msg)
    else:
        st.sidebar.error(msg)

# =========================================================
# 👥 Pilih Mode
# =========================================================
mode = st.sidebar.radio("Pilih Mode:", ["Guru", "Siswa"])

# =========================================================
# 🧑‍🏫 MODE GURU
# =========================================================
if mode == "Guru":
    st.subheader("🧑‍🏫 Mode Guru — Generate LKPD Otomatis")

    theme = st.text_input("🧩 Masukkan Tema LKPD:")
    difficulty = st.selectbox("⚙️ Pilih Tingkat Kesulitan:", ["mudah", "sedang", "sulit"])
    generate_button = st.button("🚀 Generate LKPD")

    if generate_button:
        if not theme.strip():
            st.warning("Silakan isi tema terlebih dahulu.")
        else:
            with st.spinner("Sedang membuat LKPD..."):
                data, debug = generate_lkpd(theme, difficulty=difficulty)
                if data:
                    file_id = str(uuid.uuid4())[:8]
                    save_json(LKPD_DIR, file_id, data)
                    st.success(f"✅ LKPD berhasil dibuat! ID: {file_id}")

                    st.json(data)

                    st.download_button(
                        label="💾 Unduh LKPD (JSON)",
                        data=json.dumps(data, ensure_ascii=False, indent=2),
                        file_name=f"lkpd_{file_id}.json",
                        mime="application/json",
                    )
                else:
                    st.error("Gagal membuat LKPD.")
                    st.code(debug)
    st.markdown("---")
    st.info("💡 LKPD tersimpan otomatis di folder `lkpd_outputs/`.")

# =========================================================
# 🎓 MODE SISWA
# =========================================================
elif mode == "Siswa":
    st.subheader("🎓 Mode Siswa — Kerjakan LKPD")

    # Pilih file LKPD
    lkpd_files = [
        f for f in os.listdir(LKPD_DIR) if f.endswith(".json")
    ] if os.path.exists(LKPD_DIR) else []

    if not lkpd_files:
        st.warning("Belum ada LKPD. Guru perlu membuatnya terlebih dahulu.")
    else:
        selected_file = st.selectbox("Pilih LKPD:", lkpd_files)
        lkpd_data = load_json(LKPD_DIR, selected_file.replace(".json", ""))

        if lkpd_data:
            st.markdown(f"### 🧾 {lkpd_data.get('judul', 'Tanpa Judul')}")
            st.markdown(f"**Tingkat Kesulitan:** {lkpd_data.get('tingkat_kesulitan', 'Tidak disebutkan')}")
            st.markdown("#### 🎯 Tujuan Pembelajaran")
            for i, t in enumerate(lkpd_data.get("tujuan_pembelajaran", []), 1):
                st.write(f"{i}. {t}")

            st.markdown("#### 📖 Materi Singkat")
            st.write(lkpd_data.get("materi_singkat", ""))

            st.markdown("#### 🔍 Tahapan Pembelajaran")
            for tahap in lkpd_data.get("tahapan_pembelajaran", []):
                st.markdown(f"**{tahap.get('tahap', '')}**")
                st.write(tahap.get("uraian", ""))

            st.markdown("---")

            # Jawaban siswa
            student_name = st.text_input("Nama Siswa:")
            student_answer = st.text_area("✏️ Jawaban Siswa:")

            if st.button("🧮 Kirim dan Nilai Jawaban"):
                if not student_name.strip():
                    st.warning("Nama siswa wajib diisi.")
                elif not student_answer.strip():
                    st.warning("Silakan tulis jawaban terlebih dahulu.")
                else:
                    with st.spinner("Menilai jawaban..."):
                        question_context = (
                            f"Tema: {lkpd_data.get('judul', '')}\n"
                            f"Tujuan: {lkpd_data.get('tujuan_pembelajaran', '')}\n"
                            f"Tahapan: {lkpd_data.get('tahapan_pembelajaran', '')}"
                        )
                        result = analyze_answer_with_ai(
                            question="LKPD Pembelajaran Mendalam",
                            student_answer=student_answer,
                            lkpd_context=question_context,
                        )

                        score = result.get("score", 0)
                        feedback = result.get("feedback", "")

                        st.success(f"Skor: {score}")
                        st.info(f"Umpan Balik: {feedback}")

                        # Simpan hasil
                        record = {
                            "nama_siswa": student_name,
                            "lkpd_file": selected_file,
                            "jawaban": student_answer,
                            "skor": score,
                            "feedback": feedback,
                            "waktu": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        }

                        save_json(ANSWERS_DIR, f"{student_name}_{uuid.uuid4().hex[:6]}", record)
                        st.success("✅ Jawaban tersimpan dan dinilai otomatis.")

    st.markdown("---")
    st.info("📁 Rekapan nilai tersimpan otomatis di folder `answers/`.")

# =========================================================
# 📊 REKAP NILAI GURU (opsional, diaktifkan bila di folder answers ada data)
# =========================================================
if mode == "Guru":
    if os.path.exists(ANSWERS_DIR):
        st.subheader("📊 Rekap Nilai Siswa")
        records = []
        for f in os.listdir(ANSWERS_DIR):
            if f.endswith(".json"):
                data = load_json(ANSWERS_DIR, f.replace(".json", ""))
                if data:
                    records.append(data)

        if records:
            import pandas as pd
            df = pd.DataFrame(records)
            st.dataframe(df)
            st.download_button(
                "💾 Unduh Rekap Nilai (CSV)",
                data=df.to_csv(index=False).encode("utf-8"),
                file_name="rekap_nilai.csv",
                mime="text/csv",
            )
        else:
            st.info("Belum ada jawaban siswa yang tersimpan.")
