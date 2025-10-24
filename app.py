import streamlit as st
import uuid
import pandas as pd
from gemini_config import init_model, get_model, generate_lkpd, evaluate_answer_with_ai, save_lkpd, load_lkpd

# -------------------------------
# PAGE CONFIG
# -------------------------------
st.set_page_config(page_title="LMS EduAI (Generator & Evaluator)", page_icon="🎓", layout="wide")

# -------------------------------
# Initialize model using secrets
# -------------------------------
api_key = st.secrets.get("GEMINI_API_KEY") if "GEMINI_API_KEY" in st.secrets else None
ok, msg = init_model(api_key)
if not ok:
    st.error(f"Gemini initialization failed: {msg}")
    st.stop()

model = get_model()
if model is None:
    st.error("Model not available after init.")
    st.stop()

# -------------------------------
# Sidebar: role
# -------------------------------
role = st.sidebar.radio("Pilih Peran:", ["👨🏫 Guru", "👩🎓 Siswa"])

# -------------------------------
# Siswa: isi & kirim jawaban (simple)
# -------------------------------
if role == "👩🎓 Siswa":
    st.header("👩🎓 Mode Siswa — Isi LKPD")
    lkpd_id = st.text_input("Masukkan ID LKPD dari Guru (jika ada):")
    if lkpd_id:
        lkpd = load_lkpd(lkpd_id)
        if lkpd:
            st.success(f"LKPD '{lkpd.get('judul','')}' dimuat.")
            st.write(lkpd.get("materi_singkat",""))
            for i,keg in enumerate(lkpd.get("kegiatan",[]),1):
                with st.expander(f"Kegiatan {i}: {keg.get('nama','')}"):
                    st.write(keg.get('petunjuk',''))
                    for j,q in enumerate(keg.get("pertanyaan_pemantik",[]),1):
                        key = f"ans_{lkpd_id}_{i}_{j}"
                        st.text_area(f"{j}. {q.get('pertanyaan','')}", key=key, height=120)
            if st.button("Kirim Semua Jawaban"):
                st.success("Jawaban disubmit — guru akan mengevaluasi (fitur simpan nanti).")
        else:
            st.error("LKPD tidak ditemukan atau file corrupt.")
    else:
        st.info("Masukkan ID LKPD agar form muncul.")

# -------------------------------
# Guru: generate LKPD & semi-otomatis evaluasi
# -------------------------------
elif role == "👨🏫 Guru":
    st.header("👨🏫 Mode Guru")

    st.subheader("1) Generate LKPD Otomatis")
    theme = st.text_input("Topik / Tema:")
    if st.button("Generate LKPD"):
        if not theme.strip():
            st.warning("Masukkan topik terlebih dahulu.")
        else:
            with st.spinner("Menghasilkan LKPD..."):
                lkpd_data = generate_lkpd(theme)
                if lkpd_data:
                    lkpd_id = str(uuid.uuid4())[:8]
                    saved = save_lkpd(lkpd_id, lkpd_data)
                    if saved:
                        st.success(f"LKPD dibuat (ID: {lkpd_id})")
                        st.json(lkpd_data)
                    else:
                        st.error("Gagal menyimpan LKPD (file I/O).")
                else:
                    st.error("Gagal menghasilkan LKPD (AI). Coba lagi nanti.")

    st.markdown("---")
    st.subheader("2) Evaluasi Jawaban Siswa (Semi-Otomatis)")
    st.caption("Tempel jawaban siswa, klik 'AI Evaluate' → sesuaikan → simpan.")

    student_name = st.text_input("Nama Siswa (opsional):")
    question_text = st.text_input("Pertanyaan (opsional):")
    student_answer = st.text_area("Tempel Jawaban Siswa di sini:", height=220)

    if st.button("AI Evaluate"):
        if not student_answer.strip():
            st.warning("Tempel jawaban siswa dulu.")
        else:
            with st.spinner("AI sedang menilai..."):
                eval_res = evaluate_answer_with_ai(student_answer, question_text)
                if eval_res.get("error"):
                    st.error(f"AI Error: {eval_res.get('error')}")
                    if eval_res.get("raw"):
                        st.code(eval_res.get("raw")[:2000])
                else:
                    st.success("AI memberikan penilaian awal.")
                    st.metric("Skor (AI)", eval_res["overall_score"])
                    st.write("Breakdown (AI):", eval_res["score_breakdown"])
                    st.info("Feedback (AI):")
                    st.write(eval_res["feedback"])
                    st.info("Recommendation (AI):")
                    st.write(eval_res["recommendation"])
                    # store temporarily for adjustment
                    st.session_state["last_evaluation"] = {
                        "student_name": student_name,
                        "question": question_text,
                        "answer": student_answer,
                        "ai": eval_res
                    }

    # jika ada last eval, tampilkan form penyesuaian
    if "last_evaluation" in st.session_state:
        le = st.session_state["last_evaluation"]
        ai = le["ai"]
        st.markdown("---")
        st.subheader("Penyesuaian Hasil (oleh Guru)")
        final_score = st.number_input("Skor akhir (guru)", min_value=0, max_value=100, value=int(ai.get("overall_score", 0)))
        sb = ai.get("score_breakdown", {})
        c = st.number_input("Concept", 0, 100, value=int(sb.get("concept", 0)))
        a = st.number_input("Analysis", 0, 100, value=int(sb.get("analysis", 0)))
        ctx = st.number_input("Context", 0, 100, value=int(sb.get("context", 0)))
        r = st.number_input("Reflection", 0, 100, value=int(sb.get("reflection", 0)))
        teacher_notes = st.text_area("Catatan Guru (opsional)", height=120)

        if st.button("Simpan Evaluasi"):
            record = {
                "id": str(uuid.uuid4())[:8],
                "student_name": le.get("student_name",""),
                "question": le.get("question",""),
                "answer": le.get("answer",""),
                "final_score": int(final_score),
                "breakdown": {"concept":int(c),"analysis":int(a),"context":int(ctx),"reflection":int(r)},
                "teacher_notes": teacher_notes,
                "ai_raw": ai.get("raw","")
            }
            # simpan ke session list
            if "evaluations" not in st.session_state:
                st.session_state["evaluations"] = []
            st.session_state["evaluations"].append(record)
            # simpan ke CSV volatile
            df = pd.DataFrame([{
                "id": record["id"],
                "student_name": record["student_name"],
                "question": record["question"],
                "answer": record["answer"],
                "final_score": record["final_score"],
                "concept": record["breakdown"]["concept"],
                "analysis": record["breakdown"]["analysis"],
                "context": record["breakdown"]["context"],
                "reflection": record["breakdown"]["reflection"],
                "teacher_notes": record["teacher_notes"]
            }])
            if os.path.exists(EVAL_PATH := "evaluations.csv"):
                df.to_csv(EVAL_PATH, mode="a", header=False, index=False)
            else:
                df.to_csv(EVAL_PATH, index=False)
            st.success(f"✅ Evaluasi tersimpan (ID: {record['id']}).")
            # clear temp
            st.session_state.pop("last_evaluation", None)

    # show quick table of evaluations in this session
    if "evaluations" in st.session_state and st.session_state["evaluations"]:
        st.markdown("---")
        st.subheader("Riwayat Evaluasi (sesi saat ini)")
        st.write(st.session_state["evaluations"])

st.markdown("---")
st.caption("EduAI — Gemini-powered semi-automatic evaluation.")
