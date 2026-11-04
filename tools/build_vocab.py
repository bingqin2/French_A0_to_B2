#!/usr/bin/env python3
"""Build per-lesson vocabulary lists from the lesson files.

Reads the "## 2. 单词 Vocabulary" section of every lesson (A1/, A2/, B1/, B2/),
plus the extra words in SUPPLEMENTS (words taught in prose or grammar tables),
and writes:
  词汇_Vocabulary/<level>/Lxx_词汇_Vocab.md    one word list per lesson
  词汇_Vocabulary/Anki/<level>_Anki.txt        tab-separated, ready for Anki import
Usage: python3 tools/build_vocab.py
"""
import glob
import hashlib
import os
import re

from importance import TIERS, rank, tier

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "词汇_Vocabulary")
LEVELS = ["A1", "A2", "B1", "B2"]
# Pronunciation audio made by build_anki_audio.py (macOS French voice)
VOICE, RATE = "Thomas", "150"
AUDIO_DIR = os.path.join(OUT, "Anki", "audio")

# Words a lesson teaches outside its vocabulary tables.
# lesson number -> list of (group heading, French, IPA, 中文, English, note)
SUPPLEMENTS = {
    2: [("喜好短语", "j'aime …", "[ʒɛm]", "我喜欢……", "I like …", ""),
        ("喜好短语", "je n'aime pas …", "[ʒə nɛm pa]", "我不喜欢……", "I don't like …", ""),
        ("喜好短语", "j'adore …", "[ʒa.dɔʁ]", "我非常喜欢……", "I love …", ""),
        ("喜好短语", "je déteste …", "[ʒə de.tɛst]", "我讨厌……", "I hate …", "")],
    3: [("自我介绍短语", "Je m'appelle …", "[ʒə ma.pɛl]", "我叫……", "My name is …", ""),
        ("自我介绍短语", "Enchanté(e) !", "[ɑ̃.ʃɑ̃.te]", "很高兴认识你！", "Nice to meet you!", "")],
    4: [("感觉", "avoir faim", "[fɛ̃]", "饿", "to be hungry", ""),
        ("感觉", "avoir soif", "[swaf]", "渴", "to be thirsty", ""),
        ("感觉", "avoir chaud", "[ʃo]", "（人）觉得热", "to be hot", ""),
        ("感觉", "avoir froid", "[fʁwa]", "（人）觉得冷", "to be cold", ""),
        ("感觉", "avoir peur", "[pœʁ]", "害怕", "to be afraid", ""),
        ("感觉", "avoir sommeil", "[sɔ.mɛj]", "困", "to be sleepy", ""),
        ("其他", "il y a", "[il.ja]", "有（存在）", "there is / there are", ""),
        ("其他", "Tu as quel âge ?", "[ty a kɛ.lɑʒ]", "你几岁？", "How old are you?", ""),
        ("数字", "un", "[œ̃]", "1", "one", "un‿an [œ̃.nɑ̃]"),
        ("数字", "deux", "[dø]", "2", "two", "deux‿ans [dø.zɑ̃]"),
        ("数字", "trois", "[tʁwa]", "3", "three", "trois‿ans [tʁwa.zɑ̃]"),
        ("数字", "quatre", "[katʁ]", "4", "four", ""),
        ("数字", "cinq", "[sɛ̃k]", "5", "five", ""),
        ("数字", "six", "[sis]", "6", "six", "six‿ans [si.zɑ̃]"),
        ("数字", "sept", "[sɛt]", "7", "seven", "p 不发音"),
        ("数字", "huit", "[ɥit]", "8", "eight", ""),
        ("数字", "neuf", "[nœf]", "9", "nine", "neuf‿ans [nœ.vɑ̃]，f 读 [v]"),
        ("数字", "dix", "[dis]", "10", "ten", "dix‿ans [di.zɑ̃]")],
    7: [("疑问词", "qui", "[ki]", "谁", "who", ""),
        ("疑问词", "que / qu'est-ce que", "[kə] / [kɛs.kə]", "什么", "what", "句首用"),
        ("疑问词", "quoi", "[kwa]", "什么", "what", "口语，句尾用"),
        ("疑问词", "où", "[u]", "哪里", "where", "≠ ou（或者）"),
        ("疑问词", "quand", "[kɑ̃]", "什么时候", "when", ""),
        ("疑问词", "comment", "[kɔ.mɑ̃]", "怎么样；如何", "how", ""),
        ("疑问词", "pourquoi", "[puʁ.kwa]", "为什么", "why", ""),
        ("疑问词", "parce que", "[paʁs.kə]", "因为", "because", ""),
        ("疑问词", "combien (de)", "[kɔ̃.bjɛ̃]", "多少", "how much / how many", ""),
        ("疑问词", "quel / quelle / quels / quelles", "[kɛl]", "哪个；什么", "which / what", "和名词配合")],
    9: [("数字 Numbers", w, ipa, zh, en, "") for w, ipa, zh, en in [
        ("zéro", "[ze.ʁo]", "0", "zero"), ("onze", "[ɔ̃z]", "11", "eleven"),
        ("douze", "[duz]", "12", "twelve"), ("treize", "[tʁɛz]", "13", "thirteen"),
        ("quatorze", "[ka.tɔʁz]", "14", "fourteen"), ("quinze", "[kɛ̃z]", "15", "fifteen"),
        ("seize", "[sɛz]", "16", "sixteen"), ("dix-sept", "[di.sɛt]", "17", "seventeen"),
        ("dix-huit", "[di.zɥit]", "18", "eighteen"), ("dix-neuf", "[diz.nœf]", "19", "nineteen"),
        ("vingt", "[vɛ̃]", "20", "twenty"), ("vingt et un", "[vɛ̃.te.œ̃]", "21", "twenty-one"),
        ("trente", "[tʁɑ̃t]", "30", "thirty"), ("quarante", "[ka.ʁɑ̃t]", "40", "forty"),
        ("cinquante", "[sɛ̃.kɑ̃t]", "50", "fifty"), ("soixante", "[swa.sɑ̃t]", "60", "sixty"),
        ("soixante-dix", "[swa.sɑ̃t.dis]", "70", "seventy"),
        ("soixante et onze", "[swa.sɑ̃.te.ɔ̃z]", "71", "seventy-one"),
        ("quatre-vingts", "[ka.tʁə.vɛ̃]", "80", "eighty"),
        ("quatre-vingt-un", "[ka.tʁə.vɛ̃.œ̃]", "81", "eighty-one"),
        ("quatre-vingt-dix", "[ka.tʁə.vɛ̃.dis]", "90", "ninety"),
        ("cent", "[sɑ̃]", "100", "one hundred")]],
    12: [],  # English for the country table is filled in by COUNTRY_EN below
    13: [("四季", "le printemps", "[pʁɛ̃.tɑ̃]", "春天", "spring", "au printemps"),
         ("四季", "l'été (m.)", "[e.te]", "夏天", "summer", "en été"),
         ("四季", "l'automne (m.)", "[o.tɔn]", "秋天", "autumn", "en automne；m 不发音"),
         ("四季", "l'hiver (m.)", "[i.vɛʁ]", "冬天", "winter", "en hiver"),
         ("天气表达 Weather", "Quel temps fait-il ?", "[kɛl tɑ̃ fɛ.til]", "天气怎么样？", "What's the weather like?", ""),
         ("天气表达 Weather", "Il fait beau / mauvais.", "[il fɛ bo / mɔ.vɛ]", "天气好 / 不好。", "The weather is nice / bad.", ""),
         ("天气表达 Weather", "Il fait chaud / froid.", "[il fɛ ʃo / fʁwa]", "天气热 / 冷。", "It's hot / cold.", ""),
         ("天气表达 Weather", "Il pleut.", "[il plø]", "下雨。", "It's raining.", ""),
         ("天气表达 Weather", "Il neige.", "[il nɛʒ]", "下雪。", "It's snowing.", "")],
    14: [("星期 Days", d, ipa, zh, en, "小写，阳性") for d, ipa, zh, en in [
        ("lundi", "[lœ̃.di]", "星期一", "Monday"), ("mardi", "[maʁ.di]", "星期二", "Tuesday"),
        ("mercredi", "[mɛʁ.kʁə.di]", "星期三", "Wednesday"), ("jeudi", "[ʒø.di]", "星期四", "Thursday"),
        ("vendredi", "[vɑ̃.dʁə.di]", "星期五", "Friday"), ("samedi", "[sam.di]", "星期六", "Saturday"),
        ("dimanche", "[di.mɑ̃ʃ]", "星期日", "Sunday")]]
        + [("月份 Months", m, ipa, zh, en, note) for m, ipa, zh, en, note in [
        ("janvier", "[ʒɑ̃.vje]", "一月", "January", ""), ("février", "[fe.vʁi.je]", "二月", "February", ""),
        ("mars", "[maʁs]", "三月", "March", "s 发音"), ("avril", "[a.vʁil]", "四月", "April", ""),
        ("mai", "[mɛ]", "五月", "May", ""), ("juin", "[ʒɥɛ̃]", "六月", "June", ""),
        ("juillet", "[ʒɥi.jɛ]", "七月", "July", ""), ("août", "[u] / [ut]", "八月", "August", ""),
        ("septembre", "[sɛp.tɑ̃bʁ]", "九月", "September", "p 发音"),
        ("octobre", "[ɔk.tɔbʁ]", "十月", "October", ""), ("novembre", "[nɔ.vɑ̃bʁ]", "十一月", "November", ""),
        ("décembre", "[de.sɑ̃bʁ]", "十二月", "December", "")]]
        + [("时间表达 Telling time", "Quelle heure est-il ?", "[kɛ.lœ.ʁɛ.til]", "几点了？", "What time is it?", ""),
           ("时间表达 Telling time", "et quart / et demie", "[e kaʁ] / [e də.mi]", "一刻 / 半", "quarter past / half past", ""),
           ("时间表达 Telling time", "moins le quart", "[mwɛ̃ lə kaʁ]", "差一刻", "quarter to", ""),
           ("时间表达 Telling time", "le premier (1er)", "[lə pʁə.mje]", "1 号", "the 1st", "其他日子用普通数字")],
    15: [("动词", "boire", "[bwaʁ]", "喝", "to drink", "je bois, nous buvons, ils boivent")],
    26: [("固定表达", "On y va ! / Allons-y !", "[ɔ̃.ni.va] / [a.lɔ̃.zi]", "我们走吧！", "Let's go!", ""),
         ("固定表达", "Vas-y ! / Allez-y !", "[va.zi] / [a.le.zi]", "去吧！加油！", "Go ahead!", ""),
         ("固定表达", "Il y en a.", "[il.jɑ̃.na]", "有（一些）。", "There is some.", ""),
         ("固定表达", "Il n'y en a plus.", "[il njɑ̃.na ply]", "没有了。", "There's none left.", ""),
         ("固定表达", "Ça y est !", "[sa.jɛ]", "好了！搞定了！", "That's it! Done!", ""),
         ("固定表达", "J'en ai marre !", "[ʒɑ̃.ne maʁ]", "我受够了！", "I'm fed up!", "口语"),
         ("固定表达", "Je m'en vais.", "[ʒə mɑ̃ vɛ]", "我走了。", "I'm leaving.", "")],
}

