# subtitles-generator
Subtitles for any video, in any language.

`subtitle video.mp4 --to es,fr` transcribes the video with Whisper, times every word, and writes `.srt` subtitles in the video's own language and in each language you ask for.

## Prerequisites
- Python 3.11 or higher
- ffmpeg and ffprobe on your `PATH` (`brew install ffmpeg`, or `apt install ffmpeg`)
- For translation, one of:
  - `gpt` (default): an [OpenAI API key](https://platform.openai.com/api-keys), or a local OpenAI-compatible server such as [Ollama](https://ollama.com)
  - `google`: a Google Cloud project with the Cloud Translation API enabled, and a service account JSON key

No key is needed for subtitles in the video's own language.

## Installation
```bash
git clone git@github.com:pratts/subtitles-generator.git
cd subtitles-generator
python3.12 -m venv venv          # any Python 3.11 or higher
source venv/bin/activate
pip install -e . -c constraints.txt
```
`constraints.txt` holds the versions tested together. The install is large (PyTorch and WhisperX), and the Whisper and alignment models are downloaded on the first run.

## Configuration
1. Copy `.env.example` to `.env` and fill in `OPENAI_API_KEY` (for `gpt`) or `GOOGLE_APPLICATION_CREDENTIALS` (the path to your key file, for `google`).
2. Optionally copy `config.example.toml` to `config.toml` and change settings there. Every setting is documented in that file.

Settings are resolved in this order, later ones winning: built-in defaults, `config.toml` (or `--config path`), environment variables / `.env` with the same name in upper case (e.g. `TRANSLATOR="google"`), command-line flags.

## Usage
```bash
subtitle my-video.mp4                          # subtitles in the video's own language
subtitle my-video.mp4 --to es,fr,hi            # ... and in Spanish, French and Hindi
subtitle my-video.mp4 --to en --from ja        # skip language detection
subtitle my-video.mp4 --to en --translator google
```
Subtitles are written to `output/<video name>.<language>.srt`, e.g. `output/my-video.ja.srt` and `output/my-video.en.srt`.

### Names and context
Whisper and translators often misspell names. A glossary fixes that:
```json
{"熊谷真奈": "Mana Kumagai", "仙台": "Sendai"}
```
```bash
subtitle my-video.mp4 --to en --glossary glossary.json --context "Street interview in Sendai about life in Japan"
```
The glossary's source terms are given to Whisper so it spells them as written; with a Japanese or Chinese glossary this also makes Whisper add punctuation, which gives better line breaks. The `gpt` translator uses the translations and the one-line context; `google` ignores both.

### Resuming
Each video gets a work folder, `work/<video name>/`. Finished steps are remembered, so running again only does what is new:
- adding a language, or switching translator, only translates; the video is not transcribed again
- after a failure or interruption, the next run resumes where it stopped

```bash
subtitle my-video.mp4 --force      # redo everything
subtitle my-video.mp4 --clean      # delete the video's work folder
subtitle my-video.mp4 --verbose    # also show the libraries' own output
```
The libraries' own output is always written to `work/<video name>/run.log`. Run `subtitle --help` for all options.

### Faster transcription on Apple Silicon
Set `asr_backend = "mlx"` in `config.toml` (or `ASR_BACKEND=mlx`). Word timing is the same: both backends align words with wav2vec2.

## Known limitations
- Background noise or music can hide speech, so some lines are not transcribed.
- A subtitle shows at most 84 characters (2 lines of 42) for at most 7 s; longer lines are split between words. Translations keep each line's timing, so when a sentence spans two lines, word order can differ from the speech.

## Development
```bash
pip install -e ".[dev]" -c constraints.txt
pytest
```

## License
MIT
