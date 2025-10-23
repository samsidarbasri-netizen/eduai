import streamlit as st
import os
import json
import uuid
import pandas as pd
from datetime import datetime
from typing import Optional, Dict, Any

# Impor model dan fungsi dari gemini_config
from gemini_config import get_model, load_lkpd, save_jawaban_siswa, load_all_jawaban, generate_lkpd, score_all_jawaban

# Dapatkan model yang sudah diinisialisasi (menggunakan st.cache_resource)
model = get_model()

# ========== PAGE CONFIG ==========
st.set_page_config(
    page_title="LMS Interaktif EduAI - Guru Pro",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ========== SESSION STATE ==========
if 'role' not in st.session_state:
    st.session_state.role = None
if 'lkpd_id' not in st.session_state:
    st.session_state.lkpd_id = None

# ========== SIDEBAR ==========
with st.sidebar:
    st.title("🎓 LMS EduAI Pro")
    selected_role = st.radio("Saya adalah:", ["👨‍🏫 Guru", "👩‍🎓 Siswa"], key="role_radio")
    
    if selected_role and selected_role != st.session_state.role:
        st.session_state.role = selected_role
        st.session_state.lkpd_id = None # Reset ID saat ganti peran
        st.rerun()

# Cek inisialisasi model
if model is None:
    st.warning("⚠️ **Gemini AI Belum Siap.** Pastikan API Key dimasukkan dengan benar di Streamlit Secrets dan akun tidak diblokir.")
    st.stop()

# ========== MAIN PAGE DISPLAY ==========
st.title("🚀 LMS Interaktif EduAI")
if st.session_state.role == "👨‍🏫 Guru":
    st.markdown("**GURU PRO MODE:** Buat LKPD + Monitor + Nilai Otomatis")
elif st.session_state.role == "👩‍🎓 Siswa":
    st.markdown("**SISWA MODE:** Isi LKPD Interaktif")


if not st.session_state.role:
    st.warning("👈 Silakan pilih peran Anda di sidebar.")
    st.stop()

# ========== MODE GURU ==========
if st.session_state.role == "👨‍🏫 Guru":
    
    # TABS GURU
    tab1, tab2, tab3 = st.tabs(["📝 Buat LKPD", "📊 Pemantauan Siswa", "📈 Penilaian & Report"])
    
    # --- Tab 1: Buat LKPD ---
    with tab1:
        st.header("📝 Buat LKPD Baru")
        col1, col2 = st.columns([2, 1])
        with col1:
            theme = st.text_input("Masukkan Tema", placeholder="Gerak Lurus")
        with col2:
            if st.button("🚀 Generate LKPD", use_container_width=True):
                if theme:
                    with st.spinner("🤖 AI merancang LKPD..."):
                        lkpd_data = generate_lkpd(theme) 

                    if lkpd_data:
                        try:
                            lkpd_id = str(uuid.uuid4())[:8]
                            os.makedirs("lkpd_outputs", exist_ok=True)
                            filepath = f"lkpd_outputs/{lkpd_id}.json"
                            
                            with open(filepath, 'w', encoding='utf-8') as f:
                                json.dump(lkpd_data, f, ensure_ascii=False, indent=2)
                            
                            st.session_state.lkpd_id = lkpd_id # Update session state
                            st.success(f"✅ **LKPD SIAP!** ID: `{lkpd_id}`")
                            st.info(f"**Share ke siswa:** `{lkpd_id}`")
                            
                            # DISPLAY LKPD
                            st.markdown("---")
                            st.subheader(f"📋 {lkpd_data['judul']}")
                            st.info(lkpd_data['materi_singkat'])
                            # ... (Tampilkan detail kegiatan) ...
                            for i, kegiatan in enumerate(lkpd_data.get('kegiatan', []), 1):
                                with st.expander(f"Kegiatan {i}: {kegiatan['nama']}"):
                                    st.markdown(f"**Petunjuk:** {kegiatan['petunjuk']}")
                                    st.markdown("**Tugas Interaktif:**")
                                    for tugas in kegiatan.get('tugas_interaktif', []):
                                        st.markdown(f"• {tugas}")
                                    st.markdown("**Pertanyaan Pemantik:**")
                                    for q in kegiatan.get('pertanyaan_pemantik', []):
                                        st.markdown(f"❓ {q['pertanyaan']}")
                                    
                        except Exception as e:
                            st.error(f"❌ Error saat menyimpan/menampilkan LKPD: {e}")
                    else:
                        st.error("❌ Gagal mendapatkan respons LKPD dari AI.")

    # --- Tab 2: Pemantauan Siswa ---
    with tab2:
        st.header("📊 Pemantauan Siswa Real-time")
        # Sinkronisasi ID LKPD dengan session state
        default_monitor_id = st.session_state.get('lkpd_id', '')
        lkpd_monitor_id = st.text_input("Masukkan ID LKPD untuk Monitor:", 
                                         value=default_monitor_id, 
                                         key="monitor_id")
        
        if lkpd_monitor_id:
            lkpd_data = load_lkpd(lkpd_monitor_id)
            if lkpd_data:
                all_jawaban = load_all_jawaban(lkpd_monitor_id)
                
                if all_jawaban:
                    st.success(f"✅ **{len(all_jawaban)} SISWA** sudah submit untuk LKPD: **{lkpd_data['judul']}**")
                    
                    # Hitung rata-rata nilai
                    scored_answers = [j.get('total_score', 0) for j in all_jawaban if isinstance(j.get('total_score'), (int, float)) and j.get('total_score') > 0]
                    total_nilai = sum(scored_answers)
                    rata_rata = total_nilai / len(scored_answers) if scored_answers else 0

                    # DASHBOARD
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("👥 Total Siswa Submit", len(all_jawaban))
                    with col2:
                        st.metric("✅ Status LKPD", "Tersedia")
                    with col3:
                        st.metric("⭐ Rata-rata Nilai", f"**{rata_rata:.1f}**")
                    
                    # TABLE SISWA
                    data_siswa = []
                    for jawaban in all_jawaban:
                        data_siswa.append({
                            'Nama': jawaban.get('nama_siswa', 'Anonim'),
                            'Waktu Submit': jawaban.get('waktu_submit', 'N/A'),
                            'Nilai (0-100)': jawaban.get('total_score', 'Belum Dinilai'),
                            'Status': '✅ Selesai'
                        })
                    
                    df = pd.DataFrame(data_siswa)
                    st.dataframe(df, use_container_width=True)
                    
                else:
                    st.info("⏳ **Belum ada siswa submit** - Bagikan ID ke kelas!")
            else:
                st.error("❌ ID LKPD tidak ditemukan!")
    
    # --- Tab 3: Penilaian & Report ---
    with tab3:
        st.header("🤖 Penilaian Otomatis & Export")
        # Sinkronisasi ID LKPD dengan session state
        default_report_id = st.session_state.get('lkpd_id', '')
        report_id = st.text_input("ID LKPD untuk Report:", 
                                   value=default_report_id, 
                                   key="report_id")
        
        if report_id:
            all_jawaban = load_all_jawaban(report_id)
            
            if all_jawaban:
                
                # AI SCORING
                if st.button("🤖 **Nilai Semua Jawaban**", use_container_width=True):
                    with st.spinner("🤖 AI menilai semua jawaban. Mohon tunggu..."):
                        success = score_all_jawaban(report_id)
                    
                    if success:
                        st.success("✅ **PENILAIAN SELESAI!** Data telah diperbarui.")
                        st.rerun() # Refresh untuk memuat skor yang baru
                    else:
                        st.error("❌ Gagal dalam proses penilaian. Cek log.")

                # SHOW SCORES
                st.subheader("📋 Detail Penilaian")
                
                # Muat ulang jawaban untuk menampilkan skor terbaru (setelah rerun)
                all_jawaban_scored = load_all_jawaban(report_id)
                
                if all_jawaban_scored:
                    
                    for jawaban in all_jawaban_scored:
                        score = jawaban.get('total_score', 'N/A')
                        nama = jawaban['nama_siswa']
                        
                        with st.expander(f"👤 {nama} - **Nilai: {score}**"):
                            st.info(f"**Feedback AI:** {jawaban.get('feedback', 'Belum ada feedback.')}")
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                st.write("**Kelebihan (Strengths):**")
                                for strength in jawaban.get('strengths', []):
                                    st.success(f"• {strength}")
                            with col2:
                                st.write("**Perbaikan (Improvements):**")
                                for imp in jawaban.get('improvements', []):
                                    st.warning(f"• {imp}")
                
                    # EXPORT CSV
                    df_export = pd.DataFrame([{
                        'Nama Siswa': j['nama_siswa'],
                        'Nilai': j.get('total_score', 'N/A'),
                        'Feedback Singkat': j.get('feedback', '')[:70] + '...' if j.get('feedback') else ''
                    } for j in all_jawaban_scored])

                    csv = df_export.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        "📥 Download Report CSV",
                        csv,
                        f"report_{report_id}_{datetime.now().strftime('%Y%m%d')}.csv",
                        "text/csv"
                    )
            else:
                st.info("Tidak ada jawaban siswa yang ditemukan untuk ID LKPD ini.")

