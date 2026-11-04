"""
Lines Whisper writes when nobody speaks: during silence or music it can write a line learned from the ends of
videos, or its prompt (the glossary terms) back as speech.
"""
import re
import unicodedata

# Known outro lines by language, compared without punctuation, spaces or case
WHISPER_OUTROS = {
    "en": ["Thank you for watching", "Thanks for watching", "Subtitles by the Amara.org community"],
    "ja": ["ご視聴ありがとうございました"],
    "ko": ["시청해주셔서 감사합니다"],
    "zh": ["字幕由Amara.org社区提供", "请不吝点赞 订阅 转发 打赏支持明镜与点点栏目"],
}
# separators of the glossary list in Whisper's prompt (see transcribe.asr_prompt), and how Whisper ends it
PROMPT_SEPARATORS = r"[、，,。.।]"


def _compact(text: str) -> str:
    return "".join(c for c in text.casefold() if not c.isspace() and not unicodedata.category(c).startswith("P"))


# any language's outro, since Whisper can write one in another language than the video's
_OUTROS = {_compact(line) for lines in WHISPER_OUTROS.values() for line in lines}


def is_invented(text: str, glossary_terms: list[str]) -> bool:
    """
    Whether a block of Whisper's text was invented: a known outro line, or the glossary prompt written back
    ("ニコ、タカシ、アヤ、渋谷、浅草。", "アヤ、アヤ、アヤ。"). A list counts only with two different terms or one term three
    times, and without ! or ?, so that shouted names ("Toph! Toph!", "Momo, Momo.") are kept.
    """
    if _compact(text) in _OUTROS:
        return True
    if re.search(r"[!?！？]", text):
        return False
    parts = [p.strip() for p in re.split(PROMPT_SEPARATORS, text) if p.strip()]
    terms = {t.strip() for t in glossary_terms}
    return bool(parts) and all(p in terms for p in parts) and (len(set(parts)) >= 2 or len(parts) >= 3)


def drop_invented(transcript: dict, glossary_terms: list[str]) -> tuple[dict, list[str]]:
    """The transcript without invented blocks, and the texts that were dropped."""
    kept, dropped = [], []
    for block in transcript["segments"]:
        (dropped if is_invented(block.get("text", ""), glossary_terms) else kept).append(block)
    return {**transcript, "segments": kept}, [b["text"].strip() for b in dropped]
