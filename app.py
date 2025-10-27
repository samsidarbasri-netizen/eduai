import streamlit as st
import uuid
import json
import os
import re
import pandas as pd
from gemini_config import (
    init_model, list_available_models, generate_lkpd,
    analyze_answer_with_ai, save_json, load_json, LKPD_DIR, ANSWERS_DIR
)

# ------------------ Setup ------------------
st.set_page_config(page_title="EduAI LKPD Modern", layout="wide", page_icon="🎓")

def sanitize_id(s: str) -> str:
    return re.sub(r"[^\w-]", "_", s.strip())[:64]

os.makedirs(LKPD_DIR, exist_ok=True)
os.makedirs(ANSWERS_DIR, exist_ok=True)

def card(title: str, content: str, color: str = "#f9fafb"):
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

# ------------------ Init Model ------------------
st.title("EduAI — LKPD Pembelajaran Mendalam")
st.caption("AI membantu membuat LKPD konseptual dan menganalisis pemahaman siswa secara semi-otomatis.")

api_key = st.secrets.get("GEMINI_API_KEY") if "GEMINI_API_KEY" in st.secrets else st.text_input("🔑 Masukkan API Key Gemini")
ok, msg, debug = init_model(api_key)
if not ok:
    st.error(msg)
    st.stop()
else:
    st.success(msg)

# ------------------ Sidebar ------------------
st.sidebar.header("Navigasi")
role = st.sidebar.radio("Pilih Peran", ["👨🏫 Guru", "👩🎓 Siswa"])
st.sidebar.divider()
if st.sidebar.button("🔎 Tes koneksi (list models)"):
    info = list_available_models()
    if info.get("ok"):
        st.sidebar.success(f"{info['count']} model ditemukan.")
    else:
        st.sidebar.error(info.get("error", "Gagal memeriksa model."))

# =========================================================
# MODE GURU
# =========================================================
if role == "👨🏫 Guru":
    st.header("👨🏫 Mode Guru — Buat & Pantau LKPD")
    tab_create, tab_monitor = st.tabs(["✏️ Buat LKPD", "📊 Pantau Jawaban"])

    # ---------- BUAT LKPD ----------
    with tab_create:
        tema = st.text_input("Tema / Topik Pembelajaran")
        if st.button("Generate LKPD (AI)"):
            if not tema.strip():
                st.warning("Masukkan tema terlebih dahulu.")
            else:
                with st.spinner("Menghasilkan LKPD (format pembelajaran mendalam)..."):
                    data, dbg = generate_lkpd(tema)
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

    # ---------- PANTAU JAWABAN ----------
    with tab_monitor:
        st.subheader("Pantau Jawaban Siswa")
        lkpd_id = st.text_input("Masukkan ID LKPD yang ingin dipantau")

        if lkpd_id:
            lkpd = load_json(LKPD_DIR, lkpd_id)
            if not lkpd:
                st.error("LKPD tidak ditemukan.")
            else:
                answers = load_json(ANSWERS_DIR, lkpd_id) or {}
                if not answers:
                    st.info("Belum ada jawaban siswa.")
                else:
                    # 🔘 Pilihan Mode Penilaian
                    mode_penilaian = st.radio(
                        "Pilih Metode Penilaian",
                        ["💡 Penilaian Otomatis (AI)", "✍️ Penilaian Manual (Guru)"],
                        horizontal=True
                    )

                    rekap = []
                    for nama, record in answers.items():
                        st.markdown(f"### 🧑🎓 {nama}")
                        total_score = 0
                        count = 0

                        for idx, q in enumerate(record.get("jawaban", []), 1):
                            st.markdown(f"{idx}. **{q.get('pertanyaan')}**")
                            st.write(q.get("jawaban") or "_(tidak ada jawaban)_")

                            # === MODE PENILAIAN AI ===
                            if mode_penilaian == "💡 Penilaian Otomatis (AI)":
                                ai_eval = analyze_answer_with_ai(q.get("jawaban"))
                                score = ai_eval.get("score", 0)
                                fb = ai_eval.get("feedback", "")
                                st.info(f"💬 Feedback AI: {fb} (Skor: {score})")

                            # === MODE PENILAIAN MANUAL ===
                            else:
                                score = st.number_input(
                                    f"Masukkan skor untuk pertanyaan {idx}",
                                    min_value=0, max_value=100, value=0,
                                    key=f"{nama}_{idx}_score"
                                )
                                fb = st.text_area(
                                    f"Catatan guru (opsional)",
                                    key=f"{nama}_{idx}_fb",
                                    height=60
                                )

                            total_score += score
                            count += 1

                        avg = round(total_score / count, 2) if count else 0
                        rekap.append({
                            "Nama": nama,
                            "Rata-rata Skor": avg,
                            "Analisis AI": (
                                "Pemahaman tinggi" if avg > 80 else
                                "Cukup baik" if avg >= 60 else
                                "Perlu bimbingan"
                            )
                        })
                        st.divider()

                    # ===== TABEL REKAP NILAI =====
                    st.markdown("## 📊 Rekapan Nilai Siswa")
                    df = pd.DataFrame(rekap)
                    st.dataframe(df, use_container_width=True)

