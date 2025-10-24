# Di dalam blok "if st.session_state.role == '👨🏫 Guru':" tambahkan subseksi Evaluasi Jawaban
st.markdown("## 🧾 Evaluasi Jawaban (Semi-Otomatis)")
st.caption("Tempel jawaban siswa di bawah. Klik 'AI Evaluate' untuk mendapatkan skor awal dan feedback dari AI. Guru dapat menyesuaikan lalu klik 'Save Evaluation'.")

# Input jawaban siswa
question_text = st.text_input("Pertanyaan (opsional) — copy pertanyaan dari LKPD jika ada", value="")
student_name = st.text_input("Nama Siswa (opsional)", value="")
student_answer = st.text_area("Tempel jawaban siswa di sini:", height=200)

col_a, col_b = st.columns([1,1])
with col_a:
    if st.button("🤖 AI Evaluate"):
        if not student_answer.strip():
            st.warning("Masukkan jawaban siswa dulu.")
        else:
            with st.spinner("Mengirim ke AI untuk penilaian..."):
                eval_result = evaluate_answer_with_ai(student_answer, question_text)
                # simpan hasil sementara di session_state
                st.session_state['last_eval'] = {
                    "student_name": student_name,
                    "question": question_text,
                    "answer": student_answer,
                    "ai_result": eval_result
                }
                if "error" in eval_result:
                    st.error(f"AI Error: {eval_result.get('error')}")
                    if eval_result.get("raw"):
                        st.code(eval_result.get("raw")[:1000], language="json")
                else:
                    st.success("AI telah memberikan penilaian awal.")
                    # tampilkan ringkasan
                    st.metric("Skor (AI)", eval_result["overall_score"])
                    sb = eval_result["score_breakdown"]
                    st.write("Breakdown (AI):")
                    st.write(sb)
                    st.write("Feedback (AI):")
                    st.info(eval_result["feedback"])
                    st.write("Recommendation (AI):")
                    st.info(eval_result["recommendation"])

with col_b:
    # Tombol reset
    if st.button("Reset Evaluasi"):
        st.session_state.pop("last_eval", None)
        st.success("Evaluasi sementara direset.")

# Jika ada hasil AI, tampilkan form penyesuaian untuk guru
if 'last_eval' in st.session_state:
    le = st.session_state['last_eval']
    ai = le.get("ai_result", {})
    if "error" not in ai:
        st.markdown("---")
        st.subheader("🔧 Penyesuaian dan Simpan (oleh Guru)")
        # Editable scores: teacher can tweak
        adj_overall = st.number_input("Skor Akhir (guru dapat ubah)", min_value=0, max_value=100, value=ai.get("overall_score", 0), step=1)
        sb = ai.get("score_breakdown", {})
        adj_concept = st.number_input("Concept (0-100)", 0, 100, sb.get("concept",0))
        adj_analysis = st.number_input("Analysis (0-100)", 0, 100, sb.get("analysis",0))
        adj_context = st.number_input("Context (0-100)", 0, 100, sb.get("context",0))
        adj_reflection = st.number_input("Reflection (0-100)", 0, 100, sb.get("reflection",0))

        adj_feedback = st.text_area("Ubah/Edit Feedback (AI)", value=ai.get("feedback",""), height=120)
        adj_recommendation = st.text_area("Ubah/Edit Recommendation (AI)", value=ai.get("recommendation",""), height=80)

        if st.button("💾 Save Evaluation"):
            # buat struktur tersimpan
            record = {
                "id": str(uuid.uuid4())[:8],
                "timestamp": str(__import__("datetime").datetime.now()),
                "student_name": le.get("student_name",""),
                "question": le.get("question",""),
                "answer": le.get("answer",""),
                "overall_score": int(adj_overall),
                "score_breakdown": {
                    "concept": int(adj_concept),
                    "analysis": int(adj_analysis),
                    "context": int(adj_context),
                    "reflection": int(adj_reflection)
                },
                "feedback": adj_feedback,
                "recommendation": adj_recommendation,
                "ai_raw": ai.get("raw", "")
            }

            # simpan ke session_state list
            if "evaluations" not in st.session_state:
                st.session_state["evaluations"] = []
            st.session_state["evaluations"].append(record)

            # juga append ke CSV lokal (volatile)
            import pandas as pd
            eval_path = "evaluations.csv"
            df_row = pd.DataFrame([{
                "id": record["id"],
                "timestamp": record["timestamp"],
                "student_name": record["student_name"],
                "question": record["question"],
                "answer": record["answer"],
                "overall_score": record["overall_score"],
                "concept": record["score_breakdown"]["concept"],
                "analysis": record["score_breakdown"]["analysis"],
                "context": record["score_breakdown"]["context"],
                "reflection": record["score_breakdown"]["reflection"],
                "feedback": record["feedback"],
                "recommendation": record["recommendation"]
            }])
            if os.path.exists(eval_path):
                df_row.to_csv(eval_path, mode='a', header=False, index=False)
            else:
                df_row.to_csv(eval_path, index=False)

            st.success(f"✅ Evaluasi disimpan (ID: {record['id']}).")
            # clear last_eval
            st.session_state.pop("last_eval", None)
