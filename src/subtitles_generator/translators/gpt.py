import json
import os
from functools import cache
from textwrap import dedent

# Lines translated per request, and neighbouring lines sent with them as read-only context
BATCH_SIZE = 20
CONTEXT_LINES = 3
MAX_ATTEMPTS = 3

SYSTEM_PROMPT = dedent("""
    You translate video dialogue into {target} subtitles. Viewers read each line while it is on screen.

    Rules:
    - Return exactly one translation for every id in "lines", and nothing for the context lines.
    - "translation": a faithful, complete {target} translation of the line, in natural written {target}
      (never the original text). Keep the speaker's meaning and tone; leave out only filler sounds
      ("um", "uh") and stutters.
    - A line already in {target}, such as a song's lyrics, is copied unchanged.
    - Lines can be fragments of a sentence that continues in the next line. Keep each line's content in
      that line so the sequence reads naturally.
    - Use the glossary translations for names and terms.
    - Never merge, split, reorder or skip lines.
""").strip()

TRANSLATION_SCHEMA = {
    "name": "subtitle_translations",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "translations": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "translation": {"type": "string"},
                    },
                    "required": ["id", "translation"],
                    "additionalProperties": False,
                },
            },
        },
        "required": ["translations"],
        "additionalProperties": False,
    },
}


@cache
def _client():
    # created on first use, so OPENAI_API_KEY is only needed when this backend is selected.
    # LLM_BASE_URL points it at any OpenAI-compatible server, e.g. Ollama: http://localhost:11434/v1
    from openai import OpenAI
    base_url = os.getenv("LLM_BASE_URL") or None
    api_key = os.getenv("OPENAI_API_KEY") or ("unused" if base_url else None)
    return OpenAI(api_key=api_key, base_url=base_url)


def missing_credentials() -> str | None:
    """Why this backend can't run, or None, checked before the pipeline so a missing key fails fast."""
    if os.getenv("OPENAI_API_KEY") or os.getenv("LLM_BASE_URL"):
        return None
    return ("the gpt translator needs OPENAI_API_KEY: set it in .env (see .env.example), "
            "or set llm_base_url for a local OpenAI-compatible server")


def _model() -> str:
    return os.getenv("LLM_MODEL") or "gpt-5-mini"


def _complete(system: str, payload: dict, schema: dict) -> dict:
    response = _client().chat.completions.create(
        model=_model(),
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ],
        response_format={"type": "json_schema", "json_schema": schema},
    )
    choice = response.choices[0]
    if getattr(choice.message, "refusal", None):
        raise RuntimeError(f"Model refused the request: {choice.message.refusal}")
    if choice.finish_reason == "length":
        raise RuntimeError("Model response was cut off (finish_reason=length); lower BATCH_SIZE")
    return json.loads(choice.message.content)


def _line(item: dict) -> dict:
    return {"id": item["id"], "duration": item["duration"], "text": item["text"]}


def translate(items: list[dict], source_language: str, target_language: str,
              glossary: dict | None = None, context: str | None = None) -> dict[int, str]:
    """
    Translate items in batches with neighbouring lines as context, using structured JSON output.
    Every id is checked; ids missing from a reply are retried. Returns {id: translation}.
    """
    system = SYSTEM_PROMPT.format(target=target_language)
    results = {}
    for start in range(0, len(items), BATCH_SIZE):
        batch = items[start:start + BATCH_SIZE]
        before = items[max(0, start - CONTEXT_LINES):start]
        after = items[start + BATCH_SIZE:start + BATCH_SIZE + CONTEXT_LINES]

        pending = {item["id"]: item for item in batch}
        for attempt in range(1, MAX_ATTEMPTS + 1):
            payload = {
                "source_language": source_language,
                "target_language": target_language,
                "video_context": context or "",
                "glossary": glossary or {},
                "context_before": [i["text"] for i in before],
                "lines": [_line(item) for item in pending.values()],
                "context_after": [i["text"] for i in after],
            }
            reply = _complete(system, payload, TRANSLATION_SCHEMA)
            for t in reply["translations"]:
                if t["id"] in pending and t["translation"].strip():
                    results[t["id"]] = t["translation"].strip()
                    del pending[t["id"]]
            if not pending:
                break
            print(f"⚠️ Missing translations for ids {sorted(pending)} (attempt {attempt}/{MAX_ATTEMPTS})")
        if pending:
            raise RuntimeError(f"No translation returned for ids {sorted(pending)}")
    return results

