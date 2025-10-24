import streamlit as st
import uuid
import json
import os
from gemini_config import (
    init_model, list_available_models, generate_lkpd,
    save_json, load_json, LKPD_DIR, ANSWERS_DIR
)

st.set_page_config(page_title="EduAI LKPD Debuggable", layout="wide", page_icon="🎓")

st.title("EduAI — Generator LKPD (Debuggable)")
st.caption("Alur: Guru create LKPD (AI) → Siswa kerjakan & submit → Guru pantau; AI hanya membuat LKPD dan contoh jawaban.")

# ---------------- init model ----------------
api_key = st.secrets.get("GEMINI_API_KEY") if "GEMINI_API_KEY" in st.secrets else None
ok, msg, debug_init = init_model(api_key)
if not ok:
    st.error(f"Gemini init failed: {msg}")
    # show debug hint
    st.info("Pastikan Anda menambahkan GEMINI_API_KEY di Streamlit Secrets (Manage App → Secrets).")
    st.stop()
else:
    st.success(msg)
    # show small debug (collapsible)
    with st.expander("🔍 Debug init (model list info)"):
        st.write(debug_init)

# ---------------- sidebar: tes koneksi ----------------
st.sidebar.header("🔧 Diagnostic")
if st.sidebar.button("🔎 Tes koneksi - list available models"):
    info = list_available_models()
    if info.get("ok"):
        st.sidebar.success(f"{info.get('count')} models available")
        st.sidebar.write(info.get("names")[:50])
    else:
        st.sidebar.error(f"List models failed: {info.get('error')}")

# ensure folders exist
os.makedirs(LKPD_DIR, exist_ok=True)
os.makedirs(ANSWERS_DIR, exist_ok=True)

# ---------------- mode selection ----------------
role = st.sidebar.radio("Pilih Peran:", ["👨🏫 Guru", "👩🎓 Siswa"])

# ---------------- GURU ----------------
if role == "👨🏫 Guru":
    st.header("👨🏫 Mode Guru — Buat & Pantau LKPD")
    tab1, tab2 = st.tabs(["✏️ Buat LKPD", "📊 Pemantauan Jawaban"])

    with tab1:
        st.subheader("Buat LKPD (AI)")
        theme = st.text_input("Tema / Topik:")
        if st.button("Generate LKPD (AI)"):
            if not theme.strip():
                st.warning("Isi tema dahulu.")
            else:
                with st.spinner("Menghubungi AI..."):
                    data, dbg = generate_lkpd(theme, max_retry=1)
                    if data:
                        lkpd_id = str(uuid.uuid4())[:8]
                        save_json(LKPD_DIR, lkpd_id, data)
                        st.success(f"LKPD dibuat (ID: {lkpd_id})")
                        st.json(data)
                        st.markdown("---")
                        st.download_button("Unduh LKPD (json)", json.dumps(data, ensure_ascii=False, indent=2), file_name=f"LKPD_{lkpd_id}.json")
                    else:
                        st.error("Gagal membuat LKPD. Lihat debug untuk detail.")
                        st.write("Debug info:")
                        st.json(dbg)

    with tab2:
        st.subheader("Pemantauan Jawaban Siswa")
        lkpd_id = st.text_input("Masukkan ID LKPD untuk pantau:")
        if lkpd_id:
            lkpd = load_json(LKPD_DIR, lkpd_id)
            if not lkpd:
                st.error("LKPD tidak ditemukan.")
            else:
                st.success(f"Memantau: {lkpd.get('judul','')}")
                answers = load_json(ANSWERS_DIR, lkpd_id) or {}
                if not answers:
                    st.info("Belum ada jawaban siswa.")
                else:
                    for student, record in answers.items():
                        st.markdown(f"### 🧑‍🎓 {student}")
                        for idx, q in enumerate(record.get("jawaban", []), 1):
                            st.write(f"**Pertanyaan {idx}:** {q.get('pertanyaan')}")
                            st.write(f"**Jawaban Siswa:** {q.get('jawaban')}")
                            # show AI example answer if present in LKPD
                            corrects = lkpd.get("jawaban_benar", [])
                            if idx <= len(corrects):
                                st.info(f"Contoh jawaban (AI): {corrects[idx-1]}")
                            # input for manual scoring
                            score = st.number_input(f"Nilai {student} - Pertanyaan {idx}", 0, 100, 0, key=f"{student}_{lkpd_id}_{idx}")
                            note = st.text_area(f"Catatan untuk {student} - Pertanyaan {idx}", key=f"note_{student}_{lkpd_id}_{idx}", height=80)
                        st.markdown("---")

# ---------------- SISWA ----------------
else:
    st.header("👩🎓 Mode Siswa — Kerjakan LKPD")
    lkpd_id = st.text_input("Masukkan ID LKPD yang diberikan guru:")
    nama = st.text_input("Nama lengkap:")
    if lkpd_id and nama:
        lkpd = load_json(LKPD_DIR, lkpd_id)
        if not lkpd:
            st.error("LKPD tidak ditemukan (periksa ID).")
        else:
            st.success(f"LKPD: {lkpd.get('judul','')}")
            st.write(lkpd.get("materi_singkat",""))
            jawaban_list = []
            for i, keg in enumerate(lkpd.get("kegiatan", []), 1):
                with st.expander(f"Kegiatan {i}: {keg.get('nama','')}"):
                    st.write(keg.get("petunjuk",""))
                    for j, q in enumerate(keg.get("pertanyaan_pemantik", []), 1):
                        ans = st.text_area(f"{i}.{j} {q.get('pertanyaan')}", key=f"{lkpd_id}_{nama}_{i}_{j}", height=120)
                        jawaban_list.append({"pertanyaan": q.get("pertanyaan"), "jawaban": ans})
            if st.button("Submit Jawaban"):
                # load existing answers for this LKPD (dict student->record)
                existing = load_json(ANSWERS_DIR, lkpd_id) or {}
                existing[nama] = {"jawaban": jawaban_list, "submitted_at": str(__import__("datetime").datetime.now())}
                save_json(ANSWERS_DIR, lkpd_id, existing)
                st.success("Jawaban terkirim — guru dapat memantau di mode Pemantauan.")
                st.download_button("Download salinan jawaban (untuk arsip)", json.dumps(jawaban_list, ensure_ascii=False, indent=2), file_name=f"jawaban_{lkpd_id}_{nama}.json")
    else:
        st.info("Masukkan ID LKPD dan Nama untuk mulai mengerjakan.")
