import google.generativeai as genai
import streamlit as st
import os
import json
import uuid
from datetime import datetime
import logging
from typing import Optional, Dict, Any, List
import re # Diperlukan untuk ekstraksi JSON yang lebih robust

# --- Konfigurasi dan Logger ---
# Inisialisasi logger untuk debugging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Variabel global untuk instance
_model = None
_db = None

# --- Inisialisasi Gemini API dan Database (Firestore Mock) ---

# Fungsi yang di-cache untuk inisialisasi satu kali
@st.cache_resource(show_spinner=False)
def init_gemini():
    """Menginisialisasi Model Gemini dan Mock Database."""
    global _model, _db
    
    # Dapatkan API Key dari secrets Streamlit
    # Gunakan variabel kosong jika tidak ada secret (asumsi environment akan menyediakannya)
    API_KEY = st.secrets.get("GEMINI_API_KEY", "") 
    
    # Jika API_KEY kosong, setelannya akan ditangani oleh genai.Client
    try:
        # Inisialisasi Model Gemini
        # Model defaultnya adalah gemini-2.5-flash
        _model = genai.Client(api_key=API_KEY).models
        
        # Mock Database: Menggunakan session_state sebagai pengganti Firestore
        if 'mock_db' not in st.session_state:
            # Struktur mock_db: 
            # { user_id: { 'jawaban_siswa': [], 'timestamp': datetime, 'lkpd_title': str } }
            st.session_state.mock_db = {} 
        _db = st.session_state.mock_db
        
        logger.info("✅ Gemini AI and Mock DB initialized.")
        st.sidebar.success("🤖 Gemini gemini-2.5-flash READY")
        return _db, _model
        
    except Exception as e:
        st.sidebar.error(f"Error in init_gemini: {e}")
        logger.error(f"Initialization failed: {e}")
        return None, None

# --- Operasi Database (Mock Firestore) ---

def load_lkpd() -> Optional[Dict[str, Any]]:
    """Memuat LKPD yang terakhir disimpan (dengan user_id='LKPD')."""
    if _db and 'LKPD' in _db:
        # LKPD data disimpan di 'jawaban_siswa' untuk konsistensi struktur
        return _db['LKPD'].get('jawaban_siswa') 
    return None

def save_jawaban_siswa(user_id: str, data: Any, lkpd_title: str = "LKPD Terbaru"):
    """Menyimpan data LKPD atau jawaban siswa ke mock database."""
    if not _db:
        logger.error("Database not initialized.")
        return
        
    _db[user_id] = {
        'user_id': user_id,
        'lkpd_title': lkpd_title,
        'jawaban_siswa': data,
        'timestamp': datetime.now()
    }
    logger.info(f"Data saved for user_id: {user_id}")

