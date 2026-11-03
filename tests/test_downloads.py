import os

import huggingface_hub.constants
import pytest
import torch

from subtitles_generator import downloads
from subtitles_generator.transcribe import _align_model_cached


def fake_hf_model(cache, repo_id):
    folder = cache / f"models--{repo_id.replace('/', '--')}"
    (folder / "refs").mkdir(parents=True)
    (folder / "refs" / "main").write_text("abc123")
    (folder / "snapshots" / "abc123").mkdir(parents=True)


def test_download_is_announced_only_when_not_cached(capsys):
    downloads.announce("the Whisper model large-v3-turbo", cached=False)
    downloads.announce("the Whisper model large-v3-turbo", cached=True)
    assert capsys.readouterr().out == "⬇️ Downloading the Whisper model large-v3-turbo (first run only)...\n"


def test_hugging_face_cache_is_checked_without_downloading(monkeypatch, tmp_path):
    monkeypatch.setattr(huggingface_hub.constants, "HF_HUB_CACHE", str(tmp_path))
    monkeypatch.setattr(huggingface_hub.constants, "HF_HUB_OFFLINE", True)   # a network call would fail
    assert not downloads.hf_cached("jonatasgrosman/wav2vec2-large-xlsr-53-japanese")
    assert not _align_model_cached("ja")
    fake_hf_model(tmp_path, "jonatasgrosman/wav2vec2-large-xlsr-53-japanese")
    assert downloads.hf_cached("jonatasgrosman/wav2vec2-large-xlsr-53-japanese")
    assert _align_model_cached("ja")


def test_torchaudio_aligner_cache(monkeypatch, tmp_path):
    monkeypatch.setattr(torch.hub, "get_dir", lambda: str(tmp_path))
    assert not _align_model_cached("fr")
    (tmp_path / "checkpoints").mkdir()
    (tmp_path / "checkpoints" / "wav2vec2_voxpopuli_base_10k_asr_fr.pt").write_bytes(b"")
    assert _align_model_cached("fr")


def test_unused_safetensors_conversion_is_turned_off():
    # transformers' background download of a converted copy of the Japanese aligner, never loaded
    assert os.environ["DISABLE_SAFETENSORS_CONVERSION"] == "true"


def test_demucs_cache(monkeypatch, tmp_path):
    separate = pytest.importorskip("subtitles_generator.separate")
    monkeypatch.setattr(huggingface_hub.constants, "HF_HUB_CACHE", str(tmp_path))
    assert not separate._demucs_cached("htdemucs_ft")
    fake_hf_model(tmp_path, "adefossez/HTDemucs-ft")
    assert separate._demucs_cached("htdemucs_ft")
