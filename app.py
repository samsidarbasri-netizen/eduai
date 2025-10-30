import streamlit as st
import uuid
import json
import os
import re
import pandas as pd
from datetime import datetime

# Asumsi modul dan fungsi ini didefinisikan di gemini_config.py
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

# Konfigurasi halaman Streamlit
st.set_page_config(
    page_title="EduAI LKPD Modern",
    layout="wide",
    page_icon="🎓"
)

# Fungsi untuk membersihkan ID agar aman digunakan sebagai nama file
def sanitize_id(s: str) -> str:
    """Menghilangkan karakter non-alfanumerik dari string dan memotong panjangnya."""
    return re.sub(r"[^\w-]", "_", s.strip())[:64]

# Pastikan direktori penyimpanan ada
os.makedirs(LKPD_DIR, exist_ok=True)
os.makedirs(ANSWERS_DIR, exist_ok=True)

# Fungsi komponen card kustom untuk tampilan yang lebih menarik
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

# Input atau ambil API Key Gemini
api_key = st.secrets.get("GEMINI_API_KEY")
if "GEMINI_API_KEY" in st.secrets:
    pass  # Ambil dari st.secrets
else:
    api_key = st.text_input("🔑 Masukkan API Key Gemini")

ok, msg, debug = init_model(api_key)

# Cek inisialisasi model
if not ok:
    st.error(msg)
    st.stop()
else:
    st.success(msg)

# ------------------ Sidebar ------------------

st.sidebar.header("Navigasi")
role = st.sidebar.radio("Pilih Peran", ["👨‍🏫 Guru", "👩‍🎓 Siswa"])
st.sidebar.divider()

