import os
import json
import uuid
import logging
import re 
from datetime import datetime
from typing import Optional, Dict, Any, List

# --- Third-party libraries ---
import streamlit as st
import google.generativeai as genai

# --- Konfigurasi dan Logger ---
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# --- Inisialisasi Gemini API dan Database (Firestore Mock) ---

@st.cache_resource(show_spinner=False)
def init_gemini() -> bool:
    """
    Menginisialisasi Konfigurasi Gemini dengan 3 lapis otentikasi (Manual > Secrets > Env). 
    Mengembalikan status bool koneksi AI/DB.
    """
    
    # 1. Lapis Pertama: Input Manual dari Sidebar (dari app.py)
    API_KEY = st.session_state.get('manual_api_key', '')
    
    # 2. Lapis Kedua: Streamlit Secrets
    if not API_KEY:
        API_KEY = st.secrets.get("GEMINI_API_KEY", "")
        
    # 3. Lapis Ketiga: Environment Variables
    if not API_KEY:
        API_KEY = os.environ.get("GEMINI_API_KEY", "")
        
    # Final Check
    if not API_KEY:
        st.sidebar.error("❌ Kunci API Gemini tidak ditemukan di mana pun (Secrets/Env/Input).")
        return False
    
    try:
        # Menggunakan genai.configure() untuk kompatibilitas SDK yang lebih luas
        genai.configure(api_key=API_KEY)
        
        # Mock Database: Menggunakan session_state sebagai pengganti Firestore
        if 'mock_db' not in st.session_state:
            st.session_state.mock_db = {} 
        
        logger.info("✅ Gemini AI and Mock DB initialized.")
        return True # Berhasil
        
    except Exception as e:
        # Jika konfigurasi gagal (biasanya karena kunci tidak valid)
        st.sidebar.error(f"Error saat mengkonfigurasi Gemini AI. Kunci mungkin tidak valid.")
        logger.error(f"Initialization failed: {e}")
        return False # Gagal

# --- Operasi Database (Mock Firestore) ---

def load_lkpd() -> Optional[Dict[str, Any]]:
    """Memuat LKPD yang terakhir disimpan (dengan user_id='LKPD')."""
    if 'mock_db' in st.session_state and 'LKPD' in st.session_state.mock_db:
        # LKPD disimpan di bawah 'LKPD' dengan kunci 'jawaban_siswa' yang berisi struktur LKPD
        return st.session_state.mock_db['LKPD'].get('jawaban_siswa') 
    return None

def save_jawaban_siswa(user_id: str, data: Any, lkpd_title: str = "LKPD Terbaru"):
    """Menyimpan data LKPD atau jawaban siswa ke mock database."""
    if 'mock_db' not in st.session_state:
        logger.error("Database not initialized.")
        return
        
    st.session_state.mock_db[user_id] = {
        'user_id': user_id,
        'lkpd_title': lkpd_title,
        'jawaban_siswa': data,
        'timestamp': datetime.now()
    }
    logger.info(f"Data saved for user_id: {user_id}")

