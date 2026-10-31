# Roadmap

**Principle for every phase:** build the simplest version, and add a feature only when real output shows a need.
The deferred items below are ideas, not commitments.

## Phase 1: the CLI script
**Goal:** `subtitle video.mp4 --to es,fr` writes `output/<name>.<lang>.srt` for the source language and each
target language.

**Main work**
- Port video-translator's extract, transcribe, segment, translate and translators, with the glossary (#1)
- Split segments longer than 2 lines of 42 characters or 7 s at the nearest word gap, using word timestamps
- A short README with install and usage

**Complications to expect**
- Segments come from dubbing rules (whole sentences), so lines can be long until the split step lands.
- Translations keep the source segment's timing; word order differs between languages, so a sentence split
  across segments can show words before they are spoken.
- The gpt prompt and character budget in `translate.py` are written for dubbing.
- Whisper can invent text over music or silence, more so on mlx, which has no VAD.

**Deferred, add if real output shows a need**
- `--burn`: one subtitle track burned into a copy of the video (needs ffmpeg with libass and a font for the script)
- `--embed`: soft subtitle tracks tagged with their language, in the input's container
- VAD for the mlx backend, or dropping segments whose aligned words score very low
- Merge-first split-back: put a translated sentence into its segments' combined slot before splitting it
- gpt checks: exactly one line per segment, with a retry and a proportional-split fallback
- CJK reading-speed and line-length rules

## Phase 2: a PyPI package
**Goal:** `pip install subtitles-generator` gives a working `subtitle` command, with no clone needed.

**Main work**
- Version pins in `pyproject.toml` itself, since users of the package never see `constraints.txt`
- Build and publish (name checked free on PyPI on 2026-10-31), with release notes
- A README written as the project's front page: pitch, quick start, examples, translator choices (nllb free but
  rougher, google better, gpt best with glossary and context), the first-run model download, config reference,
  known limitations

**Complications to expect**
- whisperx pins torch and huggingface-hub; loose pins break installs, strict pins clash with users' other packages.
- ffmpeg can't be installed by pip; the CLI needs a clear error when it is missing.
- A large install (torch, models) and a ~2.4 GB NLLB download on first use; the first run must not look stuck.
- `config.toml`, `.env`, `work/` and `output/` resolve against the current folder, which matters once users run
  it from anywhere.

**Deferred, add if real output shows a need**
- CI: a GitHub Actions workflow running the tests, with a README badge (before the first release); then make
  its check required in the main branch ruleset
- Optional extras: `[separate]` (Demucs), `[diarize]` (pyannote, needs a Hugging Face token)

## Phase 3: a web app
**Goal:** an upload page with a language picker, progress and download links, running on the same core code as
the CLI.

**Main work**
- A function the CLI and the web app both call, reporting progress through a callback
- A background job queue, one worker per GPU or model in memory
- Limits on upload size and duration, and cleanup of uploaded and generated files

**Complications to expect**
- Transcription needs a GPU to be fast; on CPU a long video takes many minutes. A hosted transcription API option
  would let it run without one, but changes the word timestamps the segments depend on.
- Models are several GB; loading them per job is slow, keeping them loaded limits concurrency.
- Translation keys live on the server, so usage costs need limits per user or per job.
- Uploaded videos are user data: keep them only as long as the job, never in logs.

**Deferred, add if real output shows a need**
- VTT output, for playing subtitles in the browser with `<track>`