def load_all_jawaban(user_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Memuat semua atau spesifik jawaban dari mock database."""
    if not _db:
        return []
    
    if user_id:
        # Load spesifik jawaban
        return [_db.get(user_id)] if user_id in _db else []
    else:
        # Load semua jawaban
        return list(_db.values())

# --- Fungsi Generasi Konten AI (LKPD) ---

def generate_lkpd(theme: str) -> Optional[Dict[str, Any]]:
    """Meminta AI untuk membuat LKPD baru dan mengembalikan JSON yang divalidasi."""
    if not _model: return None

    # Prompt yang diperkuat untuk memaksa format JSON
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
        // Tambahkan kegiatan lain jika diperlukan
      ]
    }}
    """
    
    try:
        # Menggunakan gemini-2.5-flash untuk kecepatan
        response = _model.generate_content(
            model="gemini-2.5-flash", 
            contents=prompt
        )
        
        # 1. Agresif mencari blok JSON dalam respons (robustness check KRITIS)
        try:
            # Mencoba decode langsung
            data = json.loads(response.text.strip())
        except json.JSONDecodeError:
            # Jika gagal, coba ekstrak konten antara tanda kurung kurawal
            json_str_match = re.search(r'\{.*\}', response.text.strip(), re.DOTALL)
            if json_str_match:
                json_str = json_str_match.group(0)
                # Hilangkan backtick markdown jika ada
                json_str = json_str.strip('`').strip()
                data = json.loads(json_str)
            else:
                # Gagal total, lempar error yang lebih jelas
                raise json.JSONDecodeError("Failed to find JSON block in AI response", response.text, 0)
        
        # 2. Safety Check (Validasi Kunci Wajib)
        required_keys = ['judul', 'tujuan_pembelajaran', 'materi_singkat', 'kegiatan']
        if not all(key in data for key in required_keys):
            raise ValueError(f"Missing required keys in final JSON structure. Required: {required_keys}")
        
        logger.info(f"✅ LKPD generated for theme: {theme}")
        return data
        
    except Exception as e:
        logger.error(f"Generate LKPD error: {e}")
        # Tangkap dan tampilkan error yang ditangkap oleh try/except di app.py
        st.error(f"❌ AI Error: Gagal mendapatkan LKPD dari AI. Detail: {e}")
        return None

# --- Fungsi Penilaian AI ---

def score_jawaban(jawaban_text: str, pertanyaan: str) -> Dict[str, Any]:
    """Meminta AI untuk menilai satu jawaban dan memberikan feedback."""
    if not _model: return {"score": 0, "feedback": "AI Not Ready"}

    prompt = f"""
    Anda adalah penilai ahli. Berikan nilai 0-100 untuk 'Jawaban Siswa' berdasarkan 'Pertanyaan' dan berikan 'feedback' singkat.
    
    Pertanyaan: {pertanyaan}
    Jawaban Siswa: {jawaban_text}
    
    Hanya hasilkan **JSON VALID** dengan kunci 'score' (int 0-100) dan 'feedback' (string). Jangan ada teks tambahan.
    Contoh: {{"score": 85, "feedback": "Jawaban Anda sangat lengkap dan relevan..."}}
    """
    
    try:
        response = _model.generate_content(
            model="gemini-2.5-flash", 
            contents=prompt
        )
        
        # LOGIKA JSON EXTRACTION BARU (Robustness Check KRITIS)
        try:
            score_data = json.loads(response.text.strip())
        except json.JSONDecodeError:
            json_str_match = re.search(r'\{.*\}', response.text.strip(), re.DOTALL)
            if json_str_match:
                json_str = json_str_match.group(0)
                # Hilangkan backtick markdown jika ada
                json_str = json_str.strip('`').strip()
                score_data = json.loads(json_str)
            else:
                raise json.JSONDecodeError("Failed to find JSON block in AI response", response.text, 0)
        
        # Validasi skor harus berupa integer
        try:
            score_value = int(score_data.get('score', 0))
        except ValueError:
            score_value = 0 # Jika skor bukan angka, set ke 0
            
        score_data['score'] = score_value
        
        # Pastikan feedback ada
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
    """Menilai semua jawaban siswa yang belum dinilai secara berurutan dan menyimpan hasilnya."""
    if not _db: return []
    
    results = []
    
    for item in all_jawaban:
        user_id = item['user_id']
        jawaban_siswa = item['jawaban_siswa']
        
        updated_jawaban = []
        is_updated = False
        
        for j in jawaban_siswa:
            # Hanya proses yang belum dinilai (score 0 atau 'Belum Dinilai' dari load)
            if 'score' not in j or j.get('score') == 0 or j.get('score') == "Belum Dinilai": 
                
                # Panggil AI untuk menilai
                scoring_result = score_jawaban(j['jawaban'], j['pertanyaan'])
                
                # Update data jawaban dengan hasil scoring
                j['score'] = scoring_result['score']
                j['feedback'] = scoring_result['feedback']
                is_updated = True
            
            updated_jawaban.append(j)

        if is_updated:
            # Simpan data yang telah dinilai kembali ke mock database
            save_jawaban_siswa(user_id, updated_jawaban, item['lkpd_title'])
            
        results.append({
            "Siswa": user_id.replace('Siswa_', ''),
            "Jumlah Soal": len(updated_jawaban),
            "Skor Total": sum(j.get('score', 0) for j in updated_jawaban),
            "Status": "Dinilai Ulang" if is_updated else "Sudah Dinilai"
        })

    return results