def load_all_jawaban(user_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Memuat semua atau spesifik jawaban dari mock database."""
    if 'mock_db' not in st.session_state:
        return []
    
    if user_id:
        return [st.session_state.mock_db.get(user_id)] if user_id in st.session_state.mock_db else []
    else:
        # Filter agar LKPD master tidak ditampilkan di daftar jawaban siswa
        return [data for uid, data in st.session_state.mock_db.items() if uid != 'LKPD']


# --- Fungsi Generasi Konten AI (LKPD) ---

def generate_lkpd(theme: str) -> Optional[Dict[str, Any]]:
    """
    Meminta AI untuk membuat LKPD baru menggunakan Structured Output (JSON Schema)
    untuk menjamin format valid.
    """
    if not genai.get_default_model(): 
        logger.error("Gemini model is not configured.")
        return None 

    # --- JSON SCHEMA WAJIB UNTUK LKPD ---
    lkpd_schema = {
        "type": "OBJECT",
        "properties": {
            "judul": {"type": "STRING", "description": "Judul LKPD yang menarik dan sesuai tema."},
            "tujuan_pembelajaran": {
                "type": "ARRAY",
                "items": {"type": "STRING"},
                "description": "Daftar tujuan pembelajaran yang relevan (minimal 2)."
            },
            "materi_singkat": {"type": "STRING", "description": "Ringkasan materi 2-3 paragraf."},
            "kegiatan": {
                "type": "ARRAY",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "nama": {"type": "STRING", "description": "Nama Kegiatan (Misal: Eksplorasi Konsep)."},
                        "petunjuk": {"type": "STRING", "description": "Petunjuk jelas untuk siswa."},
                        "tugas_interaktif": {
                            "type": "ARRAY",
                            "items": {"type": "STRING"},
                            "description": "Instruksi tugas yang melibatkan eksplorasi."
                        },
                        "pertanyaan_pemantik": {
                            "type": "ARRAY",
                            "items": {
                                "type": "OBJECT",
                                "properties": {
                                    "pertanyaan": {"type": "STRING", "description": "Pertanyaan wajib untuk dijawab siswa."}
                                },
                                "required": ["pertanyaan"]
                            },
                            "description": "Daftar pertanyaan yang membutuhkan jawaban tekstual dari siswa."
                        }
                    },
                    "required": ["nama", "petunjuk", "tugas_interaktif", "pertanyaan_pemantik"]
                }
            }
        },
        "required": ["judul", "tujuan_pembelajaran", "materi_singkat", "kegiatan"]
    }
    
    prompt = f"""
    Anda adalah pakar kurikulum dan perancang LKPD (Lembar Kerja Peserta Didik).
    Buat LKPD INTERAKTIF untuk tema "{theme}" SMP/SMA.
    Isi setiap bagian dengan konten edukatif yang kaya.
    """
    
    try:
        response = genai.generate_content(
            model="gemini-2.5-flash", 
            contents=prompt,
            config={
                # Memaksa model mengeluarkan JSON dengan schema yang ditentukan
                "response_mime_type": "application/json",
                "response_schema": lkpd_schema,
                "temperature": 0.2 # Menjaga keluaran tetap fokus dan terstruktur
            }
        )
        
        # 1. Pemeriksaan Respons Kosong atau Diblokir
        if not response.text:
            block_reason_code = response.prompt_feedback.block_reason
            if block_reason_code.name != "BLOCK_REASON_UNSPECIFIED":
                st.error(f"Konten diblokir oleh filter keamanan API. Alasan: {block_reason_code.name}. Coba tema lain.")
            else:
                st.error("Teks respons kosong dari API. Koneksi mungkin terputus atau model menolak prompt.")
            return None
        
        # 2. Parsing JSON (Sederhana karena format sudah dijamin schema)
        try:
            data = json.loads(response.text.strip())
        except json.JSONDecodeError as e:
            # Walaupun jarang, jika ini terjadi berarti ada masalah serius pada keluaran model
            # Di sini kita masih menyimpan error yang lebih spesifik (Level 2)
            st.error(f"JSON Decode Error (Level 2). Respons model: {response.text[:100]}... Error: {e}")
            return None
        
        # 3. Safety Check (Validasi Kunci Wajib) - Redundan karena schema, tapi aman.
        required_keys = ['judul', 'tujuan_pembelajaran', 'materi_singkat', 'kegiatan']
        if not all(key in data for key in required_keys):
            st.error(f"Kunci wajib hilang dalam struktur JSON akhir, meskipun schema telah diterapkan. Coba lagi.")
            return None
        
        logger.info(f"✅ LKPD generated for theme: {theme}")
        return data
        
    except Exception as e:
        # Peningkatan logging untuk diagnosis
        # Ini menangkap masalah koneksi, timeout, atau kunci API yang salah (di luar parsing JSON)
        # Inilah yang paling mungkin menghasilkan error "Gagal menghasilkan LKPD. Coba lagi atau periksa koneksi API."
        st.error(f"Gagal menghasilkan LKPD: Terjadi kesalahan API/Koneksi. Detail: {e}")
        logger.error(f"Generate LKPD fatal error: {type(e).__name__} - {e}")
        return None

# --- Fungsi Penilaian AI ---

def score_jawaban(jawaban_text: str, pertanyaan: str) -> Dict[str, Any]:
    """Meminta AI untuk menilai satu jawaban dan memberikan feedback menggunakan Structured Output."""
    if not genai.get_default_model(): return {"score": 0, "feedback": "AI Not Ready"}
    
    # --- JSON SCHEMA WAJIB UNTUK PENILAIAN ---
    score_schema = {
        "type": "OBJECT",
        "properties": {
            "score": {"type": "INTEGER", "description": "Nilai numerik antara 0 dan 100."},
            "feedback": {"type": "STRING", "description": "Feedback singkat dan konstruktif untuk siswa."}
        },
        "required": ["score", "feedback"]
    }

    prompt = f"""
    Anda adalah penilai ahli. Berikan nilai 0-100 untuk 'Jawaban Siswa' berdasarkan 'Pertanyaan' dan berikan 'feedback' singkat.
    
    Pertanyaan: {pertanyaan}
    Jawaban Siswa: {jawaban_text}
    """
    
    try:
        response = genai.generate_content(
            model="gemini-2.5-flash", 
            contents=prompt,
            config={
                # Memaksa model mengeluarkan JSON untuk penilaian
                "response_mime_type": "application/json",
                "response_schema": score_schema,
                "temperature": 0.1 # Sangat rendah agar skor dan feedback konsisten
            }
        )
        
        # Pemeriksaan Respons Kosong atau Diblokir
        if not response.text:
            block_reason_code = response.prompt_feedback.block_reason
            return {
                "score": 0,
                "feedback": f"Gagal penilaian: Konten diblokir oleh filter keamanan ({block_reason_code.name})" if block_reason_code.name != "BLOCK_REASON_UNSPECIFIED" else "Gagal penilaian: Teks respons kosong dari API."
            }

        # Parsing JSON
        try:
            score_data = json.loads(response.text.strip())
        except json.JSONDecodeError:
             # Fallback jika Structured Output gagal (sangat jarang)
            json_str_match = re.search(r'\{.*\}', response.text.strip(), re.DOTALL)
            if json_str_match:
                json_str = json_str_match.group(0)
                json_str = json_str.strip('`').strip()
                score_data = json.loads(json_str)
            else:
                raise json.JSONDecodeError("Failed to find JSON block in AI response", response.text, 0)
        
        # Validasi skor dan konversi ke int
        try:
            score_value = int(score_data.get('score', 0))
        except ValueError:
            score_value = 0 
            
        score_data['score'] = min(max(score_value, 0), 100) # Pastikan skor 0-100
        
        if 'feedback' not in score_data:
            score_data['feedback'] = "Feedback tidak tersedia dari AI."
            
        logger.info(f"📊 Scored: {score_data['score']}")
        return score_data
    except Exception as e:
        logger.error(f"Scoring error for: {jawaban_text[:30]}... Detail: {e}")
        return {
            "score": 0,
            "feedback": f"Gagal mendapatkan penilaian AI karena error format/koneksi: {e}"
        }

def score_all_jawaban(all_jawaban: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Menilai semua jawaban siswa yang belum dinilai dan menyimpan hasilnya."""
    
    if 'mock_db' not in st.session_state: return []
    
    results = []
    
    for item in all_jawaban:
        user_id = item['user_id']
        jawaban_siswa = item['jawaban_siswa']
        
        updated_jawaban = []
        is_updated = False
        
        for j in jawaban_siswa:
            # Hanya proses yang belum dinilai atau skornya nol
            if 'score' not in j or j.get('score') == 'Belum Dinilai' or j.get('score') == 0: 
                
                scoring_result = score_jawaban(j['jawaban'], j['pertanyaan'])
                
                j['score'] = scoring_result['score']
                j['feedback'] = scoring_result['feedback']
                is_updated = True
            
            updated_jawaban.append(j)

        if is_updated:
            save_jawaban_siswa(user_id, updated_jawaban, item['lkpd_title'])
            
        results.append({
            "Siswa": user_id.replace('Siswa_', ''),
            "Jumlah Soal": len(updated_jawaban),
            "Skor Total": sum(j.get('score', 0) if isinstance(j.get('score'), int) else 0 for j in updated_jawaban),
            "Status": "Dinilai Ulang" if is_updated else "Sudah Dinilai"
        })

    return results
