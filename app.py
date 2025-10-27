import streamlit as st
import uuid
import json
import os
import re
from gemini_config import (
    init_model, list_available_models, generate_lkpd,
    save_json, load_json, LKPD_DIR, ANSWERS_DIR
)

# ---------------------------------------------------------
# Utility & Setup
# ---------------------------------------------------------
st.set_page_config(page_title="EduAI LKPD Modern", layout="wide", page_icon="🎓")

def sanitize_id(s: str) -> str:
    return re.sub(r"[^\w\-]", "_", s.strip())[:64]

os.makedirs(LKPD_DIR, exist_ok=True)
os.makedirs(ANSWERS_DIR, exist_ok=True)

def card(title: str, content: str, color="#f9fafb"):
    """Card-style block with light accent background."""
    st.markdown(
        f"""
        <div style='background:{color};padding:12px 18px;border-radius:10px;
        box-shadow:0 1px 3px rgba(0,0,0,0.1);margin-bottom:10px;'>
        <div style='font-weight:600;font-size:17px;margin-bottom:6px;'>{title}</div>
        <div style='font-size:14px;line-height:1.5;'>{content}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------
# Init model
# ---------------------------------------------------------
st.title("EduAI — LKPD Modern Viewer")
st.caption("AI hanya membuat LKPD, bukan jawaban siswa. Tampilan diperindah agar UX siswa lebih baik.")

api_key = st.secrets.get("GEMINI_API_KEY") if "GEMINI_API_KEY" in st.secrets else None
ok, msg, debug = init_model(api_key)
if not ok:
    st.error(f"Gemini init failed: {msg}")
    st.info("Tambahkan GEMINI_API_KEY di Secrets → Manage App.")
    st.stop()
else:
    st.success(msg)

# ---------------------------------------------------------
# Sidebar
# ---------------------------------------------------------
st.sidebar.header("Navigasi")
role = st.sidebar.radio("Pilih Peran:", ["👨🏫 Guru", "👩🎓 Siswa"])
st.sidebar.divider()
if st.sidebar.button("🔎 Tes koneksi (list models)"):
    info = list_available_models()
    if info.get("ok"):
        st.sidebar.success(f"{info['count']} models ditemukan")
    else:
        st.sidebar.error(info.get("error"))

# ---------------------------------------------------------
# Mode Guru
# ---------------------------------------------------------
if role == "👨🏫 Guru":
    st.header("👨🏫 Mode Guru — Buat & Pantau LKPD")

    tab_create, tab_monitor = st.tabs(["✏️ Buat LKPD", "📊 Pantau Jawaban"])

    # ---- BUAT LKPD ----
    with tab_create:
        st.subheader("Buat LKPD (dengan bantuan AI)")
        tema = st.text_input("Tema / Topik pembelajaran:")
        if st.button("Generate LKPD (AI)"):
            if not tema.strip():
                st.warning("Masukkan tema terlebih dahulu.")
            else:
                with st.spinner("Menghasilkan LKPD..."):
                    data, dbg = generate_lkpd(tema, max_retry=1)
                    if data:
                        lkpd_id = str(uuid.uuid4())[:8]
                        save_json(LKPD_DIR, lkpd_id, data)
                        st.success(f"✅ LKPD berhasil dibuat (ID: {lkpd_id})")
                        st.json(data)
                        st.download_button(
                            "📥 Unduh LKPD (JSON)",
                            json.dumps(data, ensure_ascii=False, indent=2),
                            file_name=f"LKPD_{lkpd_id}.json"
                        )
                    else:
                        st.error("Gagal membuat LKPD.")
                        st.json(dbg)

    # ---- PANTAU JAWABAN ----
    with tab_monitor:
        st.subheader("Pantau Jawaban Siswa")
        lkpd_id = st.text_input("Masukkan ID LKPD yang ingin dipantau:")
        if lkpd_id:
            lkpd = load_json(LKPD_DIR, lkpd_id)
            if not lkpd:
                st.error("LKPD tidak ditemukan.")
            else:
                st.success(f"LKPD: {lkpd.get('judul','Tanpa judul')}")
                answers = load_json(ANSWERS_DIR, lkpd_id) or {}
                if not answers:
                    st.info("Belum ada jawaban siswa.")
                else:
                    for nama, record in answers.items():
                        st.markdown(f"### 🧑‍🎓 {nama}")
                        for idx, q in enumerate(record.get("jawaban", []), 1):
                            st.markdown(f"**{idx}. {q.get('pertanyaan')}**")
                            st.write(q.get("jawaban"))
                            # contoh jawaban AI hanya ditampilkan di mode guru:
                            corrects = lkpd.get("jawaban_benar", [])
                            if idx <= len(corrects):
                                st.info(f"💡 Contoh jawaban (AI): {corrects[idx-1]}")
                            st.number_input(
                                f"Nilai {nama} - Pertanyaan {idx}",
                                0, 100, 0, key=f"{nama}_{lkpd_id}_{idx}"
                            )
                        st.divider()

# ---------------------------------------------------------
# Mode Siswa
# ---------------------------------------------------------
else:
    st.header("👩🎓 Mode Siswa — Kerjakan LKPD")
    lkpd_id = st.text_input("Masukkan ID LKPD yang diberikan guru:")
    nama = st.text_input("Nama lengkap:")
    if lkpd_id and nama:
        lkpd = load_json(LKPD_DIR, lkpd_id)
        if not lkpd:
            st.error("LKPD tidak ditemukan.")
        else:
            st.success(f"LKPD: {lkpd.get('judul','Tanpa judul')}")
            card("🎯 Tujuan Pembelajaran", "<br>".join(lkpd.get("tujuan_pembelajaran", [])), "#eef2ff")
            card("📚 Materi Singkat", lkpd.get("materi_singkat","(Belum ada materi)"), "#f0fdf4")

            jawaban_list = []
            for i, kegiatan in enumerate(lkpd.get("kegiatan", []), 1):
                with st.expander(f"Kegiatan {i}: {kegiatan.get('nama','')}"):
                    st.write(kegiatan.get("petunjuk",""))
                    for j, q in enumerate(kegiatan.get("pertanyaan_pemantik", []), 1):
                        ans = st.text_area(
                            f"{i}.{j} {q.get('pertanyaan')}",
                            key=f"{lkpd_id}_{nama}_{i}_{j}", height=120
                        )
                        jawaban_list.append({"pertanyaan": q.get("pertanyaan"), "jawaban": ans})

            if st.button("📤 Submit Jawaban"):
                existing = load_json(ANSWERS_DIR, lkpd_id) or {}
                existing[nama] = {
                    "jawaban": jawaban_list,
                    "submitted_at": str(__import__("datetime").datetime.now())
                }
                save_json(ANSWERS_DIR, lkpd_id, existing)
                st.success("Jawaban terkirim! Guru akan menilai dari sistem.")
                st.download_button(
                    "📥 Unduh salinan jawaban",
                    json.dumps(jawaban_list, ensure_ascii=False, indent=2),
                    file_name=f"jawaban_{lkpd_id}_{nama}.json"
                )
    else:
        st.info("Masukkan ID LKPD dan nama untuk mulai mengerjakan.")
