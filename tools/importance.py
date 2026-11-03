#!/usr/bin/env python3
"""How important is a French word or phrase? Ranked by how often it is used.

Frequencies come from tools/data/fr_50k.txt: the 50,000 most common word forms
in French film and TV subtitles, i.e. everyday spoken French. Source:
hermitdave/FrequencyWords (https://github.com/hermitdave/FrequencyWords),
licensed CC BY-SA 4.0.

A phrase is as rare as its rarest content word. A verb is also looked up by
its common conjugated forms, a noun or adjective by its feminine/plural forms.
"""
import os
import re

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "fr_50k.txt")
TIERS = [  # (max rank, stars, label)
    (1000, "⭐⭐⭐", "核心 Core"),
    (4000, "⭐⭐", "常用 Common"),
    (10 ** 9, "⭐", "了解 Good to know"),
]
# Words that don't decide a phrase's importance (articles, pronouns, prepositions…)
FUNCTION = set("""le la les l un une des du de d au aux à en y je j tu il elle on nous vous ils elles
me m te t se s lui leur moi toi soi eux ce c cet cette ces mon ma mes ton ta tes son sa ses notre nos
votre vos leurs que qu qui quoi et ou ne n pas plus avec pour par sur dans chez sans être avoir faire
est a qn qqn qch quelqu quelque chose""".split())

# Always core, even if subtitles rarely use them: numbers, days, months, seasons, weather.
ALWAYS_CORE = re.compile(r"\b(zéro|un|deux|trois|quatre|cinq|six|sept|huit|neuf|dix|onze|douze|treize|"
                         r"quatorze|quinze|seize|vingts?|trente|quarante|cinquante|soixante|cent|mille|"
                         r"lundi|mardi|mercredi|jeudi|vendredi|samedi|dimanche|janvier|février|mars|avril|"
                         r"mai|juin|juillet|août|septembre|octobre|novembre|décembre|printemps|été|"
                         r"automne|hiver|pleut|neige)\b", re.I)

_rank = None


def _load():
    global _rank
    if _rank is None:
        _rank = {}
        for i, line in enumerate(open(DATA, encoding="utf-8")):
            w = line.split(" ", 1)[0]
            _rank.setdefault(w, i + 1)
    return _rank


def _forms(w):
    f = {w, w + "s", w + "e", w + "es"}
    if w.endswith("er"):
        s = w[:-2]
        f |= {s + "e", s + "es", s + "é", s + "ez", s + "ons", s + "ent", s + "ait", s + "ais"}
    elif w.endswith("ir"):
        s = w[:-2]
        f |= {s + "is", s + "it", s + "i", s + "issez", s + "ons", s + "ez", s + "ent"}
    elif w.endswith("re"):
        s = w[:-2]
        f |= {s + "s", s + "t", s + "u", s + "ez", s + "ons", s + "ent", s}
    if w.endswith("eux"):
        f.add(w[:-1] + "se")
    if w.endswith("if"):
        f.add(w[:-1] + "ve")
    return f


def word_rank(w):
    r = _load()
    return min((r[x] for x in _forms(w) if x in r), default=60000)


def _alt_rank(text):
    words = re.findall(r"[a-zà-ÿœæ]+", text.lower().replace("’", "'"))
    words = [w for w in words if len(w) > 1 or w in ("y", "a")]
    content = [w for w in words if w not in FUNCTION]
    use = content or words
    if not use:
        return 60000
    return max(word_rank(w) for w in use)


def rank(fr):
    """Frequency rank of a vocabulary entry (lower = more common)."""
    text = re.sub(r"\([^)]*\)|\[[^\]]*\]|…|\.\.\.", " ", fr)
    alts = [a for a in re.split(r"\s/\s|/", text) if a.strip()]
    return min((_alt_rank(a) for a in alts), default=60000)


def tier(fr, level=None):
    """Return (index 0–2, stars, label); index 0 = most important.

    A1 words are the foundation, so they are never below ⭐⭐."""
    r = rank(fr)
    i = next(i for i, (limit, _, _) in enumerate(TIERS) if r <= limit)
    words = re.sub(r"\([^)]*\)|\[[^\]]*\]", " ", fr)
    if ALWAYS_CORE.search(words) and len(words.split()) <= 3 and not words.lower().startswith(("un ", "une ")):
        i = 0
    if level == "A1":
        i = min(i, 1)
    return i, TIERS[i][1], TIERS[i][2]
