import streamlit as st
import uuid
from typing import List, Dict, Any
import logging

# --- Import dari gemini_config.py ---
from gemini_config import (
    AI_READY,
    init_gemini,
    generate_lkpd,
    save_jawaban_siswa,
    load_all_jawaban,
    score_all_jawaban,
    load_lkpd
)

# --- Konfigurasi Logger ---
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# --- Inisialisasi Aplikasi ---
st.set_page_config(page_title="EduAI - LKPD Generator & Penilai", layout="wide")
st.title("EduAI: Generator & Penilai LKPD Otomatis")

# --- Sidebar: Input API Key Manual ---
st.sidebar.header("Konfigurasi API")
manual_api_key = st.sidebar.text_input(
    "Masukkan Gemini API Key (opsional jika sudah diset di secrets/env)",
    type="password",
    help="API key akan disimpan sementara di session."
)
if manual_api_key:
    st.session_state.manual_api_key = manual_api_key

# --- Inisialisasi Gemini AI ---
if not AI_READY:
    with st.spinner("Menginisialisasi Gemini AI..."):
        init_gemini()
    if not AI_READY:
        st.error("Gagal menginisialisasi Gemini AI. Periksa API key di secrets, env, atau input manual.")
        st.stop()

st.success("Gemini AI siap digunakan!")

# --- Tab Utama: Generate LKPD & Input Jawaban ---
tab1, tab2, tab3 = st.tabs(["Generate LKPD", "Input Jawaban Siswa", "Lihat & Nilai Jawaban"])

# --- Tab 1: Generate LKPD ---
with tab1:
    st.header("Buat LKPD Baru")
    theme = st.text_input("Masukkan Tema LKPD (contoh: Fotosintesis, Demokrasi)", placeholder="Ketik tema di sini")
    
    if st.button("Generate LKPD", type="primary"):
        if not theme.strip():
            st.warning("Silakan masukkan tema terlebih dahulu.")
        else:
            with st.spinner("Menghasilkan LKPD..."):
                lkpd_data = generate_lkpd(theme.strip())
                if lkpd_data:
                    st.session_state.current_lkpd = lkpd_data
                    save_jawaban_siswa("LKPD", lkpd_data, lkpd_data.get("judul", "LKPD Baru"))
                    st.success("LKPD berhasil dibuat!")
                    st.json(lkpd_data, expanded=False)
                else:
                    st.error("Gagal menghasilkan LKPD. Coba lagi atau periksa koneksi API.")

# --- Tab 2: Input Jawaban Siswa ---
with tab2:
    st.header("Input Jawaban Siswa")
    
    # Muat LKPD terbaru jika ada
    current_lkpd = st.session_state.get("current_lkpd") or load_lkpd()
    
    if not current_lkpd:
        st.info("Belum ada LKPD yang dibuat. Buat LKPD terlebih dahulu di tab 'Generate LKPD'.")
    else:
        st.subheader(f"LKPD: {current_lkpd.get('judul', 'Tanpa Judul')}")
        
        # Input nama siswa
        student_name = st.text_input("Nama Siswa", placeholder="Masukkan nama siswa")
        student_id = f"Siswa_{uuid.uuid4().hex[:8]}" if student_name else None
        
        if student_name and student_id:
            jawaban_list = []
            kegiatan = current_lkpd.get("kegiatan", [])
            
            for idx, keg in enumerate(kegiatan):
                st.markdown(f"### Kegiatan: {keg.get('nama', f'Kegiatan {idx+1}')}")
                st.write(keg.get("petunjuk", ""))
                
                for q_idx, q in enumerate(keg.get("pertanyaan_pemantik", [])):
                    pertanyaan = q.get("pertanyaan", f"Pertanyaan {q_idx+1}")
                    jawaban = st.text_area(
                        f"{pertanyaan}",
                        key=f"jawaban_{student_id}_{idx}_{q_idx}",
                        height=100
                    )
                    if jawaban:
                        jawaban_list.append({
                            "pertanyaan": pertanyaan,
                            "jawaban": jawaban,
                            "score": "Belum Dinilai",
                            "feedback": ""
                        })
            
            if st.button("Simpan Jawaban Siswa"):
                if jawaban_list:
                    save_jawaban_siswa(student_id, jawaban_list, current_lkpd.get("judul"))
                    st.success(f"Jawaban {student_name} berhasil disimpan!")
                else:
                    st.warning("Tidak ada jawaban yang diisi.")

# --- Tab 3: Lihat & Nilai Jawaban ---
with tab3:
    st.header("Daftar Jawaban Siswa & Penilaian")
    
    all_jawaban = load_all_jawaban()
    siswa_jawaban = [item for item in all_jawaban if item["user_id"].startswith("Siswa_")]
    
    if not siswa_jawaban:
        st.info("Belum ada jawaban siswa yang disimpan.")
    else:
        if st.button("Nilai Semua Jawaban"):
            with st.spinner("Menilai jawaban..."):
                results = score_all_jawaban(siswa_jawaban)
                st.success("Penilaian selesai!")
                
                # Tampilkan hasil dalam tabel
                import pandas as pd
                df = pd.DataFrame(results)
                st.dataframe(df, use_container_width=True)
        else:
            # Tampilkan ringkasan tanpa penilaian ulang
            summary = []
            for item in siswa_jawaban:
                total_score = sum(
                    j.get("score", 0) if isinstance(j.get("score"), int) else 0
                    for j in item["jawaban_siswa"]
                )
                summary.append({
                    "Siswa": item["user_id"].replace("Siswa_", ""),
                    "Jumlah Soal": len(item["jawaban_siswa"]),
                    "Skor Total": total_score,
                    "Status": "Sudah Dinilai" if total_score > 0 else "Belum Dinilai"
                })
            if summary:
                import pandas as pd
                df_summary = pd.DataFrame(summary)
                st.dataframe(df_summary, use_container_width=True)

# --- Footer ---
st.markdown("---")
st.caption("EduAI v1.0 | Dibuat dengan Streamlit & Google Gemini | Untuk pendidikan SMP/SMA")
