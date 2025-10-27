import streamlit as st
import pandas as pd
import random
import json
from datetime import datetime
from pathlib import Path

# ==============================
# KONFIGURASI DASAR
# ==============================
st.set_page_config(page_title="EduAI LMS", layout="wide")
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

# ------------------------------
# SIMULASI FUNGSI AI GENERATOR
# ------------------------------
def generate_lkpd_ai(theme):
    """Membuat LKPD berbasis tema secara otomatis."""
    contoh_lkpd = {
        "tema": theme,
        "petunjuk": f"Kerjakan LKPD dengan tema '{theme}'. Jawablah dengan analisis kritis.",
        "soal": [
            {"pertanyaan": f"Jelaskan konsep utama terkait tema '{theme}'.", "kunci": "Konsep utama adalah ..."},
            {"pertanyaan": f"Berikan contoh kasus nyata yang relevan dengan '{theme}'.", "kunci": "Contohnya ..."},
            {"pertanyaan": f"Analisis solusi terhadap masalah dalam tema '{theme}'.", "kunci": "Solusi yang mungkin ..."}
        ]
    }
    return contoh_lkpd

def analisis_ai(jawaban_siswa, kunci):
    """AI semi-otomatis: menganalisis kualitas jawaban siswa."""
    skor = 0
    for i, (jawab, kunci_text) in enumerate(zip(jawaban_siswa, kunci)):
        if jawab.strip() == "":
            continue
        if any(word.lower() in jawab.lower() for word in kunci_text.split()[:3]):
            skor += 30
        else:
            skor += 20
    rekomendasi = "Bagus, lanjutkan." if skor >= 70 else "Perlu pendalaman konsep."
    return skor, rekomendasi

# ==============================
# MODUL GURU
# ==============================
def halaman_guru():
    st.title("👩‍🏫 Mode Guru - EduAI LMS")
    st.subheader("Buat LKPD Baru")
    tema = st.text_input("Masukkan tema LKPD:")
    
    if st.button("Generate LKPD Otomatis"):
        if not tema:
            st.warning("Masukkan tema terlebih dahulu.")
            return
        lkpd = generate_lkpd_ai(tema)
        lkpd_id = f"LKPD-{random.randint(1000, 9999)}"
        with open(DATA_DIR / f"{lkpd_id}.json", "w") as f:
            json.dump(lkpd, f)
        st.success(f"✅ LKPD berhasil dibuat! ID: {lkpd_id}")
        st.json(lkpd)

    st.divider()
    st.subheader("📊 Mode Pemantauan Siswa")
    files = list(DATA_DIR.glob("*.csv"))
    if not files:
        st.info("Belum ada hasil siswa yang dikirim.")
        return

    for file in files:
        df = pd.read_csv(file)
        st.markdown(f"### 🧾 Hasil dari {file.stem}")
        st.dataframe(df)

        # Analisis Semi-Otomatis
        if st.button(f"Analisis Jawaban {file.stem}"):
            jawaban = df["jawaban"].tolist()
            lkpd_file = DATA_DIR / f"{df['lkpd_id'][0]}.json"
            if lkpd_file.exists():
                with open(lkpd_file, "r") as f:
                    kunci = [q["kunci"] for q in json.load(f)["soal"]]
                skor, rekom = analisis_ai(jawaban, kunci)
                st.success(f"💯 Rekomendasi Nilai: {skor}/100 — {rekom}")
            else:
                st.warning("Kunci jawaban tidak ditemukan.")

# ==============================
# MODUL SISWA
# ==============================
def halaman_siswa():
    st.title("🎓 Mode Siswa - EduAI LMS")
    lkpd_id = st.text_input("Masukkan ID LKPD:")
    
    if st.button("Muat LKPD"):
        file_path = DATA_DIR / f"{lkpd_id}.json"
        if not file_path.exists():
            st.error("❌ LKPD tidak ditemukan.")
            return
        with open(file_path, "r") as f:
            lkpd = json.load(f)
        
        st.success(f"LKPD '{lkpd['tema']}' berhasil dimuat.")
        st.markdown(f"**Petunjuk:** {lkpd['petunjuk']}")
        st.divider()

        # Tampilkan soal dalam card (Modern View)
        st.markdown("### ✍️ Jawab Soal Berikut")
        jawaban = []
        for i, soal in enumerate(lkpd["soal"], 1):
            with st.container(border=True):
                st.markdown(f"#### 🧩 Soal {i}")
                st.write(soal["pertanyaan"])
                jwb = st.text_area(f"Jawaban Anda untuk Soal {i}", key=f"soal_{i}")
                jawaban.append(jwb)

        nama = st.text_input("Nama Anda:")
        if st.button("Kirim Jawaban"):
            if not nama or not any(jawaban):
                st.warning("Isi semua jawaban dan nama sebelum mengirim.")
                return
            df = pd.DataFrame({
                "nama": [nama]*len(jawaban),
                "lkpd_id": [lkpd_id]*len(jawaban),
                "soal_no": list(range(1, len(jawaban)+1)),
                "jawaban": jawaban,
                "tanggal": [datetime.now().strftime("%Y-%m-%d %H:%M:%S")]*len(jawaban)
            })
            file_path = DATA_DIR / f"hasil_{nama}_{lkpd_id}.csv"
            df.to_csv(file_path, index=False)
            st.success("✅ Jawaban berhasil dikirim ke guru.")
            st.balloons()

# ==============================
# MAIN APP
# ==============================
def main():
    st.sidebar.title("📚 EduAI LMS")
    mode = st.sidebar.radio("Pilih Mode:", ["Guru", "Siswa"])

    if mode == "Guru":
        halaman_guru()
    elif mode == "Siswa":
        halaman_siswa()

# Jalankan dengan proteksi
if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        st.error(f"⚠️ Terjadi error di aplikasi: {e}")