COUNTRY_EN = {
    "la Chine": "China", "la France": "France", "les États-Unis (m. pl.)": "the United States",
    "le Japon": "Japan", "la Corée (du Sud)": "(South) Korea", "le Canada": "Canada",
    "l'Angleterre (f.)": "England", "l'Allemagne (f.)": "Germany", "l'Espagne (f.)": "Spain",
    "l'Italie (f.)": "Italy", "le Mexique": "Mexico",
}


def clean(text):
    text = re.sub(r"\*+", "", text)
    return re.sub(r"\s+", " ", text).strip()


def split_ipa(cell):
    """'[fam] ⚠️ 读"fam"' -> ('[fam]', '⚠️ 读"fam"')"""
    ipa = " / ".join(re.findall(r"\[[^\]]*\]", cell))
    rest = clean(re.sub(r"\[[^\]]*\]|/", " ", cell))
    return ipa, rest


def parse_lesson(path):
    """Return ordered list of (group, [rows]) from the vocabulary section."""
    text = open(path, encoding="utf-8").read()
    m = re.search(r"^## \d+\. 单词.*?$(.*?)^## \d+\.", text, re.S | re.M)
    section = m.group(1) if m else ""
    groups, header = [(None, [])], None

    for line in section.split("\n"):
        if line.startswith("### "):
            groups.append((clean(line[4:]), []))
            header = None
            continue
        if not line.startswith("|"):
            header = None
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if header is None:
            header = cells
            continue
        if set("".join(cells)) <= set("-: "):
            continue
        if not any("中文" in h for h in header):
            continue  # e.g. a pronunciation table, not a word list
        row = {"fr": clean(cells[0]), "ipa": "", "zh": "", "en": "", "note": []}
        for h, c in zip(header[1:], cells[1:]):
            if "音标" in h or "IPA" in h:
                row["ipa"], extra = split_ipa(c)
                if extra:
                    row["note"].append(extra)
            elif "中文" in h:
                row["zh"] = clean(c)
            elif "English" in h:
                row["en"] = clean(c)
            elif clean(c):
                row["note"].append(f"{clean(h)}: {clean(c)}")
        # IPA written inside the French cell, e.g. "Attention ! [a.tɑ̃.sjɔ̃]"
        if not row["ipa"] and "[" in row["fr"]:
            row["ipa"] = " / ".join(re.findall(r"\[[^\]]*\]", row["fr"]))
            row["fr"] = clean(re.sub(r"\[[^\]]*\]", "", row["fr"]))
        if not row["en"] and row["fr"] in COUNTRY_EN:
            row["en"] = COUNTRY_EN[row["fr"]]
        row["note"] = "；".join(row["note"])
        groups[-1][1].append(row)
    return groups


