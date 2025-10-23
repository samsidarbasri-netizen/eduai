import google.generativeai as genai
import streamlit as st
import os
import json
import uuid
from datetime import datetime
import logging
from typing import Optional, Dict, Any, List

# ========== LOGGING SETUP ==========
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ========== CONSTANTS & SECRETS ==========
LKPD_DIR = "lkpd_outputs"
JAWABAN_DIR = "jawaban_siswa"
# Ambil dari Streamlit Secrets, aman untuk deployment
API_KEY = st.secrets.get("GEMINI_API_KEY", None) 
MODEL_NAME = "gemini-2.5-flash"

# ========== GLOBAL VARIABLES ==========
_model: Optional[genai.GenerativeModel] = None
_init_success: bool = False

# ========== UTILITY FUNCTIONS ==========
def ensure_directories() -> None:
    """Create all required directories (important for Streamlit Cloud storage)"""
    os.makedirs(LKPD_DIR, exist_ok=True)
    os.makedirs(JAWABAN_DIR, exist_ok=True)
    logger.info("✅ Directories created: lkpd_outputs, jawaban_siswa")

def validate_api_key() -> bool:
    """Validate GEMINI_API_KEY exists"""
    if not API_KEY:
        st.sidebar.error("❌ **GEMINI_API_KEY** tidak ditemukan di Secrets.")
        logger.error("API Key missing")
        return False
    return True

# ========== GEMINI INITIALIZATION (PERBAIKAN KRUSIAL ANTI-BLOKIR) ==========
@st.cache_resource
def init_gemini() -> Optional[genai.GenerativeModel]:
    """Initialize Gemini model without an immediate test call to save quota."""
    global _model, _init_success
    
    if _init_success and _model:
        return _model
    
    if not validate_api_key():
        return None
        
    try:
        genai.configure(api_key=API_KEY)
        _model = genai.GenerativeModel(MODEL_NAME)
        
        # PANGGILAN generate_content("Test") TELAH DIHAPUS.
        
        logger.info(f"✅ Gemini {MODEL_NAME} initialized successfully!")
        _init_success = True
        st.sidebar.success(f"🤖 **Gemini {MODEL_NAME} READY**")
        return _model
    except Exception as e:
        error_msg = f"❌ Gemini Init Error: {str(e)}"
        st.sidebar.error(error_msg)
        logger.error(error_msg)
        _model = None
        _init_success = False
        return None

# ... [Fungsi load_lkpd dan Jawaban Management tidak berubah] ...
def load_lkpd(lkpd_id: str) -> Optional[Dict[str, Any]]:
    filepath = os.path.join(LKPD_DIR, f"{lkpd_id}.json")
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data
        except Exception as e:
            logger.error(f"Load LKPD error: {e}")
    return None

def save_jawaban_siswa(lkpd_id: str, nama_siswa: str, jawaban_data: Dict[str, Any]) -> str:
    try:
        clean_nama = "".join(c if c.isalnum() or c.isspace() else '_' for c in nama_siswa).strip().replace(' ', '_')
        unique_id = uuid.uuid4().hex[:6]
        filename = f"{lkpd_id}_{clean_nama}_{unique_id}.json"
        filepath = os.path.join(JAWABAN_DIR, filename)
        
        full_data = {
            **jawaban_data,
            'lkpd_id': lkpd_id,
            'nama_siswa': nama_siswa,
            'waktu_submit': datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            'total_score': 0, # Nilai awal 0
            'feedback': "",
            'strengths': [],
            'improvements': []
        }
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(full_data, f, ensure_ascii=False, indent=2)
        logger.info(f"📝 Jawaban saved: {nama_siswa} - {lkpd_id}")
        return filename
    except Exception as e:
        logger.error(f"Jawaban save error: {e}")
        return ""

