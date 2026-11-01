import dataclasses
import json
import os
import sys

import pytest

from subtitles_generator import cli, translate


def segment(text):
    return {"id": 0, "start": 1.0, "end": 2.5, "text": text}


def write(path, document):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(document, f, ensure_ascii=False)


def srt_text(path):
    with open(path, encoding="utf-8") as f:
        return f.read().strip().splitlines()[-1]


@pytest.fixture
def fake_stages(monkeypatch, tmp_path):
    """Replace every stage's work with a recorder that writes the stage's outputs; returns the calls."""
    calls = []

    def recorder(name):
        def run(r):
            calls.append(name if name != "translate" else f"translate:{r.target()}")
            if name == "transcribe":
                with open(r.transcript, "w") as f:
                    json.dump({"language": "ja"}, f)
            if name == "segment":
                write(r.segments, {"language": "ja", "segments": [segment("こんにちは")]})
            if name == "translate":
                text = f"{r.config['TRANSLATOR']} {r.target()}"
                write(r.translation(), {"segments": [{**segment("こんにちは"), "translation": text}]})
            for path in dict((s.name, s) for s in cli.STAGES)[name].outputs(r):
                os.makedirs(os.path.dirname(path), exist_ok=True)
                if not os.path.exists(path):
                    open(path, "w").close()
        return run

    monkeypatch.setattr(cli, "STAGES", [dataclasses.replace(s, run=recorder(s.name)) for s in cli.STAGES])
    monkeypatch.setattr(translate, "missing_credentials", lambda name: None)
    for name in ("SOURCE_LANGUAGE", "TARGET_LANGUAGES", "TRANSLATOR", "SEPARATE"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.chdir(tmp_path)
    (tmp_path / "talk.mp4").write_bytes(b"video")
    return calls


def test_target_languages_are_split_and_deduplicated():
    assert cli.target_languages(" es, fr,es,,hi ") == ["es", "fr", "hi"]
    assert cli.target_languages("") == []


def test_source_language_only_without_targets(fake_stages):
    cli.main(["talk.mp4"])
    assert fake_stages == ["extract", "transcribe", "segment"]
    assert os.path.exists("output/talk/talk.ja.srt")


def test_each_language_is_translated_once_and_kept(fake_stages):
    cli.main(["talk.mp4", "--to", "es,fr"])
    assert fake_stages == ["extract", "transcribe", "segment", "translate:es", "translate:fr"]
    assert os.path.exists("output/talk/talk.es.srt") and os.path.exists("output/talk/talk.fr.srt")

    fake_stages.clear()
    cli.main(["talk.mp4", "--to", "es,fr"])
    assert fake_stages == []                      # both languages are still up to date

    cli.main(["talk.mp4", "--to", "fr,hi"])
    assert fake_stages == ["translate:hi"]        # a new language does not transcribe again


def test_force_reruns_everything_once_and_every_translation(fake_stages):
    cli.main(["talk.mp4", "--to", "es,fr"])
    fake_stages.clear()
    cli.main(["talk.mp4", "--to", "es,fr", "--force"])
    assert fake_stages == ["extract", "transcribe", "segment", "translate:es", "translate:fr"]


def test_output_follows_the_selected_translator(fake_stages):
    cli.main(["talk.mp4", "--to", "es", "--translator", "google"])
    cli.main(["talk.mp4", "--to", "es", "--translator", "gpt"])
    assert srt_text("output/talk/talk.es.srt") == "gpt es"
    fake_stages.clear()
    cli.main(["talk.mp4", "--to", "es", "--translator", "google"])
    assert fake_stages == []                      # google's translation is reused...
    assert srt_text("output/talk/talk.es.srt") == "google es"    # ...and written again
    assert srt_text("output/talk/talk.ja.srt") == "こんにちは"


def test_separation_is_opt_in_and_switching_it_transcribes_again(fake_stages):
    cli.main(["talk.mp4", "--to", "es"])
    assert "separate" not in fake_stages
    fake_stages.clear()
    cli.main(["talk.mp4", "--to", "es", "--separate"])
    assert fake_stages == ["separate", "transcribe", "segment", "translate:es"]
    fake_stages.clear()
    cli.main(["talk.mp4", "--to", "es"])
    assert fake_stages == ["transcribe", "segment", "translate:es"]    # back to the full mix


def test_separation_without_demucs_says_how_to_install_it(monkeypatch, tmp_path):
    monkeypatch.setitem(sys.modules, "demucs", None)                   # as if not installed
    monkeypatch.delitem(sys.modules, "subtitles_generator.separate", raising=False)
    run = cli.Run(str(tmp_path / "talk.mp4"), {"TRANSLATOR": "gpt"}, str(tmp_path / "work"))
    with pytest.raises(SystemExit, match=r"\[separate\]"):
        cli.separate(run)


def test_a_missing_key_stops_before_transcribing(fake_stages, monkeypatch):
    monkeypatch.setattr(translate, "missing_credentials", lambda name: f"{name} needs a key")
    with pytest.raises(SystemExit, match="gpt needs a key"):
        cli.main(["talk.mp4", "--to", "es"])
    assert fake_stages == []
    cli.main(["talk.mp4"])                          # the video's own language needs no key
    assert fake_stages == ["extract", "transcribe", "segment"]


def test_clean_deletes_only_this_videos_work_and_output_folders(fake_stages, tmp_path):
    cli.main(["talk.mp4"])
    (tmp_path / "other.mp4").write_bytes(b"video")
    cli.main(["other.mp4"])
    assert os.path.exists("output/talk/talk.ja.srt") and os.path.exists("output/other/other.ja.srt")
    cli.main(["talk.mp4", "--clean"])
    assert not os.path.exists("work/talk") and not os.path.exists("output/talk")
    assert os.path.exists("work/other") and os.path.exists("output/other/other.ja.srt")
