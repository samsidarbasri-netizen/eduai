import streamlit as st
import uuid
import json
import os
from gemini_config import init_model, get_model, generate_lkpd

st.set_page_config(page_title="EduAI LKPD Simplified", layout="wide", page_icon="🎓")

# Inisialisasi model Gemini
api_key = st.secrets.get("GEMINI_API_KEY") if "GEMINI_API_KEY" in st.secrets else None
ok, msg = init_model(api_key)
if not ok:
    st.error(msg)
    st.stop()

# Folder penyimpanan lokal
LKPD_DIR = "lkpd_data"
os.makedirs(LKPD_DIR, exist_ok=True)

# Sidebar: pilih peran
role = st.sidebar.radio("Pilih Mode:", ["👩‍🏫 Guru", "👨‍🎓 Siswa"])

# -------------------------------
# MODE GURU
# -------------------------------
if role == "👩‍🏫 Guru":
    st.header("👩‍🏫 Mode Guru - Pembuatan & Pemantauan LKPD")

    st.subheader("1️⃣ Buat LKPD Otomatis")
    theme = st.text_input("Masukkan Tema Pembelajaran:")

    if st.button("🚀 Buat LKPD"):
        if not theme.strip():
            st.warning("Masukkan tema terlebih dahulu.")
        else:
            with st.spinner("Sedang menghasilkan LKPD..."):
                lkpd_data = generate_lkpd(theme)
                if lkpd_data:
                    lkpd_id = str(uuid.uuid4())[:8]
                    path = os.path.join(LKPD_DIR, f"{lkpd_id}.json")
                    with open(path, "w", encoding="utf-8") as f:
                        json.dump(lkpd_data, f, indent=2, ensure_ascii=False)
                    st.success(f"✅ LKPD berhasil dibuat (ID: {lkpd_id})")
                    st.json(lkpd_data)
                else:
                    st.error("Gagal membuat LKPD. Coba lagi nanti.")

    st.markdown("---")
    st.subheader("2️⃣ Tambahkan Contoh Jawaban Benar")

    lkpd_files = [f for f in os.listdir(LKPD_DIR) if f.endswith(".json")]
    if lkpd_files:
        chosen = st.selectbox("Pilih LKPD untuk menambahkan contoh jawaban:", lkpd_files)
        path = os.path.join(LKPD_DIR, chosen)
        data = json.load(open(path, encoding="utf-8"))

        for i, q in enumerate(data.get("pertanyaan", []), start=1):
            key = f"answer_{i}"
            q["jawaban_benar"] = st.text_area(f"✅ Contoh jawaban untuk '{q['soal']}'", key=key, height=100)

        if st.button("💾 Simpan Jawaban Contoh"):
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            st.success("Contoh jawaban berhasil disimpan.")
    else:
        st.info("Belum ada LKPD yang dibuat.")

    st.markdown("---")
    st.subheader("3️⃣ Lihat Jawaban Siswa")
    uploaded = st.file_uploader("Unggah file jawaban siswa (.json):", type=["json"])
    if uploaded:
        answers = json.load(uploaded)
        st.write("📋 Jawaban siswa yang dikirim:")
        for ans in answers:
            st.markdown(f"**Siswa:** {ans['nama']} — **Soal:** {ans['soal']}")
            st.write(f"📝 Jawaban Siswa: {ans['jawaban']}")
            st.write(f"✅ Contoh Jawaban Benar: {ans.get('jawaban_benar','(belum ada)')}")
            st.markdown("---")

# -------------------------------
# MODE SISWA
# -------------------------------
else:
    st.header("👨‍🎓 Mode Siswa - Isi LKPD")

    lkpd_id = st.text_input("Masukkan ID LKPD yang diberikan guru:")
    if lkpd_id:
        path = os.path.join(LKPD_DIR, f"{lkpd_id}.json")
        if os.path.exists(path):
            data = json.load(open(path, encoding="utf-8"))
            st.success(f"LKPD '{data.get('judul','')}' dimuat.")
            st.write(data.get("materi_singkat",""))

            jawaban_siswa = []
            nama = st.text_input("Nama Siswa:")

            for q in data.get("pertanyaan", []):
                ans = st.text_area(f"{q['soal']}", height=100)
                jawaban_siswa.append({
                    "nama": nama,
                    "soal": q["soal"],
                    "jawaban": ans,
                    "jawaban_benar": q.get("jawaban_benar", "")
                })

            if st.button("📤 Kirim Jawaban"):
                if not nama.strip():
                    st.warning("Masukkan nama terlebih dahulu.")
                else:
                    fname = f"jawaban_{nama.replace(' ','_')}.json"
                    with open(fname, "w", encoding="utf-8") as f:
                        json.dump(jawaban_siswa, f, indent=2, ensure_ascii=False)
                    st.download_button("📥 Unduh File Jawaban (kirim ke guru)", data=open(fname, "r", encoding="utf-8").read(), file_name=fname)
                    st.success("Jawaban disiapkan untuk dikirim ke guru.")
        else:
            st.error("LKPD dengan ID tersebut tidak ditemukan.")
    else:
        st.info("Masukkan ID LKPD dari guru untuk memulai.")
