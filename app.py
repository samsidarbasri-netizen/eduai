import streamlit as st
import random
import json
import time
import gemini_config as gc # Menggunakan alias untuk kemudahan

# --- 1. INISIALISASI SESSION STATE ---
if 'page' not in st.session_state:
    # 'generator', 'lkpd_form', 'review_report'
    st.session_state['page'] = 'generator' 
if 'lkpd_data' not in st.session_state:
    st.session_state['lkpd_data'] = gc.load_lkpd() # Muat LKPD yang sudah ada
if 'manual_api_key' not in st.session_state:
    st.session_state['manual_api_key'] = ''
if 'user_id' not in st.session_state:
    # Buat ID siswa mock unik
    st.session_state['user_id'] = f'Siswa_{random.randint(1000, 9999)}' 

# --- 2. INITIALIZATION FIX (CRUCIAL) ---
# Memastikan init_gemini dipanggil setelah Streamlit session state diatur
gc.init_gemini()


# --- 3. FUNGSI HANDLER LOGIC ---

def handle_generate_lkpd(theme):
    """Menangani pemanggilan AI untuk membuat LKPD."""
    if not gc.AI_READY:
        st.error("AI belum siap. Masukkan Kunci API Gemini yang valid.")
        return
        
    with st.spinner("⏳ AI sedang menyusun LKPD... Proses ini mungkin memakan waktu 15-30 detik."):
        lkpd = gc.generate_lkpd(theme)
        
    if lkpd:
        st.session_state['lkpd_data'] = lkpd
        # Simpan sebagai LKPD Master
        gc.save_jawaban_siswa('LKPD', lkpd, lkpd.get('judul', 'LKPD Baru'))
        st.success("LKPD berhasil dibuat dan disimpan!")
        st.session_state['page'] = 'review_report' 
        st.rerun()
    else:
        st.error("Gagal menghasilkan LKPD. Coba lagi atau periksa koneksi API, Kunci API, dan log konsol untuk detail kesalahan JSON Decode.")

def handle_lkpd_submission(lkpd_data, answers):
    """Menyimpan jawaban siswa ke dalam mock database."""
    # Persiapkan struktur data untuk disimpan
    jawaban_siswa_list = []
    
    # Pastikan data LKPD valid
    kegiatan_list = lkpd_data.get('kegiatan', [])
    if not kegiatan_list:
        st.error("LKPD Master tidak valid atau kosong.")
        return

    # Kumpulkan jawaban dari semua pertanyaan
    for kegiatan in kegiatan_list:
        for q_obj in kegiatan.get('pertanyaan_pemantik', []):
            question = q_obj['pertanyaan']
            answer_text = answers.get(question, '')
            
            jawaban_siswa_list.append({
                'pertanyaan': question,
                'jawaban': answer_text,
                'score': 'Belum Dinilai', # Nilai awal
                'feedback': ''
            })
    
    # Simpan jawaban
    gc.save_jawaban_siswa(st.session_state['user_id'], jawaban_siswa_list, lkpd_data.get('judul', 'LKPD'))
    st.success(f"Jawaban Anda (ID: {st.session_state['user_id']}) telah berhasil dikirim!")
    st.session_state['page'] = 'review_report' # Pindah ke mode Guru setelah submit
    st.rerun()


def handle_scoring():
    """Menangani pemanggilan AI untuk menilai semua jawaban yang belum dinilai."""
    if not gc.AI_READY:
        st.error("AI belum siap untuk melakukan penilaian. Harap masukkan kunci API.")
        return
        
    all_answers = gc.load_all_jawaban()
    if not all_answers:
        st.warning("Belum ada jawaban siswa yang tersedia untuk dinilai.")
        return

    with st.spinner("🧠 AI sedang melakukan penilaian untuk semua jawaban yang belum dinilai..."):
        # Fungsi scoring ini memuat LKPD master, membandingkan, dan mengupdate data internal
        gc.score_all_jawaban(all_answers)
    
    st.success("Penilaian selesai! Tabel laporan telah diperbarui.")
    st.session_state['page'] = 'review_report'
    st.rerun()


# --- 4. FUNGSI DISPLAY UTILITY ---

