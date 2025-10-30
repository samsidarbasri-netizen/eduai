import streamlit as st
import uuid
import json
import os
import re
import pandas as pd

# Asumsi modul dan fungsi ini didefinisikan di `gemini_config.py`
from gemini_config import (
    init_model,
    list_available_models,
    generate_lkpd,
    analyze_answer_with_ai,
    save_json,
    load_json,
    LKPD_DIR,
    ANSWERS_DIR
)

# ------------------ Setup & Helpers ------------------

st.set_page_config(
    page_title="EduAI LKPD Modern",
    layout="wide",
    page_icon="🎓"
)

def sanitize_id(s: str) -> str:
    """Menghilangkan karakter non-alfanumerik dari string dan memotong panjangnya."""
    return re.sub(r"[^\w-]", "_", s.strip())[:64]

os.makedirs(LKPD_DIR, exist_ok=True)
os.makedirs(ANSWERS_DIR, exist_ok=True)

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

# ------------------ Init Model ------------------
st.title("EduAI — LKPD Pembelajaran Mendalam")
st.caption("AI membantu membuat LKPD konseptual dan menganalisis pemahaman siswa secara semi-otomatis.")

api_key = st.secrets.get("GEMINI_API_KEY") if "GEMINI_API_KEY" in st.secrets else st.text_input("🔑 Masukkan API Key Gemini")
ok, msg, debug = init_model(api_key)

if not ok:
    st.error(msg)
    st.stop()
else:
    st.success(msg)

# ------------------ Sidebar ------------------
st.sidebar.header("Navigasi")
role = st.sidebar.radio("Pilih Peran", ["👨‍🏫 Guru", "👩‍🎓 Siswa"])
st.sidebar.divider()

if st.sidebar.button("🔎 Tes koneksi (list models)"):
    info = list_available_models()
    if info.get("ok"):
        st.sidebar.success(f"{info['count']} model ditemukan.")
    else:
        st.sidebar.error(info.get("error", "Gagal memeriksa model."))

# =========================================================
# MODE GURU
# =========================================================
if role == "👨‍🏫 Guru":
    st.header("👨‍🏫 Mode Guru — Buat & Pantau LKPD")
    tab_create, tab_monitor = st.tabs(["✏️ Buat LKPD", "📊 Pantau Jawaban"])

    # --- TAB BUAT LKPD ---
    with tab_create:
        tema = st.text_input("Tema / Topik Pembelajaran")

        # 🔹 Tambahan baru: Pilih tingkat kesulitan
        tingkat_kesulitan = st.selectbox(
            "📊 Tingkat Kesulitan LKPD",
            ["Mudah", "Sedang", "Sulit"],
            help=(
                "**Mudah:** Pertanyaan langsung, fokus pada pemahaman dasar.\n\n"
                "**Sedang:** Ada analisis ringan dan penerapan sederhana.\n\n"
                "**Sulit:** Menuntut analisis mendalam, sintesis, dan refleksi kritis."
            ),
        )

        # 🔹 Penjelasan visual tentang tingkat kesulitan
        st.markdown(
            f"""
            <div style='background:#f1f5f9;padding:10px 15px;border-radius:8px;
            font-size:14px;line-height:1.6;margin-bottom:10px'>
            🔍 <b>Definisi Tingkat Kesulitan:</b><br>
            <b>Mudah:</b> Pertanyaan faktual & pemahaman dasar.<br>
            <b>Sedang:</b> Analisis ringan & penerapan konteks sederhana.<br>
            <b>Sulit:</b> Analisis mendalam & refleksi kritis terhadap fenomena sosial.
            </div>
            """,
            unsafe_allow_html=True,
        )

        if st.button("🚀 Generate LKPD (AI)"):
            if not tema.strip():
                st.warning("Masukkan **tema** terlebih dahulu.")
            else:
                with st.spinner("AI sedang membuat LKPD pembelajaran mendalam..."):
                    # Kirim parameter tambahan 'tingkat_kesulitan'
                    data, dbg = generate_lkpd(tema, tingkat_kesulitan)
                    if data:
                        lkpd_id = str(uuid.uuid4())[:8]
                        save_json(LKPD_DIR, lkpd_id, data)
                        st.success(f"✅ **LKPD berhasil dibuat!** (ID: **{lkpd_id}**)")
                        st.json(data)
                        st.download_button(
                            "📥 Unduh LKPD (JSON)",
                            json.dumps(data, ensure_ascii=False, indent=2),
                            file_name=f"LKPD_{lkpd_id}.json"
                        )
                    else:
                        st.error("❌ Gagal membuat LKPD.")
                        st.json(dbg)

    # --- TAB PANTAU JAWABAN ---
    with tab_monitor:
        st.subheader("📊 Pantau Jawaban Siswa")
        lkpd_id = st.text_input("Masukkan ID LKPD yang ingin dipantau")

        if lkpd_id:
            lkpd = load_json(LKPD_DIR, lkpd_id)
            if not lkpd:
                st.error("LKPD tidak ditemukan.")
            else:
                st.success(f"LKPD: **{lkpd.get('judul', 'Tanpa Judul')}**")
                answers = load_json(ANSWERS_DIR, lkpd_id) or {}

                if not answers:
                    st.info("Belum ada jawaban siswa untuk LKPD ini.")
                else:
                    mode_penilaian = st.radio(
                        "Pilih Metode Penilaian",
                        ["💡 Penilaian Otomatis (AI)", "✍️ Penilaian Manual (Guru)"],
                        horizontal=True
                    )
                    st.divider()

                    rekap = []
                    for nama, record in answers.items():
                        st.markdown(f"### 🧑‍🎓 Siswa: **{nama}**")
                        total_score = 0
                        count = 0

                        for idx, q in enumerate(record.get("jawaban", []), 1):
                            st.markdown(f"**{idx}. {q.get('pertanyaan')}**")
                            st.write(f"**Jawaban Siswa:** {q.get('jawaban') or '_(tidak ada jawaban)_'}")

                            score = 0
                            fb = ""

                            if mode_penilaian == "💡 Penilaian Otomatis (AI)":
                                ai_eval = analyze_answer_with_ai(
                                    question=q.get("pertanyaan"),
                                    student_answer=q.get("jawaban"),
                                    lkpd_context=lkpd
                                )
                                score = ai_eval.get("score", 0)
                                fb = ai_eval.get("feedback", "")
                                st.info(f"💬 Feedback AI: {fb} (Skor: **{score}**)")

                            else:
                                score = st.number_input(
                                    f"Skor untuk pertanyaan {idx} (0-100)",
                                    min_value=0, max_value=100, value=0,
                                    key=f"{lkpd_id}_{nama}_{idx}_score"
                                )
                                fb = st.text_area(
                                    f"Catatan Guru (opsional) untuk pertanyaan {idx}",
                                    key=f"{lkpd_id}_{nama}_{idx}_fb",
                                    height=60
                                )

                            total_score += score
                            count += 1
                            st.markdown("---")

                        avg = round(total_score / count, 2) if count else 0
                        rekap.append({
                            "Nama": nama,
                            "Total Pertanyaan": count,
                            "Total Skor": total_score,
                            "Rata-rata Skor": avg,
                            "Analisis AI": (
                                "Pemahaman tinggi" if avg > 80 else
                                "Cukup baik" if avg >= 60 else
                                "Perlu bimbingan"
                            )
                        })
                        st.divider()

                    st.markdown("## 📊 Rekapan Nilai Siswa")
                    df = pd.DataFrame(rekap)
                    st.dataframe(df, use_container_width=True)

