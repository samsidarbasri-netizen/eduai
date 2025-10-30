# app.py — V4 (Full feature + Difficulty)
# ======================================================
# Aplikasi Streamlit untuk:
# - Guru : Generate LKPD (pilih tingkat kesulitan), Pantau Jawaban, Penilaian Manual/AI, Rekap
# - Siswa : Mengerjakan LKPD, Submit jawaban
# Kompatibel dengan gemini_config.py (v3)
# ======================================================

import streamlit as st
import uuid
import json
import os
import re
import pandas as pd
from datetime import datetime

# Asumsi gemini_config.py (v3) ada di folder yang sama / importable
from gemini_config import (
    init_model,
    list_available_models,
    generate_lkpd,
    analyze_answer_with_ai,
    save_json,
    load_json,
    LKPD_DIR,
    ANSWERS_DIR,
)

# ------------------ Helpers & Setup ------------------

st.set_page_config(page_title="EduAI LKPD Modern — V4", layout="wide", page_icon="🎓")

def sanitize_id(s: str) -> str:
    """Menghilangkan karakter non-alfanumerik dari string dan memotong panjangnya."""
    return re.sub(r"[^\w-]", "_", s.strip())[:64]

def ensure_dirs():
    os.makedirs(LKPD_DIR, exist_ok=True)
    os.makedirs(ANSWERS_DIR, exist_ok=True)

ensure_dirs()

