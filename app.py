import streamlit as st
import uuid
import json
import os
import re
from typing import List, Dict, Any

# Import utilities from gemini_config (keamanan: gemini_config tidak memanggil streamlit)
from gemini_config import (
    init_model,
    list_available_models,
    generate_lkpd,
    save_json,
    load_json,
    LKPD_DIR,
    ANSWERS_DIR,
)

# --------------------------
# Helper utilities
# --------------------------
def sanitize_id(s: str) -> str:
    """Sanitize a string to be used in filenames/keys."""
    return re.sub(r"[^\w\-]", "_", s.strip())[:64]

def ensure_folders():
    os.makedirs(LKPD_DIR, exist_ok=True)
    os.makedirs(ANSWERS_DIR, exist_ok=True)

def pretty_markdown_card(title: str, body_md: str, accent: str = "#f3f4f6"):
    """Render a simple card using inline HTML/CSS (safe, minimal)."""
    st.markdown(
        f"""
        <div style="background:{accent}; padding:14px; border-radius:10px; box-shadow: 0 1px 3px rgb(16 24 40 / 8%); margin-bottom:10px;">
          <div style="font-weight:700; font-size:18px; margin-bottom:6px;">{title}</div>
          <div style="color:#111827; font-size:14px; line-height:1.45;">{body_md}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

def display_lkpd_cards(lkpd: Dict[str, Any]):
    """Modern card-based view for a LKPD dict."""
    # header card
    title = lkpd.get("judul", "LKPD Tanpa Judul")
    tujuan = lkpd.get("tujuan_pembelajaran", [])
    materi = lkpd.get("materi_singkat", "")
    jawaban_benar = lkpd.get("jawaban_benar", [])

    # Title
    st.markdown(f"## 📘 {title}")
    # Info row
    col1, col2 = st.columns([3, 1])
    with col1:
        if tujuan:
            tujuan_md = "\n".join([f"- {t}" for t in tujuan])
        else:
            tujuan_md = "Tidak ada tujuan pembelajaran tercantum."
        pretty_markdown_card("🎯 Tujuan Pembelajaran", tujuan_md, accent="#eef2ff")
    with col2:
        st.write("")  # spacing
        st.metric(label="Jumlah Kegiatan", value=len(lkpd.get("kegiatan", [])))

    # Materi singkat
    pretty_markdown_card("📚 Materi Singkat", materi or "Tidak ada materi singkat.")

    # Activities as cards in grid
    st.markdown("### 🔎 Kegiatan")
    kegiatan = lkpd.get("kegiatan", [])
    if not kegiatan:
        st.info("Belum ada kegiatan yang tersedia di LKPD ini.")
        return

    # For visual variety: alternate colors
    colors = ["#ffffff", "#fff7ed", "#f0fdf4", "#eef2ff"]

    for i, keg in enumerate(kegiatan, start=1):
        color = colors[i % len(colors)]
        name = keg.get("nama", f"Kegiatan {i}")
        petunjuk = keg.get("petunjuk", "")
        tugas = keg.get("tugas_interaktif", [])
        pertanyaan = keg.get("pertanyaan_pemantik", [])

        # Card header with columns
        st.markdown(
            f"""
            <div style="display:flex; gap:12px; align-items:center; margin-top:12px;">
              <div style="width:44px; height:44px; border-radius:12px; background:#111827; color:white; display:flex; align-items:center; justify-content:center; font-weight:700;">{i}</div>
              <div style="flex:1">
                <div style="font-size:16px; font-weight:700;">{name}</div>
                <div style="color:#374151; margin-top:6px;">{petunjuk}</div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        # Tugas list
        if tugas:
            t_md = "\n".join([f"- {t}" for t in tugas])
            pretty_markdown_card("📝 Tugas Interaktif", t_md, accent=color)
        # Pertanyaan (expandable)
        for qi, qobj in enumerate(pertanyaan, start=1):
            q_text = qobj.get("pertanyaan", "")
            # show as expander with example answer if available
            with st.expander(f"Pertanyaan {i}.{qi}: {q_text}"):
                # If LKPD contains jawaban_benar array, show corresponding example
                if qi - 1 < len(jawaban_benar):
                    st.success(f"Contoh Jawaban (AI): {jawaban_benar[qi-1]}")
                st.text("Tempat siswa menulis jawaban (ditampilkan di mode Siswa).")

# --------------------------
# App start
# --------------------------
st.set_page_config(page_title="EduAI LKPD — Modern Viewer", layout="wide", page_icon="🎓")
st.title("EduAI — LKPD Modern Viewer")
st.caption("UI diperbarui: tampilan LKPD pakai kartu & warna agar lebih menarik untuk siswa dan guru.")

# Initialize model and folders
api_key = st.secrets.get("GEMINI_API_KEY") if "GEMINI_API_KEY" in st.secrets else None
ok, msg, debug_init = init_model(api_key)
if not ok:
    st.error(f"Gemini init failed: {msg}")
    st.info("Pastikan GEMINI_API_KEY ditambahkan di Manage App → Secrets.")
    # still allow making LKPD disabled if model missing
    has_model = False
else:
    has_model = True
    st.success(msg)
    with st.expander("🔍 Info model (debug)"):
        st.write(debug_init)

ensure_folders()

# Sidebar controls
st.sidebar.header("Navigasi")
role = st.sidebar.radio("Mode:", ["👨🏫 Guru", "👩🎓 Siswa"])
st.sidebar.markdown("---")
st.sidebar.caption("EduAI — modern LKPD viewer")

# Diagnostic (optional)
if st.sidebar.button("🔎 Tes koneksi - list models"):
    info = list_available_models()
    if info.get("ok"):
        st.sidebar.success(f"{info.get('count')} models found")
        st.sidebar.write(info.get("names")[:50])
    else:
        st.sidebar.error(f"List models error: {info.get('error')}")

# --------------------------
# GURU Mode
# --------------------------
if role == "👨🏫 Guru":
    st.header("👨🏫 Mode Guru — Buat & Pantau LKPD (Modern Viewer)")
    tab_create, tab_monitor = st.tabs(["✏️ Buat LKPD", "📊 Pemantauan Jawaban"])

    with tab_create:
        st.subheader("Buat LKPD (AI)")
        theme = st.text_input("Tema / Topik pembelajaran:")
        btn_gen = st.button("Generate LKPD (AI)", key="gen_lkpd")
        if btn_gen:
            if not theme.strip():
                st.warning("Isi tema terlebih dahulu.")
            elif not has_model:
                st.error("Model AI belum aktif. Periksa GEMINI_API_KEY.")
            else:
                with st.spinner("Menghasilkan LKPD..."):
                    data, dbg = generate_lkpd(theme, max_retry=1)
                    if data:
                        lkpd_id = sanitize_id(str(uuid.uuid4())[:8])
                        save_json(LKPD_DIR, lkpd_id, data)
                        st.success(f"✅ LKPD dibuat (ID: {lkpd_id})")
                        # display in modern card style
                        display_lkpd_cards(data)
                        st.markdown("---")
                        st.download_button(
                            "📥 Unduh LKPD (JSON)",
                            json.dumps(data, ensure_ascii=False, indent=2),
                            file_name=f"LKPD_{lkpd_id}.json",
                        )
                    else:
                        st.error("Gagal membuat LKPD. Lihat debug objek di bawah.")
                        st.write(dbg)

    with tab_monitor:
        st.subheader("Pemantauan Jawaban Siswa (Modern View)")
        lkpd_id = st.text_input("Masukkan ID LKPD yang ingin dipantau:")
        if lkpd_id:
            lkpd_id_s = sanitize_id(lkpd_id)
            lkpd = load_json(LKPD_DIR, lkpd_id_s)
            if not lkpd:
                st.error("LKPD tidak ditemukan. Periksa ID atau pastikan sudah dibuat.")
            else:
                # show LKPD preview in modern style
                st.markdown("#### Pratinjau LKPD")
                display_lkpd_cards(lkpd)
                st.markdown("---")
                st.subheader("Daftar Jawaban Siswa")
                answers = load_json(ANSWERS_DIR, lkpd_id_s) or {}
                if not answers:
                    st.info("Belum ada jawaban siswa untuk LKPD ini.")
                else:
                    for student, rec in answers.items():
                        st.markdown(f"### 🧑‍🎓 {student}")
                        cols = st.columns([3, 1])
                        with cols[0]:
                            for idx, q in enumerate(rec.get("jawaban", []), start=1):
                                st.markdown(f"**{idx}. {q.get('pertanyaan')}**")
                                st.write(q.get("jawaban"))
                                # show AI sample answer if exists
                                sample = lkpd.get("jawaban_benar", [])
                                if idx <= len(sample):
                                    st.info(f"Contoh jawaban (AI): {sample[idx-1]}")
                        with cols[1]:
                            st.markdown("**Penilaian Guru**")
                            # compact scoring inputs
                            for idx, q in enumerate(rec.get("jawaban", []), start=1):
                                key_score = f"score_{lkpd_id_s}_{student}_{idx}"
                                key_note = f"note_{lkpd_id_s}_{student}_{idx}"
                                score = st.number_input(f"P{idx}", 0, 100, 0, key=key_score)
                                note = st.text_area("Catatan", key=key_note, height=80)
                            if st.button(f"Simpan Nilai untuk {student}", key=f"save_{lkpd_id_s}_{student}"):
                                st.success(f"Nilai untuk {student} disimpan (sementara di session).")
                                # store in session
                                if "grades" not in st.session_state:
                                    st.session_state["grades"] = {}
                                st.session_state["grades"].setdefault(lkpd_id_s, {})
                                st.session_state["grades"][lkpd_id_s][student] = {
                                    "scores": {k: st.session_state.get(f"score_{lkpd_id_s}_{student}_{i+1}", 0)
                                               for i in range(len(rec.get("jawaban", [])))},
                                    "notes": {k: st.session_state.get(f"note_{lkpd_id_s}_{student}_{i+1}", "")
                                              for i in range(len(rec.get("jawaban", [])))},
                                }

# --------------------------
# SISWA Mode
# --------------------------
else:
    st.header("👩🎓 Mode Siswa — Kerjakan LKPD (Tampilan Modern)")
    st.subheader("Masukkan ID LKPD yang diberikan guru")
    lkpd_id = st.text_input("ID LKPD:")
    nama = st.text_input("Nama lengkap:")

    if lkpd_id and nama:
        lkpd_id_s = sanitize_id(lkpd_id)
        lkpd = load_json(LKPD_DIR, lkpd_id_s)
        if not lkpd:
            st.error("LKPD tidak ditemukan. Pastikan ID benar.")
        else:
            st.success(f"LKPD: {lkpd.get('judul','(tanpa judul)')}")
            # show modern preview (teacher view is richer)
            display_lkpd_cards(lkpd)
            st.markdown("---")
            st.subheader("Form Jawaban — Isi di bawah setiap pertanyaan")
            jawaban_list = []
            for i, keg in enumerate(lkpd.get("kegiatan", []), start=1):
                with st.expander(f"Kegiatan {i}: {keg.get('nama','')}"):
                    st.write(keg.get("petunjuk",""))
                    for j, q in enumerate(keg.get("pertanyaan_pemantik", []), start=1):
                        key = f"ans_{lkpd_id_s}_{nama}_{i}_{j}"
                        t = st.text_area(q.get("pertanyaan", ""), key=key, height=140)
                        jawaban_list.append({"pertanyaan": q.get("pertanyaan"), "jawaban": t})
            if st.button("📤 Submit Jawaban"):
                if not nama.strip():
                    st.warning("Isi nama lengkap terlebih dahulu.")
                else:
                    existing = load_json(ANSWERS_DIR, lkpd_id_s) or {}
                    existing[nama] = {"jawaban": jawaban_list, "submitted_at": str(__import__("datetime").datetime.now())}
                    save_json(ANSWERS_DIR, lkpd_id_s, existing)
                    st.success("Jawaban berhasil dikirim — terima kasih!")
                    st.download_button(
                        "📥 Unduh salinan jawaban (arsip)",
                        json.dumps(jawaban_list, ensure_ascii=False, indent=2),
                        file_name=f"jawaban_{lkpd_id_s}_{sanitize_id(nama)}.json",
                    )
    else:
        st.info("Masukkan ID LKPD dan nama untuk mulai mengerjakan.")

# Footer / CTA
st.markdown("---")
st.caption("EduAI — Modern LKPD Viewer · Versi upgrade UI. Besok kita rampungkan fitur rekap & stabilitas I/O.")