# =========================================================
# MODE SISWA
# =========================================================
else:
    st.header("👩‍🎓 Mode Siswa — Kerjakan LKPD Pembelajaran Mendalam")
    lkpd_id = st.text_input("Masukkan ID LKPD yang diberikan guru")
    nama = st.text_input("Nama lengkap")

    if lkpd_id and nama:
        sanitized_nama = sanitize_id(nama)
        lkpd = load_json(LKPD_DIR, lkpd_id)
        if not lkpd:
            st.error("LKPD tidak ditemukan.")
        else:
            st.success(f"LKPD Ditemukan: **{lkpd.get('judul', 'Tanpa Judul')}**")
            card("🎯 Tujuan Pembelajaran", "<br>".join(lkpd.get("tujuan_pembelajaran", [])), "#eef2ff")
            card("📚 Materi Singkat", lkpd.get("materi_singkat", "(Belum ada materi)"), "#f0fdf4")

            jawaban_list = []
            tahapan = lkpd.get("tahapan_pembelajaran", [])

            if tahapan:
                for i, tahap in enumerate(tahapan, 1):
                    with st.expander(f"🧭 **Tahap {i}: {tahap.get('tahap', '')}**"):
                        st.markdown(f"**Tujuan:** {tahap.get('deskripsi_tujuan', '')}")
                        st.markdown(f"**Bagian Inti:** {tahap.get('bagian_inti', '')}")
                        st.markdown(f"**Petunjuk:** {tahap.get('petunjuk', '')}")
                        st.divider()

                        for j, q in enumerate(tahap.get("pertanyaan_pemantik", []), 1):
                            ans = st.text_area(
                                f"**{i}.{j}** {q.get('pertanyaan')}",
                                key=f"{lkpd_id}_{sanitized_nama}_{i}_q{j}",
                                height=120
                            )
                            jawaban_list.append({"pertanyaan": q.get("pertanyaan"), "jawaban": ans})

                        for j, s in enumerate(tahap.get("skenario", []), 1):
                            st.markdown(f"#### **Skenario {j}: {s.get('judul','')}**")
                            st.write(s.get("deskripsi", ""))
                            ans = st.text_area(
                                f"**Analisis Skenario {j}:** {s.get('pertanyaan')}",
                                key=f"{lkpd_id}_{sanitized_nama}_{i}_s{j}",
                                height=120
                            )
                            jawaban_list.append({"pertanyaan": s.get("pertanyaan"), "jawaban": ans})

            else:
                st.warning("Struktur LKPD lama terdeteksi (menggunakan 'kegiatan').")
                for i, kegiatan in enumerate(lkpd.get("kegiatan", []), 1):
                    with st.expander(f"Kegiatan {i}: {kegiatan.get('nama','')} (Format Lama)"):

                        st.write(kegiatan.get("petunjuk", ""))
                        st.divider()
                        for j, q in enumerate(kegiatan.get("pertanyaan_pemantik", []), 1):
                            ans = st.text_area(
                                f"**{i}.{j}** {q.get('pertanyaan')}",
                                key=f"{lkpd_id}_{sanitized_nama}_old_{i}_{j}",
                                height=120
                            )
                            jawaban_list.append({"pertanyaan": q.get("pertanyaan"), "jawaban": ans})

            if st.button("📤 **Submit Jawaban**"):
                existing = load_json(ANSWERS_DIR, lkpd_id) or {}
                existing[nama] = {
                    "jawaban": jawaban_list,
                    "submitted_at": str(__import__('datetime').datetime.now())
                }
                save_json(ANSWERS_DIR, lkpd_id, existing)
                st.success("✅ **Jawaban terkirim!** Guru akan menilai dari sistem.")
    else:
        st.info("Masukkan **ID LKPD** dan **Nama** untuk mulai mengerjakan.")
