# 法语 A0 → B2 / French from Zero to B2

80 lessons (30 min each) that teach French grammar in Chinese and English, plus the core vocabulary for each lesson.

- 🌐 **Website**: every French word and sentence has a 🔊 button (Google's online French voice, with the browser voice and local recordings as fallbacks). Vocabulary pages add a 👤 link to native-speaker recordings on Forvo and a 🎧 dictation exercise.
- 📖 Lessons: `A1/`, `A2/`, `B1/`, `B2/` (Markdown)
- 📒 Word lists: `词汇_Vocabulary/`; Anki import files with audio in `词汇_Vocabulary/Anki/`
- 📄 PDFs: `PDF/`
- Start here: [00_学习路线_Roadmap.md](00_学习路线_Roadmap.md)

Rebuild everything (audio, word lists, Anki files, PDFs, website): `bash tools/build_pdf.sh`
Website only: `python3 tools/build_site.py` (output in `docs/`)

## Word importance ⭐
Every word is rated ⭐⭐⭐ core / ⭐⭐ common / ⭐ good to know by how often it is used in spoken French. The full ranked list is in [词汇_Vocabulary/00_重要单词_Important_words.md](词汇_Vocabulary/00_重要单词_Important_words.md).
Frequency data: [hermitdave/FrequencyWords](https://github.com/hermitdave/FrequencyWords) (OpenSubtitles 2018, CC BY-SA 4.0), in `tools/data/fr_50k.txt`.
