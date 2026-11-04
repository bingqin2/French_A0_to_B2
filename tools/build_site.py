#!/usr/bin/env python3
"""Build the study website (docs/) from the Markdown lessons.

Every French word or sentence gets a 🔊 button. Clicking it plays the
pronunciation from Google Translate's online French voice; if that fails it
falls back to the browser's French voice, then to the local mp3 (vocabulary
words only). Vocabulary words also get a 👤 link to Forvo (recordings by
native speakers), and every vocabulary page has a dictation (听写) exercise.

The site is plain HTML, so GitHub Pages can serve the docs/ folder as is.
Usage: python3 tools/build_site.py
"""
import glob
import html
import os
import re
import shutil
import subprocess
import sys
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from importance import tier  # noqa: E402
from build_vocab import AUDIO_DIR, LEVELS, ROOT, audio_name, speech_text  # noqa: E402

SITE = os.path.join(ROOT, "docs")
ROADMAP = "00_学习路线_Roadmap.md"
ASSETS = os.path.join(ROOT, "tools", "site")

FR_WORDS = set("""le la les l un une des du de d je j tu il elle on nous vous ils elles est sont suis
es êtes sommes et que qu qui ne n pas en au aux à ce c ça cette ces mon ma mes ton ta tes son sa ses
notre nos votre vos leur leurs pour avec dans sur très plus moins se s y me m te t lui eux moi toi
mais ou où si bien quand comme aussi ai as avons avez ont va vais vas allons allez vont fait faire
peux veux dois veut peut doit oui non merci bonjour bonsoir salut voilà voici chez sans par il_y_a
était avait sera serait aurait faut tout tous toute toutes rien jamais personne quelque déjà encore""".split())
EN_WORDS = set("""the is are was were you i an to of and for with it this that in be my your do does
did don't what how why when where he she they we his her their our have has had will would can
could should not no yes one some any from by at or so if than then there here him them just like
only also works adds used drop drops same first big step look around say sentences change takes
take merges memorize sound sounds form feel weather other three spring top inside vehicle foot
orders requests suggestions let's let simple present past tense common spoken means after before
always never word words verb verbs subject english french chinese""".split())


def looks_french(text):
    if re.search(r"[一-鿿]", text):           # contains Chinese
        return False
    words = re.findall(r"[a-zA-ZÀ-ÿœŒ']+", text.lower().replace("’", "'"))
    words = [w for part in words for w in part.split("'") if w]
    if not words:
        return False
    fr = sum(w in FR_WORDS for w in words)
    en = sum(w in EN_WORDS for w in words)
    if en >= 2 or (en == 1 and fr <= 1 and len(words) > 2):
        return False
    if re.search(r"[éèêëàâçîïôûùüœ]", text.lower()):
        return True
    return fr > en or (fr == en == 0 and len(words) <= 3)


def strip_tags(s):
    return html.unescape(re.sub(r"<[^>]+>", "", s))


def say_text(raw):
    """Text to speak: drop IPA, emoji, (m.)/(f.)/(e), '…', '❌'."""
    t = re.sub(r"\[[^\]]*\]", " ", raw)
    t = re.sub(r"[⚠️❌✅⭐👂📌💡🔊→←↔+=]", " ", t)
    t = speech_text(t)
    t = re.sub(r"\s+", " ", t).strip(" ,;:")
    return t


def button(text, mp3=None):
    attrs = f' data-t="{html.escape(text, quote=True)}"'
    if mp3:
        attrs += f' data-mp3="{mp3}"'
    return f'<button class="say" title="听发音 Listen"{attrs}>🔊</button>'


def forvo(word):
    w = re.split(r"[ ,]", word.strip())
    if len(w) > 2:
        return ""
    q = urllib.parse.quote(word.strip())
    return (f'<a class="forvo" href="https://forvo.com/word/{q}/#fr" target="_blank" rel="noopener"'
            f' title="真人发音 Native speakers (Forvo)">👤</a>')