def card(title: str, content: str, color: str = "#f9fafb"):
    st.markdown(
        f"""
        <div style='background:{color};padding:12px 18px;border-radius:10px;
        box-shadow:0 1px 3px rgba(0,0,0,0.1);margin-bottom:10px;'>
            <div style='font-weight:600;font-size:17px;margin-bottom:6px;'>{title}</div>
            <div style='font-size:14px;line-height:1.5;'>{content}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ------------------ Sidebar: Model & Role ------------------

st.title("EduAI — LKPD Pembelajaran Mendalam (V4)")
st.caption("Mode Guru & Siswa — Generate LKPD, Penilaian AI/Manual, Rekap nilai")

st.sidebar.header("🔧 Konfigurasi & Admin")
# API key: prefer st.secrets but allow manual input
api_key_from_secrets = None
try:
    api_key_from_secrets = st.secrets.get("GEMINI_API_KEY")
except Exception:
    api_key_from_secrets = None

api_key_input = st.sidebar.text_input("Masukkan Gemini API Key (opsional):", type="password")
api_key = api_key_input.strip() or api_key_from_secrets

if st.sidebar.button("Inisialisasi Model Gemini"):
    ok, msg, debug = init_model(api_key)
    if ok:
        st.sidebar.success(msg)
    else:
        st.sidebar.error(msg)
        st.sidebar.write(debug)

if st.sidebar.button("🔎 Tes koneksi (list models)"):
    info = list_available_models()
    if info.get("ok"):
        st.sidebar.success(f"{info['count']} model ditemukan.")
        st.sidebar.write(info["names"])
    else:
        st.sidebar.error(info.get("error", "Gagal memeriksa model."))

st.sidebar.divider()
role = st.sidebar.radio("Pilih Peran", ["👨‍🏫 Guru", "👩‍🎓 Siswa"])

# ------------------ MODE GURU ------------------
if role == "👨‍🏫 Guru":
    st.header("👨‍🏫 Mode Guru — Buat & Pantau LKPD")

    tab_create, tab_monitor = st.tabs(["✏️ Buat LKPD", "📊 Pantau Jawaban"])

    # --- TAB: Buat LKPD ---
    with tab_create:
        st.subheader("✏️ Buat LKPD (AI)")
        tema = st.text_input("Tema / Topik Pembelajaran")
        subject = st.text_input("Mata Pelajaran", value="Sosiologi")
        class_level = st.text_input("Kelas / Jenjang", value="XI")
        learning_objective = st.text_area("Tujuan Pembelajaran (ringkas)", value="")
        difficulty = st.selectbox("Tingkat Kesulitan", ["mudah", "sedang", "sulit"])
        max_retry = st.number_input("Max retry AI (jika parsing JSON gagal)", min_value=0, max_value=3, value=1)

        if st.button("Generate LKPD (AI)"):
            if not tema.strip():
                st.warning("Masukkan **tema** terlebih dahulu.")
            else:
                with st.spinner("Menghasilkan LKPD (format pembelajaran mendalam)..."):
                    # generate_lkpd in gemini_config expects theme and difficulty (v3)
                    data, dbg = generate_lkpd(tema, difficulty=difficulty, max_retry=max_retry)
                    if data:
                        lkpd_id = str(uuid.uuid4())[:8]
                        save_json(LKPD_DIR, lkpd_id, data)
                        st.success(f"✅ **LKPD berhasil dibuat** (ID: **{lkpd_id}**)")
                        st.json(data)
                        st.download_button(
                            "📥 Unduh LKPD (JSON)",
                            json.dumps(data, ensure_ascii=False, indent=2),
                            file_name=f"LKPD_{lkpd_id}.json"
                        )
                    else:
                        st.error("Gagal membuat LKPD. Debug info:")
                        st.code(json.dumps(dbg, ensure_ascii=False, indent=2))

        st.markdown("---")
        st.info("LKPD yang dibuat tersimpan di folder `lkpd_outputs/` dengan ID unik.")

    # --- TAB: Pantau Jawaban ---
    with tab_monitor:
        st.subheader("📊 Pantau Jawaban & Penilaian")
        lkpd_id_input = st.text_input("Masukkan ID LKPD yang ingin dipantau (contoh: ab12cd34)")
        if lkpd_id_input:
            lkpd = load_json(LKPD_DIR, lkpd_id_input)
            if not lkpd:
                st.error("LKPD tidak ditemukan. Pastikan ID benar.")
            else:
                st.success(f"LKPD: **{lkpd.get('judul', 'Tanpa Judul')}** — Tingkat: {lkpd.get('tingkat_kesulitan','-')}")
                answers = load_json(ANSWERS_DIR, lkpd_id_input) or {}

                if not answers:
                    st.info("Belum ada jawaban siswa untuk LKPD ini.")
                else:
                    # Pilih mode penilaian
                    mode_penilaian = st.radio(
                        "Pilih Metode Penilaian",
                        ["💡 Penilaian Otomatis (AI)", "✍️ Penilaian Manual (Guru)"],
                        horizontal=True
                    )
                    st.divider()

                    rekap = []
                    # iterate students
                    for nama, record in answers.items():
                        st.markdown(f"### 🧑‍🎓 Siswa: **{nama}**")
                        jawaban_list = record.get("jawaban", [])
                        # existing penilaian (jika ada) per pertanyaan
                        penilaian_existing = record.get("penilaian", [])  # list of dicts {"score":.., "feedback":..}

                        total_score = 0
                        count = 0
                        updated_penilaian = []  # collect manual entries (if teacher saves)

                        cols = st.columns([3,1,2])  # for header layout
                        cols[0].write("Pertanyaan")
                        cols[1].write("Skor")
                        cols[2].write("Umpan Balik")

                        for idx, q in enumerate(jawaban_list, 1):
                            pertanyaan = q.get("pertanyaan")
                            jawaban_text = q.get("jawaban") or ""
                            st.markdown(f"**{idx}. {pertanyaan}**")
                            st.write(f"**Jawaban Siswa:** {jawaban_text or '_(tidak ada jawaban)_'}")

                            # default score/feedback from saved penilaian (if exists)
                            existing_score = None
                            existing_fb = ""
                            if idx-1 < len(penilaian_existing):
                                existing_entry = penilaian_existing[idx-1]
                                existing_score = existing_entry.get("score")
                                existing_fb = existing_entry.get("feedback","")

                            if mode_penilaian == "💡 Penilaian Otomatis (AI)":
                                # call analyze_answer_with_ai for each question
                                with st.spinner("Menilai dengan AI..."):
                                    ai_eval = analyze_answer_with_ai(
                                        question=pertanyaan,
                                        student_answer=jawaban_text,
                                        lkpd_context=lkpd
                                    )
                                score = ai_eval.get("score", 0)
                                fb = ai_eval.get("feedback", "")
                                st.info(f"💬 Feedback AI: {fb} (Skor: **{score}**)")

                                total_score += score
                                count += 1
                                # keep ai result in temporary list (not automatically saved as manual penilaian)
                                updated_penilaian.append({"score": score, "feedback": fb, "method": "ai"})
                            else:
                                # Manual scoring inputs
                                score_input = st.number_input(
                                    f"Skor pertanyaan {idx} (0-100)",
                                    min_value=0,
                                    max_value=100,
                                    value=int(existing_score) if existing_score is not None else 0,
                                    key=f"{lkpd_id_input}_{nama}_{idx}_score"
                                )
                                fb_input = st.text_area(
                                    f"Catatan Guru untuk pertanyaan {idx}",
                                    value=existing_fb,
                                    key=f"{lkpd_id_input}_{nama}_{idx}_fb",
                                    height=80
                                )
                                total_score += score_input
                                count += 1
                                updated_penilaian.append({"score": int(score_input), "feedback": fb_input, "method": "manual"})

                            st.markdown("---")  # pemisah antar pertanyaan

                        # rata-rata dan klasifikasi
                        avg = round(total_score / count, 2) if count else 0
                        classification = ("Pemahaman tinggi" if avg > 80 else "Cukup baik" if avg >= 60 else "Perlu bimbingan")
                        rekap.append({
                            "Nama": nama,
                            "Total Pertanyaan": count,
                            "Total Skor": total_score,
                            "Rata-rata Skor": avg,
                            "Analisis": classification
                        })

                        # Tombol untuk menyimpan penilaian manual (jika mode manual)
                        if mode_penilaian == "✍️ Penilaian Manual (Guru)":
                            if st.button(f"Simpan Penilaian Manual untuk {nama}", key=f"save_{lkpd_id_input}_{nama}"):
                                # simpan updated_penilaian ke answers file untuk siswa ini
                                answers[nama]["penilaian"] = updated_penilaian
                                answers[nama]["last_graded_at"] = str(datetime.now())
                                save_json(ANSWERS_DIR, lkpd_id_input, answers)
                                st.success(f"Penilaian manual untuk {nama} tersimpan.")

                        st.divider()

                    # tampilkan rekap sebagai tabel
                    st.markdown("## 📊 Rekapan Nilai Siswa")
                    df = pd.DataFrame(rekap)
                    st.dataframe(df, use_container_width=True)
                    st.download_button(
                        "💾 Unduh Rekap Nilai (CSV)",
                        data=df.to_csv(index=False).encode("utf-8"),
                        file_name=f"rekap_nilai_{lkpd_id_input}.csv",
                        mime="text/csv"
                    )

# ------------------ MODE SISWA ------------------
else:
    st.header("👩‍🎓 Mode Siswa — Kerjakan LKPD Pembelajaran Mendalam")
    st.info("Masukkan ID LKPD yang diberikan guru dan nama lengkap Anda.")

    lkpd_id = st.text_input("Masukkan ID LKPD")
    nama = st.text_input("Nama lengkap")
    if lkpd_id and nama:
        sanitized_nama = sanitize_id(nama)
        lkpd = load_json(LKPD_DIR, lkpd_id)
        if not lkpd:
            st.error("LKPD tidak ditemukan. Pastikan ID benar dan sudah dibuat oleh guru.")
        else:
            st.success(f"LKPD Ditemukan: **{lkpd.get('judul','Tanpa Judul')}**")
            # tampilkan tujuan & materi
            card("🎯 Tujuan Pembelajaran", "<br>".join(lkpd.get("tujuan_pembelajaran", [])) if lkpd.get("tujuan_pembelajaran") else "(Belum ada tujuan)", "#eef2ff")
            card("📚 Materi Singkat", lkpd.get("materi_singkat", "(Belum ada materi)"), "#f0fdf4")

            jawaban_list = []
            tahapan = lkpd.get("tahapan_pembelajaran", [])
            if tahapan:
                for i, tahap in enumerate(tahapan, 1):
                    with st.expander(f"🧭 Tahap {i}: {tahap.get('tahap','')}"):
                        tujuan_tahap = tahap.get("deskripsi_tujuan") or tahap.get("uraian") or ""
                        bagian_inti = tahap.get("bagian_inti","") or tahap.get("uraian","")
                        petunjuk = tahap.get("petunjuk","")
                        st.markdown(f"**Tujuan:** {tujuan_tahap}")
                        st.markdown(f"**Bagian Inti:** {bagian_inti}")
                        if petunjuk:
                            st.markdown(f"**Petunjuk:** {petunjuk}")
                        st.divider()

                        # pertanyaan pemantik
                        for j, q in enumerate(tahap.get("pertanyaan_pemantik", []), 1):
                            prompt_text = q.get("pertanyaan")
                            ans = st.text_area(
                                f"**{i}.{j}** {prompt_text}",
                                key=f"{lkpd_id}_{sanitized_nama}_{i}_q{j}",
                                height=120
                            )
                            jawaban_list.append({"pertanyaan": prompt_text, "jawaban": ans})

                        # skenario (mengaplikasikan)
                        for j, s in enumerate(tahap.get("skenario", []), 1):
                            st.markdown(f"#### Skenario {j}: {s.get('judul','') or 'Tanpa Judul'}")
                            st.write(s.get("deskripsi",""))
                            prompt_text = s.get("pertanyaan","Analisis skenario:")
                            ans = st.text_area(
                                f"**Analisis Skenario {j}:** {prompt_text}",
                                key=f"{lkpd_id}_{sanitized_nama}_{i}_s{j}",
                                height=140
                            )
                            jawaban_list.append({"pertanyaan": prompt_text, "jawaban": ans})
            else:
                # fallback untuk format lama 'kegiatan'
                kegiatan_list = lkpd.get("kegiatan", [])
                if kegiatan_list:
                    st.warning("Struktur LKPD lama terdeteksi (kegiatan). Tampilannya disesuaikan.")
                    for i, kegiatan in enumerate(kegiatan_list,1):
                        with st.expander(f"Kegiatan {i}: {kegiatan.get('nama','')}"):
                            st.write(kegiatan.get("petunjuk",""))
                            for j, q in enumerate(kegiatan.get("pertanyaan_pemantik", []),1):
                                prompt_text = q.get("pertanyaan")
                                ans = st.text_area(
                                    f"**{i}.{j}** {prompt_text}",
                                    key=f"{lkpd_id}_{sanitized_nama}_old_{i}_{j}",
                                    height=120
                                )
                                jawaban_list.append({"pertanyaan": prompt_text, "jawaban": ans})

            # Submit
            if st.button("📤 Submit Jawaban"):
                if not nama.strip():
                    st.warning("Nama wajib diisi.")
                else:
                    existing = load_json(ANSWERS_DIR, lkpd_id) or {}
                    # simpan struktur: existing[nama] = {"jawaban": [...], "submitted_at": ts}
                    existing[nama] = {
                        "jawaban": jawaban_list,
                        "submitted_at": str(datetime.now())
                    }
                    save_json(ANSWERS_DIR, lkpd_id, existing)
                    st.success("✅ Jawaban terkirim! Guru dapat menilai melalui panel Pantau Jawaban.")

    else:
        st.info("Masukkan **ID LKPD** dan **Nama** untuk mulai mengerjakan.")

# ------------------ Footer / Info ------------------
st.markdown("---")
st.caption("Catatan: Pastikan API key Gemini sudah diinisialisasi sebelum menggunakan fitur penilaian otomatis.")