def add_supplements(groups, num):
    for g, fr, ipa, zh, en, note in SUPPLEMENTS.get(num, []):
        row = {"fr": fr, "ipa": ipa, "zh": zh, "en": en, "note": note}
        for name, rows in groups:
            if name and g in name:
                rows.append(row)
                break
        else:
            groups.append((g, [row]))
    return [(g, rows) for g, rows in groups if rows]


def lesson_title(path):
    first = open(path, encoding="utf-8").readline()
    return clean(first.lstrip("# "))


def md_escape(s):
    return s.replace("|", "\\|")


def write_md(path, title, num, groups, lesson_rel, level):
    total = sum(len(r) for _, r in groups)
    counts = [0, 0, 0]
    for _, rows in groups:
        for r in rows:
            counts[tier(r["fr"], level)[0]] += 1
    lines = [f"# 第 {num} 课 词汇表 / Lesson {num} Vocabulary", "",
             f"> {title}  ",
             f"> 共 **{total}** 个词/短语 · *{total} words & phrases*  ",
             f"> 📖 课文 Lesson：[{os.path.basename(lesson_rel)}]({lesson_rel})  ",
             f"> 重要程度 Importance：⭐⭐⭐ 核心 {counts[0]} · ⭐⭐ 常用 {counts[1]} · ⭐ 了解 {counts[2]}"
             "（按法语日常使用频率 by how often French people use it）", "",
             "**时间不够时，先背 ⭐⭐⭐ 的词！** *Short on time? Learn the ⭐⭐⭐ words first.*", "",
             '<div class="vocab">', ""]
    for g, rows in groups:
        lines += [f"## {g or '常用词 Words'}", "",
                  "| 重要 | 法语 French | 音标 IPA | 中文 | English | 备注 Notes |",
                  "|---|---|---|---|---|---|"]
        for r in sorted(rows, key=lambda r: tier(r["fr"], level)[0]):
            lines.append("| " + " | ".join(md_escape(x) for x in
                         (tier(r["fr"], level)[1], f"**{r['fr']}**", r["ipa"], r["zh"], r["en"], r["note"])) + " |")
        lines.append("")
    lines += ["</div>", "", "---", "",
              "✅ 背完后：遮住法语那一列，看着中文 / English 说出法语（带冠词！）。",
              "*When done: cover the French column and say each word from the Chinese / English.*", ""]
    open(path, "w", encoding="utf-8").write("\n".join(lines))
    return total


