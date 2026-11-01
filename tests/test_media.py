import shutil

from subtitles_generator import media


def test_missing_tools_names_what_is_missing_and_how_to_install_it(monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda tool: None if tool == "ffprobe" else f"/usr/bin/{tool}")
    monkeypatch.setattr(media.sys, "platform", "darwin")
    assert media.missing_tools() == ("ffprobe not found on PATH: install ffmpeg (brew install ffmpeg) "
                                     "and run again")
    monkeypatch.setattr(shutil, "which", lambda tool: None)
    monkeypatch.setattr(media.sys, "platform", "linux")
    problem = media.missing_tools()
    assert problem.startswith("ffmpeg and ffprobe not found") and "apt install ffmpeg" in problem


def test_nothing_missing(monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda tool: f"/usr/bin/{tool}")
    assert media.missing_tools() is None
