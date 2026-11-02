import importlib
import json
import os

TRANSLATORS = {"gpt": "subtitles_generator.translators.gpt", "google": "subtitles_generator.translators.google"}


def get_translator(name: str):
    """Import the translator backend on demand, so unused backends need no credentials or packages."""
    name = name.lower()
    if name not in TRANSLATORS:
        raise ValueError(f"Unknown translator: {name}. Use one of: {', '.join(TRANSLATORS)}.")
    return importlib.import_module(TRANSLATORS[name])


def missing_credentials(name: str) -> str | None:
    return get_translator(name).missing_credentials()


def load_glossary(path: str | None) -> dict:
    """Glossary JSON: {"source term": "translation"}, e.g. names that must be kept consistent."""
    if not path:
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# === Step 4: Translate subtitle segments ===
def translate_segments(segments_doc: dict, translation_output_path: str, translator: str = "google",
                       target_language: str = "en", glossary: dict | None = None,
                       context: str | None = None) -> dict:
    """Translate every segment into the target language and save the result as JSON."""
    source_language = segments_doc["language"]
    items = [{"id": s["id"], "duration": s["duration"], "text": s["text"]} for s in segments_doc["segments"]]

    backend = get_translator(translator)
    print(f"🔤 Translating {len(items)} segments {source_language} → {target_language} with {translator}...")
    results = backend.translate(items, source_language, target_language, glossary=glossary, context=context) \
        if items else {}

    missing = [item["id"] for item in items if item["id"] not in results]
    if missing:
        raise RuntimeError(f"Translator returned no translation for segment ids {missing}")

    segments = [{"id": seg["id"], "speaker": seg["speaker"], "start": seg["start"], "end": seg["end"],
                 "duration": seg["duration"], "gap_after": seg["gap_after"], "source_text": seg["text"],
                 "translation": results[seg["id"]]} for seg in segments_doc["segments"]]
    document = {
        "source_language": source_language,
        "target_language": target_language,
        "translator": translator,
        "duration": segments_doc.get("duration"),
        "speakers": segments_doc.get("speakers", []),
        "glossary": glossary or {},
        "context": context or "",
        "segments": segments,
    }
    os.makedirs(os.path.dirname(translation_output_path), exist_ok=True)
    with open(translation_output_path, "w", encoding="utf-8") as f:
        json.dump(document, f, ensure_ascii=False, indent=2)
    print(f"✅ Saved {len(segments)} translations to {translation_output_path}")
    return document
