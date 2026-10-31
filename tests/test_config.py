from subtitles_generator.config import load_config


def test_precedence_defaults_file_env_flags(tmp_path, monkeypatch):
    for name in ("TRANSLATOR", "TARGET_LANGUAGES", "SEGMENT_MIN_DURATION", "SEGMENT_MERGE_GAP", "LLM_MODEL"):
        monkeypatch.delenv(name, raising=False)
    config_file = tmp_path / "config.toml"
    config_file.write_text('translator = "google"\ntarget_languages = "es"\nsegment_min_duration = 2\n'
                           'llm_model = "qwen2.5:14b"\n')
    monkeypatch.setenv("TARGET_LANGUAGES", "fr,hi")
    monkeypatch.setenv("SEGMENT_MERGE_GAP", "0.5")
    config = load_config(str(config_file), {"TRANSLATOR": "GPT", "SOURCE_LANGUAGE": None})
    assert config["TRANSLATOR"] == "gpt"              # flag beats file
    assert config["TARGET_LANGUAGES"] == "fr,hi"      # environment beats file
    assert config["SEGMENT_MIN_DURATION"] == 2.0 and config["SEGMENT_MERGE_GAP"] == 0.5
    assert config["SOURCE_LANGUAGE"] == ""            # default
    import os
    assert os.environ["LLM_MODEL"] == "qwen2.5:14b"   # exported for the backend that reads it


def test_gpt_is_the_default_translator(monkeypatch):
    monkeypatch.delenv("TRANSLATOR", raising=False)
    monkeypatch.chdir("/")                            # no config.toml
    assert load_config()["TRANSLATOR"] == "gpt"


def test_unknown_setting_is_an_error(tmp_path):
    import pytest
    bad = tmp_path / "config.toml"
    bad.write_text('translater = "gpt"\n')
    with pytest.raises(ValueError, match="translater"):
        load_config(str(bad))