def display_lkpd_content(lkpd_data, mode='preview'):
    """Menampilkan konten LKPD."""
    if not lkpd_data or not lkpd_data.get('judul'):
        st.info("LKPD belum dibuat. Silakan beralih ke mode 'Generator' untuk membuat LKPD baru.")
        return

    st.title(lkpd_data.get('judul', 'LKPD Tanpa Judul'))
    
    # Tampilkan Tujuan Pembelajaran
    st.subheader("Tujuan Pembelajaran")
    for tujuan in lkpd_data.get('tujuan_pembelajaran', []):
        st.markdown(f"- {tujuan}")
        
    # Tampilkan Materi Singkat
    st.subheader("Materi Singkat")
    st.markdown(lkpd_data.get('materi_singkat', 'Tidak ada materi tersedia.'))

    answers = {} # Dictionary untuk menyimpan jawaban siswa (hanya di mode 'form')
    form_placeholder = st.empty()
    
    with form_placeholder.container():
        if mode == 'form':
            st.markdown("---")
            st.header("Formulir Jawaban Siswa")
            st.markdown(f"**ID Siswa Anda:** `{st.session_state['user_id']}`")
            # Mulai formulir
            with st.form(key='lkpd_form'):
                
                # Tampilkan Kegiatan
                for i, kegiatan in enumerate(lkpd_data.get('kegiatan', [])):
                    st.markdown(f"## 📝 Kegiatan {i+1}: {kegiatan['nama']}")
                    st.info(f"Petunjuk: {kegiatan['petunjuk']}")
                    
                    # Tampilkan Tugas Interaktif
                    st.subheader("A. Tugas Interaktif")
                    for j, tugas in enumerate(kegiatan.get('tugas_interaktif', [])):
                        st.markdown(f"- **Tugas {j+1}:** {tugas}")
                        
                    # Tampilkan Pertanyaan Pemantik/Esai
                    st.subheader("B. Pertanyaan Esai")
                    for k, q_obj in enumerate(kegiatan.get('pertanyaan_pemantik', [])):
                        question = q_obj['pertanyaan']
                        st.markdown(f"**Pertanyaan {k+1}:** {question}")
                        
                        # Input Jawaban Siswa
                        answers[question] = st.text_area(
                            "Jawab di sini:", 
                            key=f"q_{i}_{k}",
                            height=150,
                            label_visibility="collapsed"
                        )
                
                # Tombol Submit
                submit_button = st.form_submit_button(label='Kirim Jawaban', use_container_width=True)
                
                if submit_button:
                    # Panggil handler submission
                    handle_lkpd_submission(lkpd_data, answers)

        elif mode == 'preview':
            st.markdown("---")
            st.header("Kunci Jawaban (Hanya untuk Guru)")
            for i, kegiatan in enumerate(lkpd_data.get('kegiatan', [])):
                st.markdown(f"## Kunci Kegiatan {i+1}: {kegiatan['nama']}")
                for k, q_obj in enumerate(kegiatan.get('pertanyaan_pemantik', [])):
                    with st.expander(f"Pertanyaan {k+1}: {q_obj['pertanyaan']}"):
                        st.markdown(f"**Kunci Ideal:** {q_obj['kunci_jawaban_ideal']}")
                        st.caption("Jawaban ini digunakan AI untuk penilaian otomatis.")


# --- 5. FUNGSI HALAMAN UTAMA ---

def page_generator():
    """Halaman untuk membuat LKPD baru."""
    st.header("✍️ Generator LKPD Otomatis")
    st.info("Masukkan tema atau topik pembelajaran yang Anda inginkan.")
    
    theme = st.text_input(
        "Tema Pembelajaran",
        placeholder="Contoh: Peran Ekosistem Hutan Mangrove dalam Mitigasi Perubahan Iklim",
        key='theme_input'
    )
    
    if st.button("Generate LKPD", use_container_width=True, disabled=not theme):
        handle_generate_lkpd(theme)

    st.markdown("---")
    st.subheader("Pratinjau LKPD Master Terakhir")
    
    if st.session_state['lkpd_data']:
        display_lkpd_content(st.session_state['lkpd_data'], mode='preview')
    else:
        st.warning("Belum ada LKPD yang dibuat.")

def page_lkpd_form():
    """Halaman untuk siswa mengisi LKPD."""
    st.header(f"🧑‍🎓 Formulir LKPD ({st.session_state['user_id']})")
    
    if st.session_state['lkpd_data']:
        display_lkpd_content(st.session_state['lkpd_data'], mode='form')
    else:
        st.error("Belum ada LKPD Master yang tersedia. Harap hubungi guru untuk membuatnya.")