def load_all_jawaban(lkpd_id: str) -> List[Dict[str, Any]]:
    jawaban_files = [f for f in os.listdir(JAWABAN_DIR) if f.startswith(lkpd_id) and f.endswith('.json')]
    all_jawaban = []
    for filename in jawaban_files:
        filepath = os.path.join(JAWABAN_DIR, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                data['filename'] = filename # Sisipkan filename untuk update skor nanti
                all_jawaban.append(data)
        except Exception as e:
            logger.error(f"Load jawaban error {filename}: {e}")
    return all_jawaban

# ========== AI GENERATION (LKPD) & SCORING ==========
@st.cache_data(show_spinner=False)
def generate_lkpd(theme: str) -> Optional[Dict[str, Any]]:
    # ... [Logika generate_lkpd tidak berubah, dipanggil oleh app.py] ...
    if not _model: return None
    
    prompt = f"""
    Buat LKPD INTERAKTIF untuk tema "{theme}" SMP/SMA.
    **OUTPUT HANYA JSON VALID** (tanpa markdown/kode):
    {{...}} 
    """ # Isi prompt di sini

    try:
        response = _model.generate_content(prompt)
        json_str = response.text.strip().replace("```json", "").replace("```", "").strip()
        data = json.loads(json_str)
        
        required_keys = ['judul', 'tujuan_pembelajaran', 'materi_singkat', 'kegiatan']
        if not all(key in data for key in required_keys):
            raise ValueError("Missing required keys in JSON")
        
        logger.info(f"✅ LKPD generated for theme: {theme}")
        return data
    except json.JSONDecodeError as e:
        st.error(f"❌ JSON Error - AI response tidak valid: {e}")
        logger.error(f"JSON decode error: {e}")
        return None
    except Exception as e:
        st.error(f"❌ AI Error: {str(e)}")
        logger.error(f"Generate error: {e}")
        return None

def score_jawaban(jawaban_text: str, pertanyaan: str) -> Dict[str, Any]:
    """AI Auto-Scoring for student answer"""
    if not _model:
        return {"score": 0, "feedback": "Model tidak tersedia"}
    
    prompt = f"""
    **NILAI JAWABAN SISWA** (skala 0-100) berdasarkan kriteria: Pemahaman konsep (40%), Kejelasan jawaban (30%), Contoh/referensi (20%), Bahasa (10%):
    
    Pertanyaan: "{pertanyaan}"
    Jawaban: "{jawaban_text}"
    
    **OUTPUT HANYA JSON VALID** (tanpa markdown/kode):
    {{
      "score": 85,
      "feedback": "Feedback positif + saran (50 kata max)",
      "strengths": ["Kelebihan 1", "Kelebihan 2"],
      "improvements": ["Perbaikan 1", "Perbaikan 2"]
    }}
    """
    try:
        response = _model.generate_content(prompt)
        json_str = response.text.strip().replace("```json", "").replace("```", "").strip()
        score_data = json.loads(json_str)
        
        # Validasi skor harus berupa integer/float
        score_value = int(score_data.get('score', 0))
        score_data['score'] = score_value
        
        logger.info(f"📊 Scored: {score_value}")
        return score_data
    except Exception as e:
        logger.error(f"Scoring error: {e}")
        return {
            "score": 0,
            "feedback": "Error dalam penilaian atau format JSON AI tidak valid.",
            "strengths": [],
            "improvements": ["Perlu perbaikan format output AI"]
        }

# ========== BULK SCORING (LOGIC UPDATE) ==========
def score_all_jawaban(lkpd_id: str) -> bool:
    """Score all student answers for LKPD and save the results."""
    all_jawaban = load_all_jawaban(lkpd_id)
    if not all_jawaban:
        logger.info(f"No answers found for scoring LKPD {lkpd_id}")
        return False

    success_count = 0
    
    for jawaban in all_jawaban:
        total_score_sum = 0
        num_questions = 0
        all_feedback = []
        all_strengths = []
        all_improvements = []
        
        for pertanyaan, answer_text in jawaban['jawaban'].items():
            if answer_text and answer_text.strip():
                score_result = score_jawaban(answer_text, pertanyaan)
                total_score_sum += score_result.get('score', 0)
                num_questions += 1
                
                all_feedback.append(score_result.get('feedback', ''))
                all_strengths.extend(score_result.get('strengths', []))
                all_improvements.extend(score_result.get('improvements', []))
        
        final_score = total_score_sum // num_questions if num_questions > 0 else 0
        
        # UPDATE DATA JAWABAN
        jawaban['total_score'] = final_score
        jawaban['feedback'] = " | ".join(filter(None, all_feedback))
        jawaban['strengths'] = list(set(all_strengths))[:3]
        jawaban['improvements'] = list(set(all_improvements))[:3]
        
        # SIMPAN ULANG FILE JAWABAN DENGAN SKOR TERBARU
        filename_to_update = jawaban.pop('filename', None) 
        if filename_to_update:
            filepath = os.path.join(JAWABAN_DIR, filename_to_update)
            try:
                # Ambil data yang sudah diupdate
                data_to_save = {k: v for k, v in jawaban.items() if k != 'filename'}
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(data_to_save, f, ensure_ascii=False, indent=2)
                logger.info(f"💾 Score saved for {jawaban['nama_siswa']}")
                success_count += 1
            except Exception as e:
                logger.error(f"Error saving score for {filename_to_update}: {e}")
                
    return success_count > 0

# ========== INITIALIZATION & GLOBAL ACCESSOR ==========
def initialize_app():
    ensure_directories()
    model = init_gemini()
    return model is not None

def get_model() -> Optional[genai.GenerativeModel]:
    global _model
    if _model is None:
        initialize_app()
    return _model

# Auto-init on import
initialize_app()