# =========================================================
# MODE SISWA
# =========================================================
else:
    st.header("👩🎓 Mode Siswa — Kerjakan LKPD Pembelajaran Mendalam")
    lkpd_id = st.text_input("Masukkan ID LKPD yang diberikan guru")
    nama = st.text_input("Nama lengkap")
    if lkpd_id and nama:
        lkpd = load_json(LKPD_DIR, lkpd_id)
        if not lkpd:
            st.error("LKPD tidak ditemukan.")
        else:
            st.success(f"LKPD: {lkpd.get('judul', 'Tanpa Judul')}")
            card("🎯 Tujuan Pembelajaran", "<br>".join(lkpd.get("tujuan_pembelajaran", [])), "#eef2ff")
            card("📚 Materi Singkat", lkpd.get("materi_singkat", "(Belum ada materi)"), "#f0fdf4")

            jawaban_list = []

            # 🧩 Tampilkan Tahapan Pembelajaran (struktur baru)
            tahapan = lkpd.get("tahapan_pembelajaran", [])
            if tahapan:
                for i, tahap in enumerate(tahapan, 1):
                    with st.expander(f"🧭 Tahap {i}: {tahap.get('tahap', '')}"):
                        st.markdown(f"**Tujuan:** {tahap.get('deskripsi_tujuan', '')}")
                        st.markdown(f"**Bagian Inti:** {tahap.get('bagian_inti', '')}")
                        st.markdown(f"**Petunjuk:** {tahap.get('petunjuk', '')}")

                        # Jika ada pertanyaan pemantik
                        for j, q in enumerate(tahap.get("pertanyaan_pemantik", []), 1):
                            ans = st.text_area(f"{i}.{j} {q.get('pertanyaan')}", key=f"{lkpd_id}_{nama}_{i}_{j}", height=120)
                            jawaban_list.append({"pertanyaan": q.get("pertanyaan"), "jawaban": ans})

                        # Jika ada skenario (khusus tahap Mengaplikasikan)
                        for j, s in enumerate(tahap.get("skenario", []), 1):
                            st.markdown(f"**Skenario {j}: {s.get('judul','')}**")
                            st.write(s.get("deskripsi", ""))
                            ans = st.text_area(f"Analisis Skenario {j}: {s.get('pertanyaan')}", key=f"{lkpd_id}_{nama}_{i}_s{j}", height=120)
                            jawaban_list.append({"pertanyaan": s.get("pertanyaan"), "jawaban": ans})
            else:
                # fallback untuk LKPD versi lama
                for i, kegiatan in enumerate(lkpd.get("kegiatan", []), 1):
                    with st.expander(f"Kegiatan {i}: {kegiatan.get('nama','')}"):
                        st.write(kegiatan.get("petunjuk", ""))
                        for j, q in enumerate(kegiatan.get("pertanyaan_pemantik", []), 1):
                            ans = st.text_area(f"{i}.{j} {q.get('pertanyaan')}", key=f"{lkpd_id}_{nama}_{i}_{j}", height=120)
                            jawaban_list.append({"pertanyaan": q.get("pertanyaan"), "jawaban": ans})

            if st.button("📤 Submit Jawaban"):
                existing = load_json(ANSWERS_DIR, lkpd_id) or {}
                existing[nama] = {
                    "jawaban": jawaban_list,
                    "submitted_at": str(__import__('datetime').datetime.now())
                }
                save_json(ANSWERS_DIR, lkpd_id, existing)
                st.success("✅ Jawaban terkirim! Guru akan menilai dari sistem.")
    else:
        st.info("Masukkan ID LKPD dan nama untuk mulai mengerjakan.")
