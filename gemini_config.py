import streamlit as st
import os
import logging
from datetime import datetime
from google import genai
from google.generativeai.errors import APIError
import json # Diperlukan untuk parsing JSON dari model

# --- Konfigurasi Logging ---
logger = logging.getLogger('GeminiConfig')
logger.setLevel(logging.INFO)
# Hanya tambahkan handler jika belum ada untuk menghindari duplikasi log di Streamlit
if not logger.handlers:
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)

# --- Variabel Global untuk Status Koneksi ---
# Catatan: Variabel ini akan diinisialisasi di st.session_state di app.py
DB = None
AI_READY = False

# --- Konfigurasi Database (Mock untuk fokus pada API Key) ---
# Dalam proyek nyata, ini akan menjadi Firebase/Firestore
def init_database():
    """Menginisialisasi database (menggunakan mock DB di session_state)."""
    global DB
    if 'mock_db' not in st.session_state:
        st.session_state.mock_db = {
            'LKPD': [],
            'Jawaban_Siswa': []
        }
    DB = st.session_state.mock_db
    logger.info("Database (Mock) berhasil diinisialisasi.")
    return True

# --- FUNGSI KRITIS: INISIALISASI GEMINI ---
# Caching digunakan agar koneksi mahal hanya terjadi sekali
@st.cache_resource(show_spinner=False)
def init_gemini() -> bool:
    """Mencari dan menginisialisasi Gemini API Key dari 3 lapisan (Manual, Secrets, Env)."""
    global AI_READY
    
    # Inisialisasi Database (Mock)
    db_ready = init_database()
    
    # 1. Lapis Pertama: Input Manual dari Sidebar (dari st.session_state)
    API_KEY = st.session_state.get('manual_api_key', '').strip()
    logger.info(f"Lapis 1 (Manual Input) Check: {'Found' if API_KEY else 'Not Found'}")

    # 2. Lapis Kedua: Streamlit Secrets (Pengecekan Tahan Banting)
    if not API_KEY:
        try:
            # Menggunakan .get() untuk menangani kasus st.secrets tidak memiliki key tersebut
            API_KEY = st.secrets.get("GEMINI_API_KEY", "").strip()
            logger.info(f"Lapis 2 (Streamlit Secrets) Check: {'Found' if API_KEY else 'Not Found'}")
        except Exception as e:
            logger.error(f"Error saat membaca st.secrets: {e}. Mencoba Environment Variables.")
            
    # 3. Lapis Ketiga: Environment Variable (Fallback OS)
    if not API_KEY:
        API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
        logger.info(f"Lapis 3 (Environment Variable) Check: {'Found' if API_KEY else 'Not Found'}")


    if not API_KEY:
        logger.error("Kunci API Gemini tidak ditemukan di SEMUA lapisan.")
        AI_READY = False
        return db_ready

    # --- Konfigurasi API ---
    try:
        genai.configure(api_key=API_KEY)
        # Uji koneksi sederhana (opsional tapi baik)
        # genai.get_model('gemini-2.5-flash').generate_content("ping", stream=False)
        logger.info("✅ Koneksi Gemini API berhasil dikonfigurasi.")
        AI_READY = True
        return db_ready
        
    except APIError as e:
        logger.error(f"❌ Gemini API menolak kunci. Error: {e}. Kunci kemungkinan tidak valid atau dicabut.")
        AI_READY = False
        return db_ready
    except Exception as e:
        logger.error(f"❌ Kesalahan umum saat konfigurasi Gemini: {e}")
        AI_READY = False
        return db_ready

# --- Fungsi Utility (Hanya perubahan kecil untuk menggunakan logger) ---

def load_lkpd():
    """Memuat LKPD terakhir yang disimpan oleh Guru."""
    if 'mock_db' not in st.session_state: return None
    
    # Cari LKPD terakhir yang disimpan oleh 'LKPD' user ID
    lkpd_list = [item for item in st.session_state.mock_db['LKPD'] if item.get('user_id') == 'LKPD']
    if lkpd_list:
        logger.info(f"LKPD terakhir dimuat. Judul: {lkpd_list[-1].get('lkpd_title')}")
        return lkpd_list[-1]['jawaban_siswa']
    return None