def add_buttons_to_tables(body, depth, level=None):
    prefix = "../" * depth

    def fix_table(m):
        table = m.group(0)
        head = re.search(r"<thead>(.*?)</thead>", table, re.S)
        if not head:
            return table
        heads = [strip_tags(h) for h in re.findall(r"<th[^>]*>(.*?)</th>", head.group(1), re.S)]
        cols = [i for i, h in enumerate(heads)
                if ("法语" in h or "French" in h or "Français" in h) and "English" not in h]
        is_vocab = any("中文" in h for h in heads)
        if not cols:
            return table

        def fix_row(rm):
            row = rm.group(0)
            cells = list(re.finditer(r"<td([^>]*)>(.*?)</td>", row, re.S))
            for i in reversed(cols):
                if i >= len(cells):
                    continue
                c = cells[i]
                text = say_text(strip_tags(c.group(2)))
                if not text or re.search(r"[一-鿿]", text):
                    continue
                fr_cell = re.sub(r"\[[^\]]*\]", "", strip_tags(c.group(2))).strip()
                mp3 = audio_name(re.sub(r"\s+", " ", fr_cell)) if is_vocab else None
                if mp3 and not os.path.exists(os.path.join(AUDIO_DIR, mp3)):
                    mp3 = None
                extra = button(text, mp3 and prefix + "audio/" + mp3)
                if is_vocab:
                    extra += forvo(text)
                    if level and not any("重要" in h for h in heads):
                        extra += f' <span class="stars">{tier(fr_cell, level)[1]}</span>'
                new = f'<td{c.group(1)}><span class="fr">{c.group(2)}</span> {extra}</td>'
                row = row[:c.start()] + new + row[c.end():]
            return row

        return re.sub(r"<tr>.*?</tr>", fix_row, table, flags=re.S)

    return re.sub(r"<table>.*?</table>", fix_table, body, flags=re.S)


def add_buttons_to_italics(body):
    def fix(m):
        inner = m.group(1)
        if "class=\"say\"" in inner:
            return m.group(0)
        text = strip_tags(inner)
        if not looks_french(text):
            return m.group(0)
        t = say_text(text)
        if not t or t.startswith("-") or len(t) < 2:
            return m.group(0)
        return f"<em>{inner}</em>{button(t)}"

    # only <em> that is not inside a table cell we already handled
    return re.sub(r"<em>(.*?)</em>", fix, body, flags=re.S)


def roadmap_links(md):
    """Turn the ✅ cell of each lesson row into links to the lesson and its word list."""
    lessons = {}
    for level in LEVELS:
        for p in glob.glob(os.path.join(ROOT, level, "L*.md")):
            n = int(re.match(r"L(\d+)", os.path.basename(p)).group(1))
            lessons[n] = (level, os.path.basename(p)[:-3])

    def fix(m):
        n = int(m.group(1))
        if n not in lessons:
            return m.group(0)
        level, name = lessons[n]
        return (f"| {m.group(1)} |{m.group(2)}| [📖 课文]({level}/{name}.md) · "
                f"[📒 单词](词汇_Vocabulary/{level}/L{n:02d}_词汇_Vocab.md) |")

    md = re.sub(r"^\| (\d\d) \|(.*)\| ✅ \|$", fix, md, flags=re.M)
    return md.replace("✅ = 已生成 ready · ⬜ = 待生成 coming next",
                      "点 📖 看课文，点 📒 看单词表（每个词都能点 🔊 听发音）。")