# Tombol tes koneksi/list models
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

    # --- TAB BUAT LKPD (Generate) ---
    with tab_create:
        tema = st.text_input("Tema / Topik Pembelajaran")

        if st.button("Generate LKPD (AI)"):
            if not tema.strip():
                st.warning("Masukkan **tema** terlebih dahulu.")
            else:
                with st.spinner("Menghasilkan LKPD (format pembelajaran mendalam)..."):
                    data, dbg = generate_lkpd(tema)

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
                        st.error("Gagal membuat LKPD.")
                        st.json(dbg)

    # --- TAB PANTAU JAWABAN (Monitor) ---
    with tab_monitor:
        st.subheader("Pantau Jawaban Siswa")
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
                    # Pilihan Mode Penilaian
                    mode_penilaian = st.radio(
                        "Pilih Metode Penilaian",
                        ["💡 Penilaian Otomatis (AI)", "✍️ Penilaian Manual (Guru)"],
                        horizontal=True
                    )
                    st.divider()

                    rekap = []
                    # Iterasi melalui setiap siswa yang menjawab
                    for nama, record in answers.items():
                        st.markdown(f"### 🧑‍🎓 Siswa: **{nama}**")
                        total_score = 0
                        count = 0

                        # Iterasi melalui setiap pertanyaan dan jawaban siswa
                        for idx, q in enumerate(record.get("jawaban", []), 1):
                            st.markdown(f"**{idx}. {q.get('pertanyaan')}**")
                            st.write(f"**Jawaban Siswa:** {q.get('jawaban') or '_(tidak ada jawaban)_'}")
                            
                            score = 0
                            fb = ""

                            # === MODE PENILAIAN AI ===
                            if mode_penilaian == "💡 Penilaian Otomatis (AI)":
                                # Asumsi analyze_answer_with_ai menggunakan konteks LKPD
                                # atau prompt yang sesuai untuk penilaian
                                ai_eval = analyze_answer_with_ai(
                                    question=q.get("pertanyaan"),
                                    student_answer=q.get("jawaban"),
                                    lkpd_context=lkpd  # Tambahkan konteks LKPD untuk AI
                                )
                                score = ai_eval.get("score", 0)
                                fb = ai_eval.get("feedback", "")
                                st.info(f"💬 Feedback AI: {fb} (Skor: **{score}**)")

                            # === MODE PENILAIAN MANUAL ===
                            else:
                                score = st.number_input(
                                    f"Skor untuk pertanyaan {idx} (0-100)",
                                    min_value=0,
                                    max_value=100,
                                    value=0,
                                    key=f"{lkpd_id}_{nama}_{idx}_score"
                                )
                                fb = st.text_area(
                                    f"Catatan Guru (opsional) untuk pertanyaan {idx}",
                                    key=f"{lkpd_id}_{nama}_{idx}_fb",
                                    height=60
                                )
                            
                            total_score += score
                            count += 1
                            st.markdown("---") # Pemisah antar pertanyaan
                        
                        # Hitung rata-rata skor per siswa
                        avg = round(total_score / count, 2) if count else 0

                        # Rekapitulasi nilai siswa
                        rekap.append({
                            "Nama": nama,
                            "Total Pertanyaan": count,
                            "Total Skor": total_score,
                            "Rata-rata Skor": avg,
                            "Analisis AI": (
                                "Pemahaman tinggi" if avg > 80 
                                else "Cukup baik" if avg >= 60 
                                else "Perlu bimbingan"
                            )
                        })
                        st.divider() # Pemisah antar siswa

                    # ===== TABEL REKAP NILAI KESELURUHAN =====
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
        # Sanitasi nama untuk penggunaan dalam key
        sanitized_nama = sanitize_id(nama)
        lkpd = load_json(LKPD_DIR, lkpd_id)

        if not lkpd:
            st.error("LKPD tidak ditemukan.")
        else:
            st.success(f"LKPD Ditemukan: **{lkpd.get('judul', 'Tanpa Judul')}**")
            
            # Tampilkan informasi LKPD menggunakan card
            card("🎯 Tujuan Pembelajaran", "<br>".join(lkpd.get("tujuan_pembelajaran", [])), "#eef2ff")
            card("📚 Materi Singkat", lkpd.get("materi_singkat", "(Belum ada materi)"), "#f0fdf4")
            
            jawaban_list = []
            
            # Tampilkan Tahapan Pembelajaran (struktur baru)
            tahapan = lkpd.get("tahapan_pembelajaran", [])
            if tahapan:
                for i, tahap in enumerate(tahapan, 1):
                    with st.expander(f"🧭 **Tahap {i}: {tahap.get('tahap', '')}**"):
                        st.markdown(f"**Tujuan:** {tahap.get('deskripsi_tujuan', '')}")
                        st.markdown(f"**Bagian Inti:** {tahap.get('bagian_inti', '')}")
                        st.markdown(f"**Petunjuk:** {tahap.get('petunjuk', '')}")
                        st.divider()

                        # Pertanyaan pemantik dalam tahap
                        for j, q in enumerate(tahap.get("pertanyaan_pemantik", []), 1):
                            ans = st.text_area(
                                f"**{i}.{j}** {q.get('pertanyaan')}",
                                key=f"{lkpd_id}_{sanitized_nama}_{i}_q{j}",
                                height=120
                            )
                            jawaban_list.append({"pertanyaan": q.get("pertanyaan"), "jawaban": ans})

                        # Skenario (khusus tahap Mengaplikasikan)
                        for j, s in enumerate(tahap.get("skenario", []), 1):
                            st.markdown(f"#### **Skenario {j}: {s.get('judul','') or 'Tanpa Judul'}**")
                            st.write(s.get("deskripsi", ""))
                            ans = st.text_area(
                                f"**Analisis Skenario {j}:** {s.get('pertanyaan')}",
                                key=f"{lkpd_id}_{sanitized_nama}_{i}_s{j}",
                                height=120
                            )
                            jawaban_list.append({"pertanyaan": s.get("pertanyaan"), "jawaban": ans})
            
            else:
                # Fallback untuk LKPD versi lama (jika ada struktur 'kegiatan')
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
                # Simpan jawaban siswa
                existing = load_json(ANSWERS_DIR, lkpd_id) or {}
                
                # Menggunakan nama asli sebagai key di JSON
                existing[nama] = {
                    "jawaban": jawaban_list,
                    "submitted_at": str(datetime.now())
                }
                save_json(ANSWERS_DIR, lkpd_id, existing)
                st.success("✅ **Jawaban terkirim!** Guru akan menilai dari sistem.")
    
    else:
        st.info("Masukkan **ID LKPD** dan **Nama** untuk mulai mengerjakan.")