def speech_text(fr):
    """'étudiant / étudiante' -> 'étudiant, étudiante'; drops (m.), (e), '…'."""
    text = re.sub(r"\([^)]*\)", "", fr)
    text = text.replace("…", "").replace(" / ", ", ").replace("/", ", ")
    return re.sub(r"\s+", " ", text).strip(" ,")


def audio_name(fr):
    key = f"{VOICE}|{RATE}|{speech_text(fr)}"
    return "fr_" + hashlib.md5(key.encode()).hexdigest()[:12] + ".mp3"


def all_words():
    """Yield (level, lesson number, row) for every word in every lesson."""
    for level in LEVELS:
        for path in sorted(glob.glob(os.path.join(ROOT, level, "L*.md"))):
            num = int(re.match(r"L(\d+)", os.path.basename(path)).group(1))
            for _, rows in add_supplements(parse_lesson(path), num):
                for r in rows:
                    yield level, num, r


def anki_line(r, tag, deck, level):
    t, stars, _ = tier(r["fr"], level)
    tag += " " + ["importance::1_core", "importance::2_common", "importance::3_extra"][t]
    if r["fr"] in DAY_OF:
        tag += f" day::{DAY_OF[r['fr']]:02d}"
    front = " / ".join(x for x in (r["zh"], r["en"]) if x)
    sound = audio_name(r["fr"])
    back = r["fr"] + (f"<br>{r['ipa']}" if r["ipa"] else "") + f"<br><small>{stars}</small>" + \
        (f"<br><small>{r['note']}</small>" if r["note"] else "") + \
        (f"[sound:{sound}]" if os.path.exists(os.path.join(AUDIO_DIR, sound)) else "")
    return "\t".join(x.replace("\t", " ") for x in (front, back, tag, deck))


