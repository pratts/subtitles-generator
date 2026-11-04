# subtitles-generator
[![Tests](https://github.com/pratts/subtitles-generator/actions/workflows/tests.yml/badge.svg)](https://github.com/pratts/subtitles-generator/actions/workflows/tests.yml)

Subtitles for any video, in any language.

`subtitle video.mp4 --to en,fr` transcribes the video with Whisper, times every word, and writes `.srt` subtitles in the video's own language and in each language you ask for.

- **Any language:** the video's language is detected, and the subtitles can be translated into any language
- **Timed per word:** every word is aligned to the audio, so lines start and end with the speech and are split between words
- **Names spelled right:** a glossary gives Whisper and the translator the spellings of names and places
- **Two translators:** `gpt` (OpenAI, or a local model through Ollama) uses the glossary and a description of the video; `google` is a literal translation
- **Resumable:** finished steps are kept, so adding a language only translates
- **Speech under music:** `--separate` removes music and noise before transcription

## Example
From a 42 s street interview in Japanese, with `subtitle video.mp4 --to en,fr --glossary glossary.json`:
```
1
00:00:01,883 --> 00:00:04,307
みなさん、こんにちは。熊谷真奈です。

2
00:00:04,669 --> 00:00:07,494
Easy Japaneseは仙台からお送りします。
```
```
1
00:00:01,883 --> 00:00:04,307
Hello everyone. I'm Mana Kumagai.

2
00:00:04,669 --> 00:00:07,494
Easy Japanese is coming to you from Sendai.
```
```
1
00:00:01,883 --> 00:00:04,307
Bonjour à tous. Je suis Mana Kumagai.

2
00:00:04,669 --> 00:00:07,494
Easy Japanese vous est présenté depuis Sendai.
```

## Quick start
You need Python 3.12 or higher and ffmpeg (`brew install ffmpeg`, `sudo apt install ffmpeg` or `winget install ffmpeg`).

1. Install:
   ```bash
   git clone https://github.com/pratts/subtitles-generator.git
   cd subtitles-generator
   python3.12 -m venv venv
   source venv/bin/activate
   pip install -e . -c constraints.txt
   ```
2. For translation, copy `.env.example` to `.env` and set `OPENAI_API_KEY` ([get a key](https://platform.openai.com/api-keys)). Subtitles in the video's own language need no key.
3. Run:
   ```bash
   subtitle my-video.mp4 --to en
   ```
   The subtitles are in `output/my-video/`: one file in the video's language (e.g. `my-video.ja.srt`) and `my-video.en.srt`.

`constraints.txt` holds the versions tested together. The install is large (PyTorch and WhisperX), and the first run downloads the models (see [First run](#first-run)).

## Translators
| | `gpt` (default) | `google` |
|---|---|---|
| Needs | `OPENAI_API_KEY`, or `llm_base_url` for a local OpenAI-compatible server such as [Ollama](https://ollama.com) (free) | A Google Cloud project with the Cloud Translation API enabled, and a service account JSON key in `GOOGLE_APPLICATION_CREDENTIALS` |
| Glossary and context | used | ignored |
| Translation | faithful, in natural written language, with the neighbouring lines as context | literal, line by line |
| Cost | about $0.20 per language for an hour of video like the example, with `gpt-5-mini`; more when more is said | $20 per million characters of source text, after 500,000 free each month; an hour of the example is about 10,000 characters |

Measured on the example and scaled to an hour: `gpt-5-mini` used 430 input and 1,070 output tokens per language (at $0.25 and $2.00 per million), and the source text has 123 characters. Prices as of November 2026.

## Speed
On an Apple M4 Pro, per minute of video, after the models are loaded (8 to 17 s per run):
| Step | Time |
|---|---|
| Transcription and alignment, `whisperx` on CPU (default) | about 11 s |
| Transcription and alignment, `mlx` on Apple Silicon | about 3 to 4 s |
| Vocal separation (`--separate`) | about 70 s |

## Usage
```bash
subtitle my-video.mp4                          # subtitles in the video's own language
subtitle my-video.mp4 --to es,fr,hi            # ... and in Spanish, French and Hindi
subtitle my-video.mp4 --to en --from ja        # skip language detection
subtitle my-video.mp4 --to en --translator google
```
Subtitles in the video's own language are always written, so `--to` only needs the other languages; the video's own language in `--to` is skipped. Subtitles are written to `output/<video name>/<video name>.<language>.srt`. They are named after the video, so a video player loads them when they are copied next to it. Run `subtitle --help` for all options.

### Names and context
Whisper and translators often misspell names. A glossary fixes that:
```json
{"熊谷真奈": "Mana Kumagai", "仙台": "Sendai"}
```
```bash
subtitle my-video.mp4 --to en --glossary glossary.json --context "Street interview in Sendai about life in Japan"
```
The glossary's source terms are given to Whisper so it spells them as written; with a Japanese or Chinese glossary this also makes Whisper add punctuation, which gives better line breaks. The `gpt` translator uses the translations and the one-line context; `google` ignores both. During music or silence, Whisper sometimes writes the glossary back as a line ("Niko, Takashi, Aya,"), or a line it learned from the ends of videos ("Thanks for watching"); such lines are dropped, and the run says how many.

### Resuming
Each video gets a work folder, `work/<video name>/`. Finished steps are remembered, so running again only does what is new:
- adding a language, or switching translator, only translates; the video is not transcribed again
- after a failure or interruption, the next run resumes where it stopped

```bash
subtitle my-video.mp4 --force              # redo everything
subtitle my-video.mp4 --force segment      # redo the subtitle lines and the translations, keep the transcript
subtitle my-video.mp4 --force translate    # redo only the translations
subtitle my-video.mp4 --clean              # delete the video's work and output folders
subtitle my-video.mp4 --verbose            # also show the libraries' own output
```
The steps are `extract`, `separate`, `transcribe`, `segment` and `translate`. `--force <step>` needs the steps before it to be finished and up to date: if one isn't (e.g. its files were deleted or its settings changed), it stops and says which, instead of quietly running it, since separation and transcription can take hours for a film.

The libraries' own output is always written to `work/<video name>/run.log`.

### Speech hidden by music or noise
With `--separate` (or `separate = true` in `config.toml`), [Demucs](https://github.com/adefossez/demucs) first separates the voices from the music and noise, and Whisper transcribes the voices alone. This recovers lines that background sound hides, but it costs more:
- a larger install: `pip install -e ".[separate]" -c constraints.txt`, and a model download on the first run
- a slower run: on an Apple Silicon CPU, a little over 1 s per second of video (49 s for a 42 s video), before transcription

Turning it on or off transcribes the video again. For about 4× faster separation at slightly lower quality, set `demucs_model = "htdemucs"`.

### Faster transcription on Apple Silicon
Set `asr_backend = "mlx"` in `config.toml` (or `ASR_BACKEND=mlx`). Word timing is the same: both backends align words with wav2vec2.

## Configuration
1. Copy `.env.example` to `.env` and fill in `OPENAI_API_KEY` (for `gpt`) or `GOOGLE_APPLICATION_CREDENTIALS` (the path to your key file, for `google`).
2. Optionally copy `config.example.toml` to `config.toml` and change settings there. Every setting is documented in that file.

Settings are resolved in this order, later ones winning: built-in defaults, `config.toml` (or `--config path`), environment variables / `.env` with the same name in upper case (e.g. `TRANSLATOR="google"`), command-line flags.

## First run
The models are downloaded the first time they are needed, each with a progress bar, then cached:
| Model | Size | Needed | Cache |
|---|---|---|---|
| Whisper `large-v3-turbo` | 1.6 GB | always | `~/.cache/huggingface` (`HF_HOME`) |
| wav2vec2 aligner, one per source language | 0.4 GB (en, fr, de, es, it) to 1.3 GB (ja) | always | `~/.cache/torch` (`TORCH_HOME`) for en, fr, de, es, it; `~/.cache/huggingface` for the others |
| Demucs `htdemucs_ft` | 0.3 GB | with `--separate` | `~/.cache/huggingface` |

For a Japanese video, the downloads added about 4 minutes at 12 MB/s. Later runs don't download.

## Troubleshooting
- **`ffmpeg and ffprobe not found on PATH`:** install ffmpeg (see [Quick start](#quick-start)), and check that `ffmpeg -version` works in the same terminal.
- **`the gpt translator needs OPENAI_API_KEY`** (or `GOOGLE_APPLICATION_CREDENTIALS` for `google`): set it in `.env`; see [Configuration](#configuration).
- **The first run is slow:** it downloads up to 3.2 GB of models; see [First run](#first-run).
- **Something failed:** the libraries' own output and the full error are in `work/<video name>/run.log`; `--verbose` also shows them on the console.
- **After updating the code:** run again with `--force`, or `--force segment` to keep the transcript. Finished steps are only redone when their settings change, not when the code does.
- **Lines are missing:** speech under music or noise may not be transcribed; try `--separate`.

## Known limitations
- Background noise or music can hide speech, so some lines are not transcribed; `--separate` helps.
- A subtitle shows at most 84 characters (2 lines of 42) for at most 7 s; longer lines are split between words. Translations keep each line's timing, so when a sentence spans two lines, word order can differ from the speech.
- Glossary names keep the glossary's spelling, so in a language with another script (e.g. Hindi) they stay in Latin letters.

## Development
```bash
pip install -e ".[dev]" -c constraints.txt
pytest
```
See [CONTRIBUTING.md](CONTRIBUTING.md) to send a change, and [ROADMAP.md](ROADMAP.md) for what is planned.

## License
MIT