def page_review_report():
    """Halaman untuk guru melihat laporan dan memicu penilaian."""
    st.header("📊 Laporan Penilaian Siswa")
    
    # Muat semua data siswa yang sudah submit
    all_answers = gc.load_all_jawaban()
    
    if not all_answers:
        st.info("Belum ada jawaban siswa yang dikumpulkan.")
        st.markdown("---")
        if st.session_state['lkpd_data']:
             st.subheader("LKPD Aktif:")
             st.caption(st.session_state['lkpd_data'].get('judul', ''))
        return

    # Tombol Penilaian
    if st.button("🧠 Penilaian Otomatis (Score All)", type="primary", use_container_width=True):
        handle_scoring()

    st.markdown("---")
    
    # Struktur data untuk DataFrame
    report_data = []
    
    for record in all_answers:
        user_id = record['user_id']
        lkpd_title = record.get('lkpd_title', 'N/A')
        timestamp = record.get('timestamp', 'N/A')
        
        # Hitung skor rata-rata
        total_score = 0
        total_questions = 0
        
        for ans_obj in record['jawaban_siswa']:
            score = ans_obj.get('score', 0)
            if isinstance(score, int):
                total_score += score
                total_questions += 1

        avg_score = round(total_score / total_questions) if total_questions > 0 else 'N/A'
        
        report_data.append({
            'ID Siswa': user_id,
            'LKPD': lkpd_title,
            'Tanggal Submit': timestamp.strftime("%Y-%m-%d %H:%M") if isinstance(timestamp, datetime) else str(timestamp),
            'Status Nilai': 'Belum Selesai' if any(a.get('score') == 'Belum Dinilai' for a in record['jawaban_siswa']) else 'Selesai',
            'Skor Rata-rata': avg_score
        })

    # Tampilkan Ringkasan dalam bentuk tabel
    st.subheader("Ringkasan Submisi")
    st.dataframe(report_data, use_container_width=True, hide_index=True)
    
    st.markdown("---")
    st.subheader("Detail Jawaban dan Feedback")
    
    # Tampilkan detail setiap jawaban
    for record in all_answers:
        with st.expander(f"Detail Jawaban dari {record['user_id']} ({record.get('lkpd_title', 'LKPD')})"):
            for ans_obj in record['jawaban_siswa']:
                st.markdown(f"#### Pertanyaan: {ans_obj['pertanyaan']}")
                st.warning(f"**Jawaban Siswa:** {ans_obj['jawaban']}")
                
                score = ans_obj.get('score', 'Belum Dinilai')
                feedback = ans_obj.get('feedback', 'Belum ada feedback.')
                
                if score == 'Belum Dinilai':
                    st.info(f"Status: **{score}**")
                else:
                    st.success(f"**Skor:** {score}/100")
                    st.info(f"**Feedback AI:** {feedback}")


# --- 6. SIDEBAR DAN NAVIGASI ---

st.sidebar.title("🛠️ Pengaturan & Navigasi")

# Input API Key
st.sidebar.text_input(
    "Masukkan Kunci API Gemini",
    type="password",
    value=st.session_state['manual_api_key'],
    key='api_key_input',
    on_change=lambda: st.session_state.update(
        manual_api_key=st.session_state.api_key_input,
        # Re-initialize AI status when key changes
        _ = gc.init_gemini() 
    )
)

# Tampilkan Status AI
if gc.AI_READY:
    st.sidebar.success("Gemini AI Ready! 🎉")
else:
    st.sidebar.error("AI GAGAL! Masukkan kunci API yang valid.")

st.sidebar.markdown("---")

# Tombol Navigasi
st.sidebar.subheader("Pilih Mode Aplikasi")
col1, col2 = st.sidebar.columns(2)

with col1:
    if st.button("👨‍🏫 Generator (Guru)", use_container_width=True):
        st.session_state['page'] = 'generator'
        st.rerun()

with col2:
    if st.button("📋 Laporan & Nilai", use_container_width=True):
        st.session_state['page'] = 'review_report'
        st.rerun()

# Tombol Mode Siswa (di luar tombol Guru)
st.sidebar.markdown("---")
if st.button("📝 Formulir LKPD (Siswa)", use_container_width=True):
    st.session_state['page'] = 'lkpd_form'
    st.rerun()

# Informasi ID Siswa saat ini (untuk simulasi)
st.sidebar.markdown(f"**Mode Siswa Aktif:** `{st.session_state['user_id']}`")
st.sidebar.caption("Gunakan ID ini untuk simulasi pengiriman jawaban.")


# --- 7. MAIN APP ROUTER ---
st.title("EduAI: Pembuat LKPD Otomatis")
st.markdown("Aplikasi untuk membantu guru membuat LKPD dan menilai jawaban siswa menggunakan Google Gemini API.")

if st.session_state['page'] == 'generator':
    page_generator()
elif st.session_state['page'] == 'lkpd_form':
    page_lkpd_form()
elif st.session_state['page'] == 'review_report':
    page_review_report()
