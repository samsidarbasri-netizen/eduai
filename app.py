import streamlit as st
import pandas as pd
from gemini_config import (
    init_gemini, 
    load_lkpd, 
    save_jawaban_siswa, 
    load_all_jawaban, 
    generate_lkpd, 
    score_jawaban,
    score_all_jawaban,
    logger
)

# --- Konfigurasi Halaman ---
st.set_page_config(
    page_title="EduAI LMS Interaktif",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Inisialisasi Sesi State ---
if 'page' not in st.session_state:
    st.session_state.page = 'guru'
if 'lkpd_data' not in st.session_state:
    st.session_state.lkpd_data = load_lkpd()
if 'lkpd_theme' not in st.session_state:
    st.session_state.lkpd_theme = ""
if 'current_user' not in st.session_state:
    st.session_state.current_user = "Guru" # Default pengguna
if 'siswa_answers' not in st.session_state:
    st.session_state.siswa_answers = [] # Inisialisasi daftar jawaban siswa

# --- Inisialisasi Model AI dan Database ---
# init_gemini sekarang mengembalikan status boolean
db_ready = init_gemini()
db = st.session_state.get('mock_db', None) # Ambil db dari session state

# Tampilkan status koneksi di sidebar
st.sidebar.markdown(f"**Status Koneksi:**")
if db_ready:
    st.sidebar.success("Database & Gemini AI Ready!")
else:
    st.sidebar.error("Database/Gemini AI Not Ready.")
    
# Tampilkan nama pengguna saat ini
st.sidebar.info(f"Anda masuk sebagai: **{st.session_state.current_user}**")
st.sidebar.divider()

# --- Fungsi Pindah Halaman ---
def set_page(page_name):
    st.session_state.page = page_name
    # Pastikan data jawaban siswa direset atau dimuat ulang saat pindah ke halaman siswa
    if page_name == 'siswa':
        # Reset siswa_answers state agar dimuat ulang di siswa_page
        st.session_state.siswa_answers = [] 

# --- Sidebar Navigasi ---
st.sidebar.header("Navigasi")

if st.session_state.page.startswith('siswa'):
    # Mode Siswa
    if st.sidebar.button("Kembali ke Halaman Siswa"):
        set_page('siswa')
    if st.sidebar.button("Lihat Nilai/Feedback"):
        set_page('siswa_nilai')
    if st.sidebar.button("Ganti Pengguna (Guru)"):
        st.session_state.current_user = "Guru"
        st.session_state.page = 'guru'
        st.rerun()

elif st.session_state.page.startswith('guru'):
    # Mode Guru
    if st.sidebar.button("Halaman Utama Guru"):
        set_page('guru')
    if st.sidebar.button("Lihat Jawaban Siswa"):
        set_page('guru_jawaban')
    if st.sidebar.button("Ganti Pengguna (Siswa)"):
        st.session_state.current_user = f"Siswa_{st.sidebar.text_input('Nama Siswa', 'Budi')}"
        st.session_state.page = 'siswa'
        st.rerun()

st.sidebar.divider()


# --- Tampilan Halaman Guru ---

def guru_page():
    st.title("👨‍🏫 Dashboard Guru: Pembuatan LKPD AI")

    # 1. Input Tema LKPD
    st.subheader("1. Tentukan Tema LKPD")
    col1, col2 = st.columns([3, 1])
    
    theme_input = col1.text_input(
        "Masukkan Tema Pembelajaran (misal: Hukum Newton Kelas X, Pembentukan Sel Kelas XI)", 
        value=st.session_state.lkpd_theme,
        key="theme_input_key"
    )
    
    # 2. Tombol Generate LKPD
    if col2.button("🚀 Generate LKPD", use_container_width=True):
        if not db_ready: # Menggunakan db_ready status
            st.error("Koneksi Gemini/Database belum siap. Mohon cek status di sidebar.")
            return

        st.session_state.lkpd_theme = theme_input
        with st.spinner(f"AI sedang membuat LKPD untuk tema: **{theme_input}**..."):
            new_lkpd = generate_lkpd(theme_input)
        
        if new_lkpd:
            st.session_state.lkpd_data = new_lkpd
            save_jawaban_siswa("LKPD", new_lkpd) # Simpan LKPD ke DB
            st.success("LKPD berhasil dibuat dan disimpan!")
            # Muat ulang LKPD dari DB untuk sinkronisasi
            st.session_state.lkpd_data = load_lkpd() 
        else:
            st.error("Gagal mendapatkan LKPD dari AI. Cek log atau coba tema lain.")
            st.session_state.lkpd_data = None


    st.divider()

    # 3. Tampilkan LKPD
    if st.session_state.lkpd_data:
        lkpd = st.session_state.lkpd_data
        st.subheader(f"2. Pratinjau LKPD: {lkpd.get('judul', 'Judul Tidak Ada')}")
        
        st.info(f"**Tujuan Pembelajaran:** {', '.join(lkpd.get('tujuan_pembelajaran', ['-']))}")
        
        with st.expander("Materi Singkat"):
            st.markdown(lkpd.get('materi_singkat', 'Materi tidak tersedia.'))
            
        st.markdown("---")
        
        for i, kegiatan in enumerate(lkpd.get('kegiatan', [])):
            st.markdown(f"#### 📝 Kegiatan {i+1}: {kegiatan.get('nama', 'Kegiatan Tanpa Nama')}")
            st.markdown(f"**Petunjuk:** {kegiatan.get('petunjuk', '-')}")
            
            # Tampilkan Tugas Interaktif
            st.markdown("**Tugas Interaktif (Instruksi):**")
            for j, tugas in enumerate(kegiatan.get('tugas_interaktif', [])):
                st.markdown(f"- {tugas}")
            
            # Tampilkan Pertanyaan Pemantik
            st.markdown("**Pertanyaan Pemantik (Akan dijawab Siswa):**")
            for k, q_obj in enumerate(kegiatan.get('pertanyaan_pemantik', [])):
                st.markdown(f"**{i+1}.{k+1}.** {q_obj.get('pertanyaan', 'Pertanyaan tidak ada')}")
            
            st.markdown("---")
    else:
        st.info("Silakan masukkan tema dan klik 'Generate LKPD' untuk memulai.")

def guru_jawaban_page():
    st.title("📚 Dashboard Guru: Hasil Jawaban Siswa")

    # 1. Load Semua Jawaban Siswa
    all_jawaban = load_all_jawaban()
    
    if not all_jawaban:
        st.warning("Belum ada jawaban siswa yang tersimpan.")
        return

    # Filter data hanya untuk jawaban (bukan LKPD asli)
    jawaban_siswa = [item for item in all_jawaban if item['user_id'] != 'LKPD']
    
    if not jawaban_siswa:
        st.warning("Belum ada jawaban siswa yang tersimpan.")
        return

    # 2. Tampilkan Ringkasan dalam DataFrame
    data_summary = []
    for item in jawaban_siswa:
        data_summary.append({
            "Siswa": item['user_id'].replace('Siswa_', ''),
            "Tanggal": item['timestamp'].strftime("%Y-%m-%d %H:%M"),
            "Jumlah Soal": len(item['jawaban_siswa']),
            "Sudah Dinilai": sum(1 for j in item['jawaban_siswa'] if 'score' in j and j.get('score') != 'Belum Dinilai'),
            "Skor Total": sum(j.get('score', 0) if isinstance(j.get('score'), int) else 0 for j in item['jawaban_siswa'])
        })
    
    df = pd.DataFrame(data_summary)
    st.subheader("Ringkasan Nilai Siswa")
    st.dataframe(df, use_container_width=True)
    
    st.divider()
    
    # 3. Proses Penilaian
    st.subheader("Proses Penilaian Jawaban")

    if st.button("✨ Nilai Semua Jawaban Siswa"):
        if not db_ready: # Menggunakan db_ready status
            st.error("Koneksi Gemini/Database belum siap.")
            return

        with st.spinner("AI sedang menilai semua jawaban siswa... Proses ini mungkin memakan waktu."):
            try:
                # Memanggil fungsi scoring yang telah di-robust
                results = score_all_jawaban(jawaban_siswa) 
                
                # Tampilkan hasil penilaian
                st.success("Penilaian Selesai!")
                # Tampilkan ringkasan penilaian yang diperbarui
                updated_summary = []
                for res in results:
                    # Cari item asli untuk mendapatkan total skor
                    item = next((i for i in load_all_jawaban() if i['user_id'] == f"Siswa_{res['Siswa']}"), None)
                    if item:
                        total_score = sum(j.get('score', 0) if isinstance(j.get('score'), int) else 0 for j in item['jawaban_siswa'])
                        updated_summary.append({
                            "Siswa": res['Siswa'],
                            "Jumlah Soal": res['Jumlah Soal'],
                            "Skor Total Baru": total_score,
                            "Status": res['Status']
                        })
                
                st.dataframe(pd.DataFrame(updated_summary), use_container_width=True)
                # Force rerun to update detail view below
                st.rerun()

            except Exception as e:
                st.error(f"Gagal saat proses penilaian massal: {e}")
                logger.error(f"Error during mass scoring: {e}")

    st.divider()

    # 4. Detail Jawaban Siswa
    st.subheader("Detail Jawaban Siswa")
    
    siswa_ids = [item['user_id'] for item in jawaban_siswa]
    if not siswa_ids:
        st.warning("Tidak ada data siswa untuk ditampilkan.")
        return

    selected_user = st.selectbox(
        "Pilih Siswa untuk melihat detail:",
        options=siswa_ids
    )
    
    if selected_user:
        # Muat ulang data siswa secara spesifik
        detail_data = load_all_jawaban(user_id=selected_user)
        detail_data = detail_data[0] if detail_data else None

        if detail_data:
            st.markdown(f"#### Hasil untuk {selected_user.replace('Siswa_', '')} (LKPD: {detail_data.get('lkpd_title', 'Tanpa Judul')})")
            
            for i, j in enumerate(detail_data['jawaban_siswa']):
                score = j.get('score', 'Belum Dinilai')
                feedback = j.get('feedback', 'Belum Dinilai')

                # Menampilkan pertanyaan, jawaban, skor, dan feedback
                with st.container(border=True):
                    st.markdown(f"**Pertanyaan {i+1}:** {j['pertanyaan']}")
                    st.markdown(f"**Jawaban Siswa:** {j['jawaban']}")
                    st.markdown(f"**Nilai:** **{score}** / 100")
                    st.markdown(f"**Feedback AI:** {feedback}")
                    
# --- Tampilan Halaman Siswa ---

def siswa_page():
    st.title(f"🧑‍🎓 Halaman Siswa: {st.session_state.current_user.replace('Siswa_', '')}")
    
    # 1. Load LKPD terbaru (yang sudah di-generate Guru)
    lkpd = load_lkpd() 
    st.session_state.lkpd_data = lkpd

    if not lkpd:
        st.warning("LKPD belum tersedia. Mohon Guru membuat LKPD terlebih dahulu.")
        return

    st.header(lkpd.get('judul', 'LKPD Interaktif'))
    st.info(f"**Tujuan Pembelajaran:** {', '.join(lkpd.get('tujuan_pembelajaran', ['-']))}")
    
    with st.expander("Materi Singkat"):
        st.markdown(lkpd.get('materi_singkat', 'Materi tidak tersedia.'))
    
    st.markdown("---")
    
    # 2. Formulir Jawaban Siswa
    
    jawaban_form = st.container()
    
    # Memuat jawaban yang sudah ada untuk pengguna ini (jika ada)
    all_jawaban_user = load_all_jawaban(user_id=st.session_state.current_user)
    current_jawaban = next((item for item in all_jawaban_user if item['user_id'] == st.session_state.current_user), None)
    
    # Inisialisasi/Update daftar jawaban siswa untuk formulir
    if not st.session_state.siswa_answers or len(st.session_state.siswa_answers) == 0:
        if current_jawaban:
            st.session_state.siswa_answers = [j['jawaban'] for j in current_jawaban['jawaban_siswa']]
        else:
            total_questions = sum(len(kegiatan.get('pertanyaan_pemantik', [])) for kegiatan in lkpd.get('kegiatan', []))
            st.session_state.siswa_answers = [""] * total_questions
        
    
    # Tampilkan formulir
    with jawaban_form:
        st.subheader("Jawab Pertanyaan Pemantik")
        
        # Iterasi melalui semua pertanyaan di LKPD
        q_idx = 0
        all_questions = []
        for i, kegiatan in enumerate(lkpd.get('kegiatan', [])):
            st.markdown(f"##### Kegiatan {i+1}: {kegiatan.get('nama', 'Kegiatan Tanpa Nama')}")
            
            for j, q_obj in enumerate(kegiatan.get('pertanyaan_pemantik', [])):
                pertanyaan_text = q_obj.get('pertanyaan', f"Pertanyaan {q_idx+1} tidak ada")
                
                # Tambahkan pertanyaan ke daftar global untuk saving
                all_questions.append(pertanyaan_text) 
                
                # Pastikan indeks ada di st.session_state.siswa_answers
                current_answer = st.session_state.siswa_answers[q_idx] if q_idx < len(st.session_state.siswa_answers) else ""

                # Tampilkan area teks untuk jawaban
                st.text_area(
                    label=f"**{q_idx+1}.** {pertanyaan_text}",
                    value=current_answer,
                    key=f"answer_{q_idx}",
                    help="Jawab pertanyaan ini di sini."
                )
                q_idx += 1
                
        # 3. Tombol Simpan Jawaban
        if st.button("💾 Simpan Jawaban", type="primary"):
            if not db_ready:
                st.error("Koneksi database tidak tersedia.")
                return
            
            # Kumpulkan jawaban dari state form
            siswa_data = []
            for idx, q_text in enumerate(all_questions):
                # Ambil jawaban terbaru dari key Streamlit
                answer = st.session_state.get(f"answer_{idx}", "") 
                
                # Gabungkan dengan data skor/feedback jika sudah ada
                existing_score = current_jawaban['jawaban_siswa'][idx].get('score', 'Belum Dinilai') if current_jawaban and idx < len(current_jawaban['jawaban_siswa']) else 'Belum Dinilai'
                existing_feedback = current_jawaban['jawaban_siswa'][idx].get('feedback', 'Belum Dinilai') if current_jawaban and idx < len(current_jawaban['jawaban_siswa']) else 'Belum Dinilai'

                siswa_data.append({
                    "pertanyaan": q_text,
                    "jawaban": answer,
                    "score": existing_score,
                    "feedback": existing_feedback
                })
            
            # Simpan ke database
            save_jawaban_siswa(st.session_state.current_user, siswa_data, lkpd.get('judul', 'LKPD Tanpa Judul'))
            st.success("Jawaban Anda berhasil disimpan!")
            st.session_state.siswa_answers = [d['jawaban'] for d in siswa_data] # Update state

def siswa_nilai_page():
    st.title(f"💯 Hasil Penilaian LKPD")

    # 1. Load Jawaban Siswa
    all_jawaban_user = load_all_jawaban(user_id=st.session_state.current_user)
    current_jawaban = next((item for item in all_jawaban_user if item['user_id'] == st.session_state.current_user), None)
    
    if not current_jawaban:
        st.warning("Anda belum menyimpan jawaban apapun.")
        return

    st.info(f"LKPD: **{current_jawaban.get('lkpd_title', 'Tanpa Judul')}** | Disimpan pada: **{current_jawaban['timestamp'].strftime('%d %B %Y %H:%M')}**")
    
    total_score = sum(j.get('score', 0) if isinstance(j.get('score'), int) else 0 for j in current_jawaban['jawaban_siswa'])
    total_questions = len(current_jawaban['jawaban_siswa'])
    
    st.markdown(f"## Skor Total Anda: **{total_score}** / {total_questions * 100}")
    st.divider()
    
    # 2. Tampilkan Detail Jawaban, Skor, dan Feedback
    for i, j in enumerate(current_jawaban['jawaban_siswa']):
        score = j.get('score', 'Belum Dinilai')
        feedback = j.get('feedback', 'Belum Dinilai')
        
        # Penanganan display untuk skor dan feedback
        score_display = score if isinstance(score, int) else 'Belum Dinilai'
        feedback_display = feedback if feedback != 'Belum Dinilai' else "Nilai dan Feedback AI akan muncul di sini setelah Guru memproses penilaian."
        
        with st.container(border=True):
            st.markdown(f"**Pertanyaan {i+1}:** {j['pertanyaan']}")
            st.markdown(f"**Jawaban Anda:** {j['jawaban']}")
            st.markdown("---")
            
            if score_display == 'Belum Dinilai':
                 st.info(feedback_display)
            else:
                st.markdown(f"**Nilai AI:** <span style='font-size: 1.5em; font-weight: bold;'>{score_display} / 100</span>", unsafe_allow_html=True)
                st.markdown(f"**Feedback AI:** {feedback_display}")
        
    st.divider()

# --- Pengendali Halaman Utama ---
if st.session_state.page == 'guru':
    guru_page()
elif st.session_state.page == 'guru_jawaban':
    guru_jawaban_page()
elif st.session_state.page == 'siswa':
    siswa_page()
elif st.session_state.page == 'siswa_nilai':
    siswa_nilai_page()