def save_jawaban_siswa(user_id, data, lkpd_title="LKPD Tanpa Judul"):
    """Menyimpan jawaban siswa atau LKPD asli ke database."""
    if 'mock_db' not in st.session_state: return False
    
    is_lkpd = (user_id == 'LKPD')
    collection_name = 'LKPD' if is_lkpd else 'Jawaban_Siswa'

    new_data = {
        "user_id": user_id,
        "timestamp": datetime.now(),
        "lkpd_title": lkpd_title,
        "jawaban_siswa": data if not is_lkpd else data # Untuk LKPD, data adalah struktur LKPD
    }
    
    # Hapus data lama (simulasi update data)
    st.session_state.mock_db[collection_name] = [
        item for item in st.session_state.mock_db[collection_name] if item['user_id'] != user_id
    ]

    st.session_state.mock_db[collection_name].append(new_data)
    logger.info(f"Data {user_id} berhasil disimpan ke {collection_name}.")
    return True

def load_all_jawaban(user_id=None):
    """Memuat semua jawaban siswa, atau jawaban spesifik."""
    if 'mock_db' not in st.session_state: return []
    
    all_answers = st.session_state.mock_db['Jawaban_Siswa'] + st.session_state.mock_db['LKPD']
    
    if user_id:
        return [item for item in all_answers if item['user_id'] == user_id]
        
    return all_answers

# --- FUNGSI AI ---

def generate_lkpd(theme: str) -> dict or None:
    """Menggunakan Gemini untuk menghasilkan struktur LKPD dalam format JSON."""
    global AI_READY
    if not AI_READY:
        logger.warning("Gemini AI tidak siap.")
        return None

    system_prompt = (
        "Anda adalah generator Lembar Kerja Peserta Didik (LKPD) yang ahli. "
        "Tugas Anda adalah membuat LKPD yang interaktif dan lengkap berdasarkan tema yang diberikan. "
        "Hasil harus dalam format JSON yang spesifik. Pastikan JSON yang Anda hasilkan adalah valid dan murni, "
        "tanpa tambahan Markdown atau teks penjelasan. Gunakan bahasa Indonesia baku."
    )
    
    user_prompt = (
        f"Buatkan LKPD lengkap tentang '{theme}'. "
        "Sertakan: 'judul', 'tujuan_pembelajaran' (array), 'materi_singkat' (string), "
        "dan 'kegiatan' (array of objects). Setiap 'kegiatan' harus memiliki 'nama', 'petunjuk', "
        "'tugas_interaktif' (array of strings), dan 'pertanyaan_pemantik' (array of objects, "
        "di mana setiap objek berisi 'pertanyaan' dan 'jawaban_kunci' untuk penilaian AI)."
    )
    
    # Skema Respons JSON yang Diperlukan
    response_schema = {
        "type": "OBJECT",
        "properties": {
            "judul": {"type": "STRING", "description": "Judul LKPD."},
            "tujuan_pembelajaran": {"type": "ARRAY", "items": {"type": "STRING"}},
            "materi_singkat": {"type": "STRING"},
            "kegiatan": {
                "type": "ARRAY",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "nama": {"type": "STRING"},
                        "petunjuk": {"type": "STRING"},
                        "tugas_interaktif": {"type": "ARRAY", "items": {"type": "STRING"}},
                        "pertanyaan_pemantik": {
                            "type": "ARRAY",
                            "items": {
                                "type": "OBJECT",
                                "properties": {
                                    "pertanyaan": {"type": "STRING"},
                                    "jawaban_kunci": {"type": "STRING", "description": "Jawaban kunci detail untuk penilaian."}
                                }
                            }
                        }
                    }
                }
            }
        },
        "required": ["judul", "tujuan_pembelajaran", "materi_singkat", "kegiatan"]
    }

    try:
        response = genai.GenerativeModel('gemini-2.5-flash').generate_content(
            contents=[user_prompt],
            config={
                "system_instruction": system_prompt,
                "response_mime_type": "application/json",
                "response_schema": response_schema
            }
        )
        
        # Output adalah string JSON, perlu di-parse
        lkpd_data = json.loads(response.text)
        return lkpd_data
        
    except Exception as e:
        logger.error(f"Gagal generate LKPD dari AI: {e}")
        return None

