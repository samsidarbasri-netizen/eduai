import streamlit as st
import uuid
import json
import os
import re
import pandas as pd
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
import datetime # Import datetime untuk timestamp

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

# Fungsi komponen card kustom
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
api_key = st.secrets.get("GEMINI_API_KEY") if "GEMINI_API_KEY" in st.secrets else st.text_input("🔑 Masukkan API Key Gemini")
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
        
        # DEFINISI SKALA KESIAPAN (BARU)
        readiness_options = {
            "1 - Mulai dari Dasar": "1 (Mulai dari Dasar): Sedikit atau tidak ada prasyarat. Materi harus sangat rinci.",
            "2 - Membutuhkan Bantuan": "2 (Membutuhkan Bantuan): Prasyarat terbatas. Materi harus mengulang konsep dasar.",
            "3 - Cukup Siap": "3 (Cukup Siap): Prasyarat memadai (Standar). Materi langsung ke inti.",
            "4 - Siap & Mandiri": "4 (Siap & Mandiri): Pemahaman kuat. Materi singkat, langsung ke analisis.",
            "5 - Melebihi Target": "5 (Melebihi Target): Sudah menguasai. Materi hanya pengantar singkat, langsung ke evaluasi/sintesis."
        }
        
        level_selection = st.selectbox(
            "Tingkat Kesiapan Siswa (Skala 1-5)",
            list(readiness_options.keys()),
            help="Pilih skala untuk menyesuaikan kedalaman 'Materi Singkat' dan scaffolding LKPD."
        )
        
        # Ambil instruksi detail yang akan dikirim ke AI
        readiness_instruction = readiness_options[level_selection]

        if st.button("Generate LKPD (AI)"):
            if not tema.strip():
                st.warning("Masukkan **tema** terlebih dahulu.")
            else:
                with st.spinner("Menghasilkan LKPD (format pembelajaran mendalam)..."):
                    # Meneruskan instruksi kesiapan ke fungsi generate_lkpd
                    data, dbg = generate_lkpd(tema, readiness_instruction) 
                    
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
                    total_max_score_lkpd = 0
                    
                    # Iterasi melalui setiap siswa yang menjawab
                    for nama, record in answers.items():
                        st.markdown(f"### 🧑‍🎓 Siswa: **{nama}**")
                        total_score_siswa = 0
                        count = 0

                        # Iterasi melalui setiap pertanyaan dan jawaban siswa
                        for idx, q in enumerate(record.get("jawaban", []), 1):
                            pertanyaan = q.get('pertanyaan')
                            bobot = q.get('bobot', 10) # Ambil bobot (default 10 jika tidak ada)
                            level = q.get('level_kognitif', 1) # Ambil level kognitif (default 1)
                            
                            st.markdown(f"**{idx}. (Lvl {level} | Bobot {bobot} Poin) {pertanyaan}**")
                            st.write(f"**Jawaban Siswa:** {q.get('jawaban') or '_(tidak ada jawaban)_'}")

                            score_persentase = 0
                            
                            # === MODE PENILAIAN AI ===
                            if mode_penilaian == "💡 Penilaian Otomatis (AI)":
                                # Meneruskan objek pertanyaan/jawaban (q)
                                ai_eval = analyze_answer_with_ai(q)
                                
                                score_persentase = ai_eval.get("score", 0)
                                fb = ai_eval.get("feedback", "")
                                
                                # Hitung Skor Absolut: (Skor Persentase / 100) * Bobot Maks
                                score_absolut = round((score_persentase / 100) * bobot, 2)
                                
                                st.info(f"💬 Feedback AI: {fb} (Persentase: {score_persentase}%)")
                                st.success(f"Skor Absolut Siswa: **{score_absolut} / {bobot} Poin**")
                                
                                total_score_siswa += score_absolut
                                
                            # === MODE PENILAIAN MANUAL ===
                            else:
                                score_absolut = st.number_input(
                                    f"Skor Absolut ({bobot} Poin Maks)",
                                    min_value=0, max_value=bobot, value=0,
                                    key=f"{lkpd_id}_{nama}_{idx}_score"
                                )
                                fb = st.text_area(
                                    f"Catatan Guru (opsional)",
                                    key=f"{lkpd_id}_{nama}_{idx}_fb",
                                    height=60
                                )
                                total_score_siswa += score_absolut

                            count += 1
                            st.markdown("---") # Pemisah antar pertanyaan

                        # Hitung Total Max Score LKPD (hanya sekali per LKPD)
                        if not total_max_score_lkpd and record.get("jawaban"):
                            total_max_score_lkpd = sum([q.get('bobot', 10) for q in record.get("jawaban", [])])
                        
                        # Hitung Nilai Akhir Siswa (Skala 100)
                        nilai_skala_100 = round((total_score_siswa / total_max_score_lkpd) * 100, 2) if total_max_score_lkpd else 0

                        # Rekapitulasi nilai siswa
                        rekap.append({
                            "Nama": nama,
                            "Skor Absolut": f"{total_score_siswa} / {total_max_score_lkpd}",
                            "Nilai Akhir (Skala 100)": nilai_skala_100,
                            "Analisis": (
                                "Pemahaman Tinggi" if nilai_skala_100 > 80 else
                                "Cukup Baik" if nilai_skala_100 >= 60 else
                                "Perlu Bimbingan"
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
            card("🎯 Tujuan Pembelajaran", "<br>".join(lkpd.get("tujuan_pembelajaran", [])), "#eef2ff")
            card("📚 Materi Singkat", lkpd.get("materi_singkat", "(Belum ada materi)"), "#f0fdf4")

            jawaban_list = []
            
            # Tampilkan Tahapan Pembelajaran
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
                            bobot = q.get('bobot', 10)
                            level = q.get('level_kognitif', 1)
                            
                            ans = st.text_area(
                                f"**{i}.{j}** (Lvl {level}, Bobot {bobot}) {q.get('pertanyaan')}",
                                key=f"{lkpd_id}_{sanitized_nama}_{i}_q{j}",
                                height=120
                            )
                            # Simpan semua detail pertanyaan dan jawaban untuk penilaian
                            jawaban_list.append({
                                "pertanyaan": q.get("pertanyaan"), 
                                "jawaban": ans,
                                "bobot": bobot,
                                "level_kognitif": level
                            })

                        # Skenario (khusus tahap Mengaplikasikan)
                        for j, s in enumerate(tahap.get("skenario", []), 1):
                            bobot = s.get('bobot', 20)
                            level = s.get('level_kognitif', 3)
                            
                            st.markdown(f"#### **Skenario {j}: {s.get('judul','')}**")
                            st.write(s.get("deskripsi", ""))
                            ans = st.text_area(
                                f"**Analisis Skenario {j}:** (Lvl {level}, Bobot {bobot}) {s.get('pertanyaan')}",
                                key=f"{lkpd_id}_{sanitized_nama}_{i}_s{j}",
                                height=120
                            )
                            # Simpan semua detail skenario dan jawaban untuk penilaian
                            jawaban_list.append({
                                "pertanyaan": s.get("pertanyaan"), 
                                "jawaban": ans,
                                "bobot": bobot,
                                "level_kognitif": level
                            })

            else:
                # Fallback untuk LKPD versi lama (jika ada struktur 'kegiatan')
                st.warning("Struktur LKPD lama terdeteksi. Bobot dan Level Kognitif default (10 poin/Lvl 1) akan digunakan.")
                for i, kegiatan in enumerate(lkpd.get("kegiatan", []), 1):
                    with st.expander(f"Kegiatan {i}: {kegiatan.get('nama','')} (Format Lama)"):
                        st.write(kegiatan.get("petunjuk", ""))
                        st.divider()
                        for j, q in enumerate(kegiatan.get("pertanyaan_pemantik", []), 1):
                            # Default bobot/level untuk LKPD lama
                            bobot_default = 10 
                            level_default = 1
                            
                            ans = st.text_area(
                                f"**{i}.{j}** (Lvl {level_default}, Bobot {bobot_default}) {q.get('pertanyaan')}",
                                key=f"{lkpd_id}_{sanitized_nama}_old_{i}_{j}",
                                height=120
                            )
                            jawaban_list.append({
                                "pertanyaan": q.get("pertanyaan"), 
                                "jawaban": ans,
                                "bobot": bobot_default,
                                "level_kognitif": level_default
                            })

            if st.button("📤 **Submit Jawaban**"):
                # Simpan jawaban siswa
                existing = load_json(ANSWERS_DIR, lkpd_id) or {}
                # Menggunakan nama asli sebagai key di JSON
                existing[nama] = {
                    "jawaban": jawaban_list,
                    "submitted_at": str(datetime.datetime.now()) # Menggunakan datetime yang diimpor
                }
                save_json(ANSWERS_DIR, lkpd_id, existing)
                st.success("✅ **Jawaban terkirim!** Guru akan menilai dari sistem.")
    else:
        st.info("Masukkan **ID LKPD** dan **Nama** untuk mulai mengerjakan.")