def main():
    global DAY_OF
    DAY_OF = {r["fr"]: d for d, words in enumerate(daily_plan(), 1) for _, _, r in words}
    for level in LEVELS:
        lessons = sorted(glob.glob(os.path.join(ROOT, level, "L*.md")))
        if not lessons:
            continue
        os.makedirs(os.path.join(OUT, level), exist_ok=True)
        os.makedirs(os.path.join(OUT, "Anki"), exist_ok=True)
        anki = ["#separator:tab", "#html:true", "#notetype:Basic",
                "#tags column:3", "#deck column:4"]
        for path in lessons:
            name = os.path.basename(path)
            num = int(re.match(r"L(\d+)", name).group(1))
            groups = add_supplements(parse_lesson(path), num)
            out = os.path.join(OUT, level, f"L{num:02d}_词汇_Vocab.md")
            total = write_md(out, lesson_title(path), num, groups, f"../../{level}/{name}", level)
            for _, rows in groups:
                deck = f"法语 French::{level}::L{num:02d} " + lesson_title(path).split("·", 1)[-1].strip()
                anki += [anki_line(r, f"French::{level}::L{num:02d}", deck, level) for r in rows]
            print(f"✓ {level}/L{num:02d}_词汇_Vocab.md  ({total})")
        open(os.path.join(OUT, "Anki", f"{level}_Anki.txt"), "w", encoding="utf-8").write("\n".join(anki) + "\n")
        print(f"✓ Anki/{level}_Anki.txt  ({len(anki) - 5} cards)")
    write_important()
    write_extra()
    write_daily()


DAY_OF = {}
PER_DAY = 20
DAILY = "每日单词_Daily"


def ranked_words():
    """Every word once, most important first (tier, then level, then lesson order)."""
    seen, by_tier = set(), {0: [], 1: [], 2: []}
    for level, num, r in all_words():
        if r["fr"] in seen:
            continue
        seen.add(r["fr"])
        by_tier[tier(r["fr"], level)[0]].append((level, num, r))
    return by_tier


# Extra word lists (words no lesson teaches): level -> (tsv, page, title, goal text)
EXTRAS = {
    "B1": ("b1_extra.tsv", "00_B1补充单词_B1_extra_words.md", "B1 补充单词 / B1 Extra Words",
           "课程 80 课里没教、但达到 **B1** 必须会的"),
    "B2": ("b2_extra.tsv", "00_B2补充单词_NCLC7_words.md", "B2 / NCLC 7 补充单词 / B2 Exam Words",
           "考 **B2 / NCLC 7**（TCF / TEF Canada）常用、但课程和 B1 补充词里都没有的"),
}
EXTRA_MD = EXTRAS["B1"][1]


def _key(fr):
    return re.sub(r"\s+", " ", re.sub(r"\([^)]*\)", "", fr)).strip(" .!?").lower()


_extra_cache = {}


