import argparse
import json
import os
import shutil
import sys
from dotenv import load_dotenv

# Load .env before importing the pipeline modules, so secrets and settings are available when they load
load_dotenv()

from subtitles_generator import output
from subtitles_generator.config import load_config
from subtitles_generator.pipeline import Pipeline, Stage, file_id
from subtitles_generator.subtitles import subtitles_path, write_subtitles

# Each stage imports its own modules when it runs, so --help, --clean and skipped stages
# do not load the heavy model libraries


def read_json(path: str):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


class Run:
    """Paths and settings for subtitling one video. Everything for the video lives in <work_dir>/<video name>/."""

    def __init__(self, video: str, config: dict, work_root: str = "work", output_dir: str = "output"):
        self.video = os.path.abspath(video)
        self.config = config
        self.name = os.path.splitext(os.path.basename(video))[0]
        self.work_dir = os.path.abspath(os.path.join(work_root, self.name))
        self.output_dir = os.path.abspath(output_dir)
        w = lambda *p: os.path.join(self.work_dir, *p)

        self.metadata = w("metadata.json")
        self.source_audio = w("source-audio.wav")
        self.vocals = w("separation", "vocals.wav")
        self.background = w("separation", "background.wav")
        self.transcript = w("transcript.json")
        self.transcript_srt = w("transcript.srt")
        self.segments = w("segments.json")
        self.segments_srt = w("segments.srt")
        # each translator has its own folder, with one translation per target language
        self.translation_dir = w("translations", config["TRANSLATOR"])

    def duration(self) -> float:
        return read_json(self.metadata)["duration"]

    def target(self) -> str:
        return self.config["TARGET_LANGUAGE"]

    def translation(self) -> str:
        return os.path.join(self.translation_dir, f"{self.target()}.json")

    def source_subtitles(self) -> str:
        language = read_json(self.transcript)["language"] if os.path.exists(self.transcript) else "unknown"
        return subtitles_path(self.video, language, self.output_dir)

    def target_subtitles(self) -> str:
        return subtitles_path(self.video, self.target(), self.output_dir)


# === Stages ===
def extract(run: Run):
    from subtitles_generator.media import extract_audio, probe_media
    from subtitles_generator.transcribe import ASR_SAMPLE_RATE
    probe_media(run.video, run.metadata)
    extract_audio(run.video, run.source_audio, sample_rate=ASR_SAMPLE_RATE, mono=True)


def separate(run: Run):
    try:
        from subtitles_generator.separate import separate_vocals
    except ModuleNotFoundError as e:
        if (e.name or "").split(".")[0] != "demucs":
            raise
        raise SystemExit('separate = true needs Demucs: pip install -e ".[separate]" -c constraints.txt') from None
    separate_vocals(run.source_audio, run.vocals, run.background, model=run.config["DEMUCS_MODEL"])


def transcribe_stage(run: Run):
    from subtitles_generator.transcribe import transcribe
    c = run.config
    audio = run.vocals if c["SEPARATE"] else run.source_audio
    transcribe(audio, run.transcript, run.transcript_srt, backend=c["ASR_BACKEND"],
               model_name=c["WHISPER_MODEL"], language=c["SOURCE_LANGUAGE"] or None, device=c["ASR_DEVICE"] or None,
               glossary=c["GLOSSARY"])


def segment(run: Run):
    from subtitles_generator.segment import build_segments, save_segments
    # no diarization: every word gets the same speaker
    segments = build_segments(read_json(run.transcript), [], run.duration(),
                              min_duration=run.config["SEGMENT_MIN_DURATION"],
                              merge_gap=run.config["SEGMENT_MERGE_GAP"])
    save_segments(segments, run.segments, run.segments_srt)


def translate(run: Run):
    from subtitles_generator.translate import translate_segments
    c = run.config
    base = os.path.join(run.translation_dir, run.target())
    translate_segments(read_json(run.segments), run.translation(), f"{base}.raw.srt", f"{base}.polished.srt",
                       translator=c["TRANSLATOR"], target_language=run.target(), glossary=c["GLOSSARY"],
                       context=c["VIDEO_CONTEXT"] or None)


STAGES = [
    Stage("extract", "reading video metadata and extracting the audio", extract,
          lambda r: [r.metadata, r.source_audio]),
    # only with SEPARATE
    Stage("separate", "separating vocals from background", separate,
          lambda r: [r.vocals, r.background], ["DEMUCS_MODEL"]),
    Stage("transcribe", "transcribing the audio", transcribe_stage,
          lambda r: [r.transcript], ["SEPARATE", "ASR_BACKEND", "WHISPER_MODEL", "SOURCE_LANGUAGE", "GLOSSARY"]),
    Stage("segment", "building subtitle segments", segment, lambda r: [r.segments],
          ["SEGMENT_MIN_DURATION", "SEGMENT_MERGE_GAP"]),
    Stage("translate", "translating the segments", translate, lambda r: [r.translation()],
          ["TRANSLATOR", "TARGET_LANGUAGE", "GLOSSARY", "VIDEO_CONTEXT", "LLM_MODEL", "LLM_BASE_URL"],
          per_translator=True),
]


