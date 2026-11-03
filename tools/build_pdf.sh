#!/bin/bash
# Build pronunciation audio and vocabulary lists, then PDF versions of everything:
# one PDF per lesson and per vocabulary list, plus one combined PDF per level.
# Usage: tools/build_pdf.sh   (run from anywhere)
# Needs: python3, pandoc, Google Chrome.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$ROOT/PDF"
STYLE="$ROOT/tools/pdf_style.html"
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# Markdown file -> standalone HTML (links to .md become links to .pdf)
md_to_html() {
  local md="$1" html="$2"
  pandoc -f gfm+hard_line_breaks -t html5 -s \
    --metadata pagetitle="$(basename "$md" .md)" \
    --include-in-header="$STYLE" \
    "$md" | sed -E 's/href="([^"]+)\.md"/href="\1.pdf"/g' > "$html"
}

html_to_pdf() {
  "$CHROME" --headless=new --disable-gpu --no-pdf-header-footer \
    --print-to-pdf="$2" "file://$1" >/dev/null 2>&1
}

# build_set <source dir> <output dir> <combined pdf path>
build_set() {
  local src="$1" dest="$2" combined_pdf="$3"
  local combined="$TMP/$(basename "$combined_pdf" .pdf).md" first=1
  mkdir -p "$dest"
  : > "$combined"
  for md in "$src"/L*.md; do
    local name
    name="$(basename "$md" .md)"
    md_to_html "$md" "$TMP/$name.html"
    html_to_pdf "$TMP/$name.html" "$dest/$name.pdf"
    echo "✓ ${dest#$OUT/}/$name.pdf"
    # Each lesson starts on a new page in the combined PDF
    [ $first -eq 1 ] || printf '\n\n<div class="lesson-break"></div>\n\n' >> "$combined"
    cat "$md" >> "$combined"
    first=0
  done
  md_to_html "$combined" "$TMP/combined.html"
  html_to_pdf "$TMP/combined.html" "$combined_pdf"
  echo "✓ ${combined_pdf#$OUT/}"
}

python3 "$ROOT/tools/build_anki_audio.py"   # audio, then vocab lists + Anki files
mkdir -p "$OUT"

md_to_html "$ROOT/00_学习路线_Roadmap.md" "$TMP/roadmap.html"
html_to_pdf "$TMP/roadmap.html" "$OUT/00_学习路线_Roadmap.pdf"
echo "✓ 00_学习路线_Roadmap.pdf"

for level in A1 A2 B1 B2; do
  [ -d "$ROOT/$level" ] || continue
  build_set "$ROOT/$level" "$OUT/$level" "$OUT/${level}_全部课程_All_lessons.pdf"
  build_set "$ROOT/词汇_Vocabulary/$level" "$OUT/词汇_Vocabulary/$level" \
    "$OUT/词汇_Vocabulary/${level}_全部词汇_All_vocab.pdf"
done

# Most-important-words list
md_to_html "$ROOT/词汇_Vocabulary/00_重要单词_Important_words.md" "$TMP/important.html"
html_to_pdf "$TMP/important.html" "$OUT/词汇_Vocabulary/00_重要单词_Important_words.pdf"
echo "✓ 词汇_Vocabulary/00_重要单词_Important_words.pdf"

# Website (docs/) for GitHub Pages
python3 "$ROOT/tools/build_site.py"