def extra_words(level=None):
    """Extra words for one level (or B1 + B2) that are not taught earlier, most common first."""
    if level is None:
        return extra_words("B1") + extra_words("B2")
    if level in _extra_cache:
        return _extra_cache[level]
    path = os.path.join(ROOT, "tools", "data", EXTRAS[level][0])
    if not os.path.exists(path):
        return []
    known = {_key(r["fr"]) for _, _, r in all_words()}
    if level == "B2":
        known |= {_key(r["fr"]) for r in extra_words("B1")}
    rows, seen = [], set()
    for line in open(path, encoding="utf-8"):
        f = line.rstrip("\n").split("\t")
        if line.startswith("#") or len(f) != 4 or _key(f[0]) in known or _key(f[0]) in seen:
            continue
        seen.add(_key(f[0]))
        rows.append({"fr": f[0], "ipa": "", "zh": f[1], "en": f[2], "note": "", "theme": f[3]})
    rows.sort(key=lambda r: (tier(r["fr"], level)[0], rank(r["fr"])))
    _extra_cache[level] = rows
    return rows


def course_plan():
    words = [w for i in range(3) for w in ranked_words()[i]]
    return [words[i:i + PER_DAY] for i in range(0, len(words), PER_DAY)]


def extra_plan(level):
    extra = [(level + "+", None, r) for r in extra_words(level)]
    return [extra[i:i + PER_DAY] for i in range(0, len(extra), PER_DAY)]


def daily_plan():
    """Course words first, then the B1 extra words, then the B2 / NCLC 7 words; PER_DAY a day."""
    return course_plan() + extra_plan("B1") + extra_plan("B2")


def lesson_files():
    titles = {}
    for level in LEVELS:
        for p in glob.glob(os.path.join(ROOT, level, "L*.md")):
            titles[int(re.match(r"L(\d+)", os.path.basename(p)).group(1))] = (level, os.path.basename(p))
    return titles


def write_daily():
    """One short list per day: 词汇_Vocabulary/每日单词_Daily/Day_NN.md + an index page."""
    days = daily_plan()
    n = len(days)
    n1 = len(course_plan())
    n2 = n1 + len(extra_plan("B1"))
    out = os.path.join(OUT, DAILY)
    os.makedirs(out, exist_ok=True)
    for old in glob.glob(os.path.join(out, "Day_*.md")):
        os.remove(old)
    index = ["# 每日单词 / One List a Day", "",
             f"> 共 {sum(map(len, days))} 个单词，分成 **{n} 天**，每天 **{PER_DAY} 个**。  ",
             f"> - **第 1–{n1} 天**：课程里的全部单词，最重要的在前面（先学完全部 ⭐⭐⭐ 核心词）。  ",
             f"> - **第 {n1 + 1}–{n2} 天**：[B1 补充单词]({EXTRAS['B1'][1]})——课程没教、"
             "但达到 B1 必须会的常用词。  ",
             f"> - **第 {n2 + 1}–{n} 天**：[B2 / NCLC 7 补充单词]({EXTRAS['B2'][1]})——"
             "TCF / TEF Canada 考试常见话题的词（环境、工作、移民、科技……）。  ",
             f"> *{n} short lists of {PER_DAY}: course words, then B1 extra words, then B2 / NCLC 7 exam words.*", "",
             "🎯 **目标 B1**：第 1–50 天左右（A1–B1 课程词）+ 第 "
             f"{n1 + 1}–{n2} 天，大约 2,000 个词。  ",
             f"🎯 **目标 NCLC 7 / B2**：全部 {n} 天，大约 {sum(map(len, days)):,} 个词。"
             "备考方法见 [NCLC 7 备考](../NCLC7_备考_Exam_prep/00_NCLC7_总览_Overview.md)。", "",
             "💡 **每天怎么学 (about 15 min)**",
             "1. 打开今天的列表，每个词点 🔊 听 2–3 遍，跟着读出声。",
             "2. 用页面最上面的 🎧 听写练习，练到大部分都能写对。",
             "3. 复习页面上列出的前几天（第 1、3、7 天前学的词），每天各听写几个。",
             "4. 点页面最下面的 **✅ 今天背完了**，这一页会打勾。",
             "",
             "Anki：在浏览器里搜 `tag:day::01` 就只看第 1 天的词（`tag:day::0*` 是第 1–9 天）。", "",
             "| 天 Day | 单词 Words | 重要 | 进度 |", "|---|---|---|---|"]
    for d, words in enumerate(days, 1):
        if d == 1:
            index += [f"| **第一部分 Part 1 · 课程单词 Course words** | | | |"]
        if d == n1 + 1:
            index += [f"| **第二部分 Part 2 · B1 补充单词 Extra words** | | | |"]
        if d == n2 + 1:
            index += [f"| **第三部分 Part 3 · B2 / NCLC 7 考试词 Exam words** | | | |"]
        stars = sorted({tier(r["fr"], lv)[1] for lv, _, r in words}, key=len, reverse=True)
        preview = ", ".join(r["fr"].rstrip(" …") for _, _, r in words[:4]) + " …"
        index.append(f"| [Day {d:02d}]({DAILY}/Day_{d:02d}.md) | {md_escape(preview)} | "
                     f"{' '.join(stars)} | <span class=\"daymark\" data-day=\"{d}\"></span> |")
        write_day(out, d, n, words)
    index.append("")
    open(os.path.join(OUT, "00_每日单词_Daily_words.md"), "w", encoding="utf-8").write("\n".join(index))
    print(f"✓ 00_每日单词_Daily_words.md  ({n} days × {PER_DAY} words)")


