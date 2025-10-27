import streamlit as st
if not lkpd:
st.error("LKPD tidak ditemukan.")
else:
st.success(f"Memantau LKPD: {lkpd.get('judul', 'Tanpa Judul')}")
answers = load_json(ANSWERS_DIR, lkpd_id) or {}
if not answers:
st.info("Belum ada jawaban siswa.")
else:
for nama, record in answers.items():
st.subheader(f"🧑‍🎓 {nama}")
for idx, q in enumerate(record.get("jawaban", []), 1):
st.markdown(f"**{idx}. {q.get('pertanyaan')}**")
st.markdown(f"✏️ Jawaban siswa: {q.get('jawaban')}")
ai_analysis = analyze_answer_with_ai(q.get('jawaban'))
st.info(f"💬 Analisis AI: {ai_analysis['penjelasan']}")
st.markdown(f"📊 Saran Nilai AI: **{ai_analysis['skor']} / 100**")
nilai_guru = st.number_input(
f"Nilai akhir (guru menyesuaikan)",
0, 100, int(ai_analysis['skor'] or 0), key=f"nilai_{nama}_{idx}"
)
st.divider()


# ---------------------------------------------------------
# SISWA MODE
# ---------------------------------------------------------
else:
lkpd_id = st.text_input("Masukkan ID LKPD dari guru")
nama = st.text_input("Nama lengkap siswa")


if lkpd_id and nama:
lkpd = load_json(LKPD_DIR, lkpd_id)
if not lkpd:
st.error("LKPD tidak ditemukan.")
else:
st.success(f"Mengisi LKPD: {lkpd.get('judul', 'Tanpa Judul')}")
st.markdown(f"### 🎯 Tujuan Pembelajaran")
st.write("\n".join(lkpd.get("tujuan_pembelajaran", [])))
st.markdown(f"### 📚 Materi Singkat")
st.info(lkpd.get("materi_singkat", "(Belum ada materi)"))


jawaban_list = []
for i, kegiatan in enumerate(lkpd.get("kegiatan", []), 1):
with st.expander(f"📘 Kegiatan {i}: {kegiatan.get('nama')}"):
st.write(kegiatan.get("petunjuk", ""))
for j, q in enumerate(kegiatan.get("pertanyaan_pemantik", []), 1):
ans = st.text_area(
f"{i}.{j} {q.get('pertanyaan')}", height=120, key=f"{lkpd_id}_{nama}_{i}_{j}"
)
jawaban_list.append({"pertanyaan": q.get('pertanyaan'), "jawaban": ans})


if st.button("📤 Submit Jawaban"):
existing = load_json(ANSWERS_DIR, lkpd_id) or {}
existing[nama] = {
"jawaban": jawaban_list,
"submitted_at": str(datetime.now())
}
save_json(ANSWERS_DIR, lkpd_id, existing)
st.success("Jawaban berhasil dikirim ke guru!")
else:
st.info("Masukkan ID LKPD dan nama siswa untuk mulai mengerjakan.")
