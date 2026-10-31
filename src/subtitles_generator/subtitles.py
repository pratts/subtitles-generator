import os
from datetime import timedelta

import srt


def write_subtitles(document: dict, field: str, path: str) -> str:
    """One subtitle per segment, with the segment's timing (no speaker labels)."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    subtitles = [srt.Subtitle(index=i + 1, start=timedelta(seconds=s["start"]), end=timedelta(seconds=s["end"]),
                              content=s[field]) for i, s in enumerate(document["segments"]) if s[field].strip()]
    with open(path, "w", encoding="utf-8") as f:
        f.write(srt.compose(subtitles))
    print(f"✅ Saved {len(subtitles)} subtitles to {path}")
    return path


def subtitles_path(video_path: str, language: str, output_dir: str) -> str:
    """output/<video name>.<language>.srt"""
    name = os.path.splitext(os.path.basename(video_path))[0]
    return os.path.join(output_dir, f"{name}.{language}.srt")