def write_day(out, d, n, words):
    titles = lesson_files()
    nav = []
    if d > 1:
        nav.append(f"[← Day {d - 1:02d}](Day_{d - 1:02d}.md)")
    nav.append("[📅 全部天数 All days](../00_每日单词_Daily_words.md)")
    if d < n:
        nav.append(f"[Day {d + 1:02d} →](Day_{d + 1:02d}.md)")
    review = [f"[Day {d - k:02d}](Day_{d - k:02d}.md)" for k in (1, 3, 7) if d - k >= 1]
    lines = [f"# 第 {d} 天 / Day {d:02d}", "", " · ".join(nav), "",
             f"> 今天的 {len(words)} 个新词。先点 🔊 听、跟读，再用上面的 🎧 听写练习。  ",
             f"> *Today's {len(words)} new words. Listen, repeat, then use the dictation above.*", ""]
    if review:
        lines += ["🔁 **今天也复习 Also review:** " + " · ".join(review), ""]
    lines += ["| 重要 | 法语 French | 中文 | English | 课 Lesson |", "|---|---|---|---|---|"]
    for lv, num, r in words:
        if num is None:
            link = f"[{lv}](../{EXTRAS[lv[:2]][1]})"
        else:
            lv2, _ = titles[num]
            link = f"[L{num:02d}](../{lv2}/L{num:02d}_词汇_Vocab.md)"
        lines.append(f"| {tier(r['fr'], lv)[1]} | " + " | ".join(md_escape(x) for x in
                     (f"**{r['fr']}**", r["zh"], r["en"])) + f" | {link} |")
    lines += ["", f'<div class="daydone" data-day="{d}"></div>', "", " · ".join(nav), ""]
    open(os.path.join(out, f"Day_{d:02d}.md"), "w", encoding="utf-8").write("\n".join(lines))


def write_extra():
    for level in EXTRAS:
        write_extra_level(level)


def write_extra_level(level):
    """Extra words of one level: one page grouped by theme, plus an Anki file."""
    tsv, md, title, intro = EXTRAS[level]
    rows = extra_words(level)
    if not rows:
        return
    order = []
    for ln in open(os.path.join(ROOT, "tools", "data", tsv), encoding="utf-8"):
        if not ln.startswith("#") and ln.count("\t") == 3 and ln.split("\t")[3].strip() not in order:
            order.append(ln.split("\t")[3].strip())
    themes = [t for t in order if any(r["theme"] == t for r in rows)]
    n = [sum(1 for r in rows if tier(r["fr"], level)[0] == i) for i in range(3)]
    lines = [f"# {title}", "",
             f"> {intro} **{len(rows)} 个词**，按主题排列，每个主题里最重要的在前面。"
             "它们也已经分进了 [每日单词](00_每日单词_Daily_words.md)。  ",
             f"> *{len(rows)} extra words for {level}, by theme, most important first.*", "",
             f"⭐⭐⭐ {n[0]} · ⭐⭐ {n[1]} · ⭐ {n[2]}", ""] + (
             ["⚠️ 星级按**日常口语**的频率算，很多考试写作用的正式词（如 *néanmoins*、*engendrer*）"
              "在口语里少见，所以只有 ⭐。但考 NCLC 7 的写作和阅读时**它们都很有用**，不要跳过。", ""]
             if level == "B2" else []) + [
             "**主题 Themes：** " + " · ".join(f"[{t}](#{i + 1})" for i, t in enumerate(themes)), ""]
    anki = ["#separator:tab", "#html:true", "#notetype:Basic", "#tags column:3", "#deck column:4"]
    deck = {"B1": "B1 补充 Extra", "B2": "B2 NCLC 7"}[level]
    for i, t in enumerate(themes, 1):
        group = sorted((r for r in rows if r["theme"] == t), key=lambda r: tier(r["fr"], level)[0])
        lines += [f'<a id="{i}"></a>', "", f"## {i}. {t}（{len(group)}）", "",
                  "| 重要 | 法语 French | 中文 | English |", "|---|---|---|---|"]
        for r in group:
            lines.append(f"| {tier(r['fr'], level)[1]} | " + " | ".join(md_escape(x) for x in
                         (f"**{r['fr']}**", r["zh"], r["en"])) + " |")
            anki.append(anki_line(r, f"French::{level}_extra", f"法语 French::{deck}::{i:02d} {t}", level))
        lines.append("")
    open(os.path.join(OUT, md), "w", encoding="utf-8").write("\n".join(lines))
    open(os.path.join(OUT, "Anki", f"{level}_extra_Anki.txt"), "w", encoding="utf-8").write("\n".join(anki) + "\n")
    print(f"✓ {md}  ({len(rows)} words) + Anki/{level}_extra_Anki.txt")