def target_languages(value: str) -> list[str]:
    """"es, fr,es" -> ["es", "fr"]"""
    languages = []
    for language in value.split(","):
        language = language.strip()
        if language and language not in languages:
            languages.append(language)
    return languages


def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(
        description="Make subtitles for a video in its own language and, translated, in others. Finished stages "
                    "are remembered, so re-running resumes where it stopped and only redoes stages whose settings "
                    "changed (e.g. adding a language only translates).")
    parser.add_argument("input", help="path to the video")
    parser.add_argument("--to", help="target languages, comma-separated, e.g. es,fr,hi")
    parser.add_argument("--from", dest="source", help="source language code (default: detect)")
    parser.add_argument("--translator", choices=["gpt", "google"], help="translation backend (default: gpt)")
    parser.add_argument("--separate", action="store_true", default=None,
                        help="transcribe vocals separated from music and noise (needs the [separate] extra; slower)")
    parser.add_argument("--glossary", help='JSON file {"source term": "translation"} of names and terms')
    parser.add_argument("--context", help="one-line description of the video (used by gpt)")
    parser.add_argument("--config", help="settings file (default: ./config.toml if present)")
    parser.add_argument("--work-dir", default="work", help="folder for intermediate files (default: work)")
    parser.add_argument("--output-dir", default="output", help="folder for the subtitles (default: output)")
    parser.add_argument("--force", action="store_true", help="re-run every stage")
    parser.add_argument("--clean", action="store_true", help="delete this video's work folder and exit")
    parser.add_argument("--verbose", action="store_true",
                        help="also show third-party output (always written to <work folder>/run.log)")
    args = parser.parse_args(argv)

    if not os.path.exists(args.input):
        parser.error(f"input video not found: {args.input}")
    config = load_config(args.config, {"SOURCE_LANGUAGE": args.source, "TARGET_LANGUAGES": args.to,
                                       "TRANSLATOR": args.translator, "SEPARATE": args.separate,
                                       "GLOSSARY_FILE": args.glossary,
                                       "VIDEO_CONTEXT": args.context})
    # the glossary's content, not its path, decides whether transcription and translation must run again
    from subtitles_generator.translate import load_glossary
    config["GLOSSARY"] = load_glossary(config["GLOSSARY_FILE"] or None)
    run = Run(args.input, config, args.work_dir, args.output_dir)

    if args.clean:
        if os.path.exists(run.work_dir):
            shutil.rmtree(run.work_dir)
            print(f"🧹 Deleted {run.work_dir}")
        else:
            print(f"Nothing to delete: {run.work_dir} does not exist")
        return

    os.makedirs(run.work_dir, exist_ok=True)
    restore = output.setup(os.path.join(run.work_dir, "run.log"), verbose=args.verbose)
    try:
        subtitle(run, config, args)
    except BaseException:
        output.log_exception()
        raise
    finally:
        restore()


def subtitle(run: Run, config: dict, args):
    targets = target_languages(config["TARGET_LANGUAGES"])
    languages = f" → {', '.join(targets)}" if targets else ""
    print(f"🎬 Subtitling {run.video}{languages} "
          f"(translator: {config['TRANSLATOR']}); work folder: {run.work_dir}")
    inputs_id = file_id(run.video)
    stages = [s for s in STAGES if s.name != "separate" or config["SEPARATE"]]
    if not targets:
        Pipeline(stages, run.work_dir, config["TRANSLATOR"]).run(run, config, to_stage="segment", force=args.force,
                                                                  inputs_id=inputs_id)
    # one pass per language: the stages before translate are shared, so later passes skip them
    for i, target in enumerate(targets):
        config["TARGET_LANGUAGE"] = target
        print(f"🌐 {target}")
        pipeline = Pipeline(stages, run.work_dir, f"{config['TRANSLATOR']}:{target}")
        # --force re-runs everything once, then only translation for the other languages
        pipeline.run(run, config, force=args.force and i == 0,
                     from_stage="translate" if args.force and i > 0 else None, inputs_id=inputs_id)
    # written from the work files on every run, since output/ holds one file per language whichever translator
    # made it: a skipped translate stage must still replace another translator's file
    written = [write_subtitles(read_json(run.segments), "text", run.source_subtitles())]
    for target in targets:
        config["TARGET_LANGUAGE"] = target
        written.append(write_subtitles(read_json(run.translation()), "translation", run.target_subtitles()))
    print(f"🎉 Done: {', '.join(written)}")


if __name__ == "__main__":
    sys.exit(main())
