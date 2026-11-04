from subtitles_generator.invented import drop_invented, is_invented
from subtitles_generator.segment import build_segments


def test_whisper_outro_lines_are_invented():
    assert is_invented("ご視聴ありがとうございました。", [])
    assert is_invented(" Thanks for watching!", [])
    assert not is_invented("どうもありがとうございました。", [])
    assert not is_invented("Thanks for watching the kids last night.", [])


def test_the_glossary_prompt_written_back_is_invented():
    terms = ["平山", "ニコ", "タカシ", "アヤ", "渋谷", "浅草"]
    assert is_invented("ニコ、タカシ、アヤ、渋谷、浅草。", terms)
    assert is_invented("アヤ、アヤ、アヤ。", terms)
    assert is_invented("सुग्रीव, लंका.", ["राम", "सुग्रीव", "लंका"])
    assert not is_invented("アヤ、ニコと渋谷に行った。", terms)       # other words too
    assert not is_invented("Toph! Toph!", ["Toph"])                  # shouted names
    assert not is_invented("Momo, Momo.", ["Momo"])
    assert not is_invented("राम.", ["राम"])


def block(i, text, start):
    words = [{"word": w, "start": start + k * 0.4, "end": start + k * 0.4 + 0.3, "score": 0.9}
             for k, w in enumerate(text.split())]
    return {"id": i, "start": start, "end": words[-1]["end"], "text": " " + text, "words": words}


def test_invented_blocks_are_dropped_before_segments_are_built():
    t = {"language": "en", "segments": [block(0, "Thanks for watching.", 0.0), block(1, "Hello there.", 2.0)]}
    kept, dropped = drop_invented(t, [])
    assert dropped == ["Thanks for watching."]
    assert [s["text"] for s in build_segments(kept, [], 5.0)["segments"]] == ["Hello there."]
