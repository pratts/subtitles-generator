import os
import tomllib

# Every pipeline setting: name -> (type, default). Names match the environment variables;
# in config.toml the same names are written in lower case.
# Secrets (OPENAI_API_KEY, GOOGLE_APPLICATION_CREDENTIALS) are read from the environment / .env only.
SETTINGS = {
    # languages
    "SOURCE_LANGUAGE": (str, ""),          # empty = detect
    "TARGET_LANGUAGES": (str, ""),         # comma-separated, e.g. "es,fr"; empty = source-language subtitles only
    # transcription
    "ASR_BACKEND": (str, "whisperx"),
    "WHISPER_MODEL": (str, "large-v3-turbo"),
    "ASR_DEVICE": (str, ""),
    # segmentation
    "SEGMENT_MIN_DURATION": (float, 1.5),
    "SEGMENT_MERGE_GAP": (float, 1.0),
    # translation
    "TRANSLATOR": (str, "gpt"),
    "GLOSSARY_FILE": (str, ""),
    "VIDEO_CONTEXT": (str, ""),
    "LLM_MODEL": (str, "gpt-5-mini"),
    "LLM_BASE_URL": (str, ""),
}

# Settings that translator backends read from the environment themselves
BACKEND_SETTINGS = ("LLM_MODEL", "LLM_BASE_URL")


def load_config(config_path: str | None = None, overrides: dict | None = None) -> dict:
    """
    Resolve every setting. Later sources win: defaults < config file < environment (.env) < overrides
    (command-line flags). config_path defaults to ./config.toml when it exists.
    """
    config = {name: default for name, (_, default) in SETTINGS.items()}

    path = config_path or ("config.toml" if os.path.exists("config.toml") else None)
    if path:
        with open(path, "rb") as f:
            file_values = tomllib.load(f)
        unknown = [k for k in file_values if k.upper() not in SETTINGS]
        if unknown:
            raise ValueError(f"Unknown settings in {path}: {', '.join(unknown)}")
        for key, value in file_values.items():
            config[key.upper()] = _convert(key.upper(), value)

    for name in SETTINGS:
        if os.getenv(name) not in (None, ""):
            config[name] = _convert(name, os.environ[name])

    for name, value in (overrides or {}).items():
        if value is not None:
            config[name] = _convert(name, value)

    config["TRANSLATOR"] = config["TRANSLATOR"].lower()
    for name in BACKEND_SETTINGS:
        if config[name]:
            os.environ[name] = str(config[name])
        else:
            os.environ.pop(name, None)
    return config


def _convert(name: str, value):
    kind, default = SETTINGS[name]
    if value is None or (isinstance(value, str) and value.strip() == ""):
        return default
    if kind is bool:
        return value if isinstance(value, bool) else str(value).strip().lower() not in ("false", "0", "no", "off")
    return kind(value)