def render(md_text, src_path, depth, title):
    body = subprocess.run(["pandoc", "-f", "gfm+hard_line_breaks", "-t", "html5"],
                          input=md_text, capture_output=True, text=True, check=True).stdout
    body = re.sub(r'href="([^"#]+)\.md(#[^"]*)?"',
                  lambda m: f'href="{m.group(1)}.html{m.group(2) or ""}"', body)
    body = body.replace(f'href="{ROADMAP[:-3]}.html"', 'href="index.html"')
    body = re.sub(r'href="((?:\.\./)+)' + re.escape(ROADMAP[:-3]) + r'\.html"', r'href="\1index.html"', body)
    body = re.sub(r'(<a\s+href="[^"]+\.html">[^<]*?)\.md</a>', r"\1</a>", body)
    lv = next((x for x in LEVELS if f"{os.sep}{x}{os.sep}" in src_path), None)
    body = add_buttons_to_tables(body, depth, lv if "词汇_Vocabulary" not in src_path else None)
    body = add_buttons_to_italics(body)
    is_vocab = "词汇_Vocabulary" in src_path
    up = "../" * depth
    tpl = open(os.path.join(ASSETS, "template.html"), encoding="utf-8").read()
    return (tpl.replace("{{TITLE}}", html.escape(title))
               .replace("{{UP}}", up)
               .replace("{{DICTATION}}", '<div id="dictation"></div>' if is_vocab else "")
               .replace("{{BODY}}", body))


def build_page(src, out, depth):
    md = open(src, encoding="utf-8").read()
    if os.path.basename(src) == ROADMAP:
        md = roadmap_links(md)
    title = re.sub(r"[#*]", "", md.split("\n", 1)[0]).strip()
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, "w", encoding="utf-8").write(render(md, src, depth, title))


def main():
    if os.path.isdir(SITE):
        shutil.rmtree(SITE)
    os.makedirs(SITE)
    build_page(os.path.join(ROOT, ROADMAP), os.path.join(SITE, "index.html"), 0)
    count = 1
    for level in LEVELS:
        for src in sorted(glob.glob(os.path.join(ROOT, level, "L*.md"))):
            build_page(src, os.path.join(SITE, level, os.path.basename(src)[:-3] + ".html"), 1)
            count += 1
        for src in sorted(glob.glob(os.path.join(ROOT, "词汇_Vocabulary", level, "L*.md"))):
            build_page(src, os.path.join(SITE, "词汇_Vocabulary", level,
                                         os.path.basename(src)[:-3] + ".html"), 2)
            count += 1
    imp = os.path.join(ROOT, "词汇_Vocabulary", "00_重要单词_Important_words.md")
    if os.path.exists(imp):
        build_page(imp, os.path.join(SITE, "词汇_Vocabulary", "00_重要单词_Important_words.html"), 1)
        count += 1
    extra = os.path.join(ROOT, "词汇_Vocabulary", "00_B1补充单词_B1_extra_words.md")
    if os.path.exists(extra):
        build_page(extra, os.path.join(SITE, "词汇_Vocabulary", "00_B1补充单词_B1_extra_words.html"), 1)
        count += 1
    daily = os.path.join(ROOT, "词汇_Vocabulary", "00_每日单词_Daily_words.md")
    if os.path.exists(daily):
        build_page(daily, os.path.join(SITE, "词汇_Vocabulary", "00_每日单词_Daily_words.html"), 1)
        count += 1
    for src in sorted(glob.glob(os.path.join(ROOT, "词汇_Vocabulary", "每日单词_Daily", "Day_*.md"))):
        build_page(src, os.path.join(SITE, "词汇_Vocabulary", "每日单词_Daily",
                                     os.path.basename(src)[:-3] + ".html"), 2)
        count += 1
    shutil.copy(os.path.join(ASSETS, "site.css"), SITE)
    shutil.copy(os.path.join(ASSETS, "site.js"), SITE)
    shutil.copytree(AUDIO_DIR, os.path.join(SITE, "audio"))
    open(os.path.join(SITE, ".nojekyll"), "w").close()
    print(f"✓ website: {count} pages in docs/  (open docs/index.html)")


if __name__ == "__main__":
    main()
