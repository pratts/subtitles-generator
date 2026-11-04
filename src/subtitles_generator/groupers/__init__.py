"""
Phrase groupers for languages that WhisperX aligns per character (Japanese, Chinese, Cantonese).

A speaker change taken from diarization can fall inside a word when every character is its own unit
(け|ど, 日|本). A grouper merges the characters of each transcript block into phrases that nobody would
switch speaker in the middle of, so speakers are assigned and segments split per phrase.

Each language module provides tokens(text) -> [(surface, starts_phrase)]: the text split into words,
each marked with whether it starts a new phrase or attaches to the phrase before it.
Languages aligned per word (with spaces) need no grouper.
"""
import importlib
import unicodedata

GROUPERS = {"ja": "subtitles_generator.groupers.japanese", "zh": "subtitles_generator.groupers.chinese",
            "yue": "subtitles_generator.groupers.chinese"}


def group_into_phrases(units: list[dict], language: str) -> list[dict]:
    """Merge aligned units {"word", "start", "end", "score", "block"} into phrases; unchanged if not needed."""
    if language not in GROUPERS:
        return units
    tokenizer = importlib.import_module(GROUPERS[language])
    return [phrase for block in _blocks(units) for run in _latin_runs(block)
            for phrase in (run if run[0].get("latin") else _group_block(run, tokenizer.tokens))]


def _latin_runs(units: list[dict]) -> list[list[dict]]:
    """
    Split a block into runs of Latin words (marked "latin" by segment.py) and of the language's own text.
    Each Latin word stays a phrase of its own, as in English.
    """
    runs = []
    for u in units:
        if not runs or bool(runs[-1][-1].get("latin")) != bool(u.get("latin")):
            runs.append([])
        runs[-1].append(u)
    return runs


def _group_block(units: list[dict], tokens) -> list[dict]:
    text = "".join(u["word"] for u in units)
    owner, pos, phrase = [], 0, -1     # owner[i] = phrase index of text[i]
    for surface, starts_phrase in tokens(text):
        start = text.find(surface, pos)
        if start < 0:                  # the tokenizer normalized something: keep the rest in the current phrase
            break
        owner += [max(phrase, 0)] * (start - pos)
        if phrase < 0 or (starts_phrase and not _is_punctuation(surface)):
            phrase += 1
        owner += [phrase] * len(surface)
        pos = start + len(surface)
    owner += [max(phrase, 0)] * (len(text) - pos)

    # a unit belongs to the phrase of its first character (units can carry attached punctuation, e.g. す。)
    groups, offset = {}, 0
    for u in units:
        groups.setdefault(owner[offset], []).append(u)
        offset += len(u["word"])
    # keep the spaces between Latin words that segment.py marked with space_before
    return [{"word": "".join((" " if i and u.get("space_before") else "") + u["word"]
                             for i, u in enumerate(members)),
             "start": members[0]["start"],
             "end": members[-1]["end"],
             "score": _mean([u.get("score") for u in members]),
             "block": members[0]["block"],
             **({"space_before": True} if members[0].get("space_before") else {})}
            for members in groups.values()]


def _blocks(units: list[dict]) -> list[list[dict]]:
    blocks = []
    for u in units:
        if not blocks or blocks[-1][-1]["block"] != u["block"]:
            blocks.append([])
        blocks[-1].append(u)
    return blocks


def _is_punctuation(text: str) -> bool:
    return all(unicodedata.category(c).startswith("P") for c in text)


def _mean(values: list) -> float | None:
    values = [v for v in values if v is not None]
    return sum(values) / len(values) if values else None
