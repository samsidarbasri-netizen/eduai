import google.generativeai as genai
import streamlit as st
import os
import json
import uuid
from datetime import datetime
import logging
from typing import Optional, Dict, Any, List
import re 

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
        return list(st.session_state.mock_db.values())


# --- Fungsi Generasi Konten AI (LKPD) ---

def generate_lkpd(theme: str) -> Optional[Dict[str, Any]]:
    """Meminta AI untuk membuat LKPD baru dan mengembalikan JSON yang divalidasi."""
    if not genai.get_default_model(): 
        logger.error("Gemini model is not configured.")
        return None 

    prompt = f"""
    Anda adalah pakar kurikulum dan perancang LKPD (Lembar Kerja Peserta Didik).
    Buat LKPD INTERAKTIF untuk tema "{theme}" SMP/SMA.
    
    **OUTPUT HANYA JSON VALID** (Tanpa Markdown/backtick, tanpa penjelasan di luar JSON).
    
    Pastikan JSON mengandung SEMUA kunci wajib berikut: 'judul', 'tujuan_pembelajaran', 'materi_singkat', dan 'kegiatan'.
    
    Format JSON harus:
    {{
      "judul": "Judul LKPD yang menarik dan sesuai tema",
      "tujuan_pembelajaran": ["Tujuan 1", "Tujuan 2", "Daftar tujuan pembelajaran yang relevan"],
      "materi_singkat": "Ringkasan materi 2-3 paragraf.",
      "kegiatan": [
        {{
          "nama": "Nama Kegiatan 1 (Misal: Eksplorasi Konsep)",
          "petunjuk": "Petunjuk jelas untuk siswa...",
          "tugas_interaktif": ["Instruksi tugas 1", "Instruksi tugas 2"],
          "pertanyaan_pemantik": [
            {{"pertanyaan": "Pertanyaan wajib 1 terkait konsep utama"}},
            {{"pertanyaan": "Pertanyaan wajib 2 yang membutuhkan analisis"}}
          ]
        }}
      ]
    }}
    """
    
    try:
        response = genai.generate_content(
            model="gemini-2.5-flash", 
            contents=prompt
        )
        
        # 1. Agresif mencari blok JSON dalam respons (robustness check KRITIS)
        try:
            data = json.loads(response.text.strip())
        except json.JSONDecodeError:
            json_str_match = re.search(r'\{.*\}', response.text.strip(), re.DOTALL)
            if json_str_match:
                json_str = json_str_match.group(0)
                json_str = json_str.strip('`').strip()
                data = json.loads(json_str)
            else:
                raise json.JSONDecodeError("Failed to find JSON block in AI response", response.text, 0)
        
        # 2. Safety Check (Validasi Kunci Wajib)
        required_keys = ['judul', 'tujuan_pembelajaran', 'materi_singkat', 'kegiatan']
        if not all(key in data for key in required_keys):
            raise ValueError(f"Missing required keys in final JSON structure. Required: {required_keys}")
        
        logger.info(f"✅ LKPD generated for theme: {theme}")
        return data
        
    except Exception as e:
        logger.error(f"Generate LKPD error: {e}")
        return None

# --- Fungsi Penilaian AI ---

def score_jawaban(jawaban_text: str, pertanyaan: str) -> Dict[str, Any]:
    """Meminta AI untuk menilai satu jawaban dan memberikan feedback."""
    if not genai.get_default_model(): return {"score": 0, "feedback": "AI Not Ready"}

    prompt = f"""
    Anda adalah penilai ahli. Berikan nilai 0-100 untuk 'Jawaban Siswa' berdasarkan 'Pertanyaan' dan berikan 'feedback' singkat.
    
    Pertanyaan: {pertanyaan}
    Jawaban Siswa: {jawaban_text}
    
    Hanya hasilkan **JSON VALID** dengan kunci 'score' (int 0-100) dan 'feedback' (string). Jangan ada teks tambahan.
    Contoh: {{"score": 85, "feedback": "Jawaban Anda sangat lengkap dan relevan..."}}
    """
    
    try:
        response = genai.generate_content(
            model="gemini-2.5-flash", 
            contents=prompt
        )
        
        # LOGIKA JSON EXTRACTION BARU (Robustness Check)
        try:
            score_data = json.loads(response.text.strip())
        except json.JSONDecodeError:
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
            
        score_data['score'] = score_value
        
        if 'feedback' not in score_data:
            score_data['feedback'] = "Feedback tidak tersedia dari AI."
            
        logger.info(f"📊 Scored: {score_value}")
        return score_data
    except Exception as e:
        logger.error(f"Scoring error for: {jawaban_text[:30]}... Detail: {e}")
        return {
            "score": 0,
            "feedback": f"Gagal mendapatkan penilaian AI karena error format: {e}"
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