# ========== MODE SISWA ==========
elif st.session_state.role == "👩‍🎓 Siswa":
    st.header("👩‍🎓 Isi LKPD")
    lkpd_id = st.text_input("Masukkan ID LKPD:", key="siswa_lkpd_id")
    
    if lkpd_id:
        lkpd_data = load_lkpd(lkpd_id)
        
        if lkpd_data:
            
            st.success(f"✅ **{lkpd_data['judul']}** dimuat!")
            st.markdown("---")
            st.subheader(lkpd_data['judul'])
            st.info(lkpd_data['materi_singkat'])
            
            # FORM JAWABAN
            nama_siswa = st.text_input("Nama Anda:", key="siswa_nama")
            jawaban_form = {}
            
            for i, kegiatan in enumerate(lkpd_data.get('kegiatan', []), 1):
                with st.expander(f"Kegiatan {i}: {kegiatan['nama']}"):
                    st.markdown(f"**Petunjuk:** {kegiatan['petunjuk']}")
                    
                    for j, q in enumerate(kegiatan.get('pertanyaan_pemantik', []), 1):
                        pertanyaan_teks = q.get('pertanyaan', f"Pertanyaan {j}")
                        key = f"k{i}_q{j}_{lkpd_id}" 
                        jawaban_form[pertanyaan_teks] = st.text_area(
                            f"{j}. {pertanyaan_teks}", 
                            key=key, 
                            height=80
                        )
            
            if st.button("✨ **Submit & Kirim ke Guru**", use_container_width=True):
                if nama_siswa and any(jawaban_form.values()):
                    
                    filename = save_jawaban_siswa(lkpd_id, nama_siswa, {'jawaban': jawaban_form})
                    
                    if filename:
                        st.success(f"✅ **TERKIRIM!** Jawaban Anda telah disimpan. Tunggu nilai dari guru.")
                        st.balloons()
                    else:
                         st.error("❌ Gagal menyimpan jawaban. Cek izin akses file.")
                else:
                    st.warning("❌ Isi nama & minimal satu jawaban!")

st.markdown("---")
st.markdown("**Powered by Gemini AI 2.5 • Made with ❤️ untuk Guru Indonesia**")
