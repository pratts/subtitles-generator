import json

import httpx2 as httpx  # the HTTP client openai uses
import openai
import pytest

from subtitles_generator.translators import gpt
from subtitles_generator import translate as T


def segments_doc(n):
    return {"language": "ja", "duration": n * 2.0, "speakers": ["S"],
            "segments": [{"id": i, "speaker": "S", "start": i * 2.0, "end": i * 2.0 + 1.5, "duration": 1.5,
                          "gap_after": 0.5, "text": f"line {i}", "words": []} for i in range(n)]}


@pytest.fixture
def fake_openai(monkeypatch):
    """OpenAI client backed by a local handler; calls records every request body."""
    calls = []

    def install(reply):
        def handler(request):
            body = json.loads(request.content)
            calls.append(body)
            content = reply(json.loads(body["messages"][1]["content"]), len(calls))
            return httpx.Response(200, json={
                "id": "x", "object": "chat.completion", "created": 0, "model": body["model"],
                "choices": [{"index": 0, "finish_reason": "stop",
                             "message": {"role": "assistant", "content": json.dumps(content), "refusal": None}}]})
        client = openai.OpenAI(api_key="test", base_url="http://test/v1",
                               http_client=httpx.Client(transport=httpx.MockTransport(handler)))
        monkeypatch.setattr(gpt, "_client", lambda: client)
        return calls
    return install


def test_every_id_is_matched_and_missing_ids_are_retried(fake_openai, tmp_path, monkeypatch):
    monkeypatch.setattr(gpt, "BATCH_SIZE", 50)

    def reply(payload, call):
        ids = [line["id"] for line in payload["lines"]]
        out = [{"id": i, "translation": f"line {i} in English"} for i in ids]
        if call == 1:  # drop one id, blank one, add an unknown one, and shuffle
            out = [{**o, "translation": ""} if o["id"] == 5 else o for o in out if o["id"] != 3][::-1]
            out.append({"id": 999, "translation": "x"})
        return {"translations": out}

    calls = fake_openai(reply)
    doc = T.translate_segments(segments_doc(120), str(tmp_path / "t.json"), translator="gpt", target_language="en")
    assert [s["translation"] for s in doc["segments"]] == [f"line {i} in English" for i in range(120)]
    retried = [line["id"] for line in json.loads(calls[1]["messages"][1]["content"])["lines"]]
    assert retried == [3, 5]
    assert calls[0]["response_format"]["json_schema"]["strict"] is True


def test_gives_up_when_an_id_never_comes_back(fake_openai, tmp_path):
    fake_openai(lambda payload, call: {"translations": []})
    with pytest.raises(RuntimeError, match="No translation returned"):
        T.translate_segments(segments_doc(2), str(tmp_path / "t.json"), translator="gpt")


def test_subtitle_translation_is_kept_whole(fake_openai, tmp_path):
    # a faithful line much longer than a 1.5 s dubbing slot allowed: subtitles keep it, with no shortening request
    long = "I would really like to ask the people in this town what they honestly think about Japan."
    calls = fake_openai(lambda payload, call: {"translations": [{"id": 0, "translation": long}]})
    doc = T.translate_segments(segments_doc(1), str(tmp_path / "t.json"), translator="gpt")
    assert doc["segments"][0]["translation"] == long
    assert len(calls) == 1
    assert "subtitles" in calls[0]["messages"][0]["content"]
    assert json.loads(calls[0]["messages"][1]["content"])["lines"] == [{"id": 0, "duration": 1.5, "text": "line 0"}]


def test_google_batches_and_keeps_order(monkeypatch, tmp_path):
    from subtitles_generator.translators import google

    class FakeClient:
        def __init__(self):
            self.batches = []

        def translate(self, texts, source_language, target_language, format_):
            self.batches.append(len(texts))
            return [{"translatedText": t.upper()} for t in texts]

    client = FakeClient()
    monkeypatch.setattr(google, "_client", lambda: client)
    doc = T.translate_segments(segments_doc(300), str(tmp_path / "t.json"), translator="google")
    assert client.batches == [128, 128, 44]
    assert doc["segments"][299]["translation"] == "LINE 299"


def test_gpt_needs_a_key_unless_a_local_server_is_set(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("LLM_BASE_URL", raising=False)
    assert "OPENAI_API_KEY" in T.missing_credentials("gpt")
    monkeypatch.setenv("OPENAI_API_KEY", "")
    assert "OPENAI_API_KEY" in T.missing_credentials("gpt")
    monkeypatch.setenv("LLM_BASE_URL", "http://localhost:11434/v1")
    assert T.missing_credentials("gpt") is None
    monkeypatch.delenv("LLM_BASE_URL")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    assert T.missing_credentials("gpt") is None


def test_google_needs_its_credentials_variable(monkeypatch):
    monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS", raising=False)
    assert "GOOGLE_APPLICATION_CREDENTIALS" in T.missing_credentials("google")
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", "")
    assert "GOOGLE_APPLICATION_CREDENTIALS" in T.missing_credentials("google")
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", "key.json")
    assert T.missing_credentials("google") is None