def write_important():
    """One page with every word, most important first: 词汇_Vocabulary/00_重要单词_Important_words.md"""
    seen, by_tier = set(), {0: [], 1: [], 2: []}
    titles = {}
    for level, num, r in all_words():
        if r["fr"] in seen:
            continue
        seen.add(r["fr"])
        by_tier[tier(r["fr"], level)[0]].append((level, num, r))
    for level in LEVELS:
        for p in glob.glob(os.path.join(ROOT, level, "L*.md")):
            titles[int(re.match(r"L(\d+)", os.path.basename(p)).group(1))] = (level, os.path.basename(p))
    n = [len(by_tier[i]) for i in range(3)]
    lines = ["# 重要单词 / Most Important Words", "",
             "> 全部课程的单词，按**重要程度**排列。重要程度 = 法国人日常说话时用这个词有多频繁"
             "（根据法语影视字幕的词频统计），数字、星期、月份等基础词一律算核心。  ",
             "> *Every word in the course, most important first — ranked by how often it is used in "
             "everyday spoken French (film & TV subtitles).*", "",
             f"| 等级 | 意思 | 词数 | 建议 |", "|---|---|---|---|",
             f"| ⭐⭐⭐ 核心 Core | 最常用的约 1,000 个词之一 | {n[0]} | **必须会听、会说、会写** |",
             f"| ⭐⭐ 常用 Common | 最常用的 1,000–4,000 词 | {n[1]} | 会听、会读，常用的会说 |",
             f"| ⭐ 了解 Good to know | 较少用或较正式 | {n[2]} | 认识就行，阅读和考试时用 |", "",
             "💡 **怎么用**：每天打开这一页，用最上面的 🎧 听写练习，先把 ⭐⭐⭐ 全部练到能听写正确。"
             "Anki 里也可以只学核心词：在浏览器里搜 `tag:importance::1_core`。", "",
             '<div class="important">', ""]
    for i in range(3):
        stars, label = TIERS[i][1], TIERS[i][2]
        lines += [f"## {stars} {label}（{n[i]}）", ""]
        for level in LEVELS:
            rows = [x for x in by_tier[i] if x[0] == level]
            if not rows:
                continue
            lines += [f"### {level}（{len(rows)}）", "",
                      "| 法语 French | 中文 | English | 课 Lesson |", "|---|---|---|---|"]
            for lv, num, r in rows:
                lv2, fname = titles[num]
                link = f"[L{num:02d}]({lv2}/L{num:02d}_词汇_Vocab.md)"
                lines.append("| " + " | ".join(md_escape(x) for x in
                             (f"**{r['fr']}**", r["zh"], r["en"])) + f" | {link} |")
            lines.append("")
    lines += ["</div>", ""]
    open(os.path.join(OUT, "00_重要单词_Important_words.md"), "w", encoding="utf-8").write("\n".join(lines))
    print(f"✓ 00_重要单词_Important_words.md  (⭐⭐⭐ {n[0]} · ⭐⭐ {n[1]} · ⭐ {n[2]})")


if __name__ == "__main__":
    main()