def score_jawaban(jawaban_siswa: dict, kunci_jawaban: str) -> tuple[int, str] or tuple[str, str]:
    """Menggunakan Gemini untuk memberikan skor (0-100) dan feedback."""
    global AI_READY
    if not AI_READY:
        logger.warning("Gemini AI tidak siap untuk menilai.")
        return ("Belum Dinilai", "Gemini AI tidak aktif.")
        
    system_prompt = (
        "Anda adalah penilai (scorer) otomatis yang adil. "
        "Bandingkan 'jawaban_siswa' dengan 'jawaban_kunci' (yang sangat detail). "
        "Berikan skor antara 0 hingga 100 dan berikan feedback konstruktif. "
        "Pastikan output Anda adalah JSON murni (Skema: {score: int, feedback: string})."
    )
    
    user_prompt = (
        f"Jawaban Kunci (Panduan Penilaian): {kunci_jawaban}\n\n"
        f"Jawaban Siswa yang akan dinilai: {jawaban_siswa['jawaban']}"
    )
    
    response_schema = {
        "type": "OBJECT",
        "properties": {
            "score": {"type": "INTEGER", "description": "Skor 0-100."},
            "feedback": {"type": "STRING", "description": "Feedback konstruktif dan penjelasan skor."}
        },
        "required": ["score", "feedback"]
    }

    try:
        response = genai.GenerativeModel('gemini-2.5-flash').generate_content(
            contents=[user_prompt],
            config={
                "system_instruction": system_prompt,
                "response_mime_type": "application/json",
                "response_schema": response_schema
            }
        )
        
        result = json.loads(response.text)
        score = result.get('score', 0)
        feedback = result.get('feedback', 'Penilaian Otomatis Selesai.')
        
        # Sanitasi skor
        score = max(0, min(100, score))
        
        return (score, feedback)
        
    except Exception as e:
        logger.error(f"Gagal menilai jawaban: {e}")
        return ("Belum Dinilai", "Gagal mendapatkan penilaian dari AI.")

def score_all_jawaban(all_siswa_data: list):
    """Memproses penilaian untuk semua jawaban siswa yang belum dinilai."""
    
    # 1. Muat LKPD asli untuk mendapatkan kunci jawaban
    lkpd_original = load_lkpd()
    if not lkpd_original:
        logger.error("LKPD asli (kunci jawaban) tidak ditemukan.")
        return False
        
    # Kumpulkan semua pertanyaan pemantik dari LKPD asli untuk mendapatkan kunci jawaban
    lkpd_questions = []
    for kegiatan in lkpd_original.get('kegiatan', []):
        lkpd_questions.extend(kegiatan.get('pertanyaan_pemantik', []))

    if not lkpd_questions:
        logger.error("Tidak ada pertanyaan ditemukan di LKPD asli.")
        return False

    # 2. Iterasi melalui setiap data siswa
    for siswa_entry in all_siswa_data:
        updated = False
        jawaban_siswa_baru = siswa_entry['jawaban_siswa']
        
        for i, jawaban in enumerate(jawaban_siswa_baru):
            # Cek apakah skor sudah ada atau masih 'Belum Dinilai'
            if isinstance(jawaban.get('score'), int) and jawaban.get('score') >= 0:
                 continue # Sudah dinilai, lewati
            
            if i < len(lkpd_questions):
                kunci_jawaban = lkpd_questions[i].get('jawaban_kunci', 'Tidak ada kunci.')
                
                # Panggil fungsi penilaian AI
                score, feedback = score_jawaban(jawaban, kunci_jawaban)
                
                # Update data
                jawaban_siswa_baru[i]['score'] = score
                jawaban_siswa_baru[i]['feedback'] = feedback
                updated = True
                
        if updated:
            # Simpan data siswa yang sudah diupdate ke DB
            save_jawaban_siswa(
                siswa_entry['user_id'], 
                jawaban_siswa_baru, 
                siswa_entry.get('lkpd_title', 'LKPD Tanpa Judul')
            )
            logger.info(f"Jawaban {siswa_entry['user_id']} berhasil dinilai dan diupdate.")
            
    return True
