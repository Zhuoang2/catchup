from types import SimpleNamespace

import pytest
import requests
from youtube_transcript_api import _errors as errors

from catchup.transcripts.youtube import SpacedSession, _join_snippets, fetch_captions


class Spacer:
    def __init__(self):
        self.urls = []

    def wait(self, url):
        self.urls.append(url)


def test_caption_snippets_join_until_speaker_marker():
    snippets = [SimpleNamespace(text=text) for text in ("First", "second", "- Alice", "speaks", ">> Bob", "replies")]
    assert _join_snippets(snippets) == "First second\n\n- Alice speaks\n\n>> Bob replies"


def test_session_spaces_each_request_and_disables_environment(monkeypatch):
    events = []

    class Adapter(requests.adapters.BaseAdapter):
        def send(self, request, **kwargs):
            events.append(("send", request.url, request.headers["User-Agent"], kwargs["timeout"]))
            response = requests.Response()
            response.status_code = 200
            response.url = request.url
            response._content = b"ok"
            return response

        def close(self):
            pass

    class Recorder(Spacer):
        def wait(self, url):
            events.append(("wait", url))

    with SpacedSession(Recorder()) as session:
        session.mount("https://", Adapter())
        assert session.trust_env is False
        for _ in range(2):
            assert session.get("https://www.youtube.com/watch?v=abc").text == "ok"
    assert [event[0] for event in events] == ["wait", "send", "wait", "send"]
    assert all(event[2].startswith("CatchUp/") and event[3] == (10, 30)
               for event in events if event[0] == "send")


def test_session_spaces_redirect_hops():
    events = []

    class Adapter(requests.adapters.BaseAdapter):
        def send(self, request, **kwargs):
            events.append(("send", request.url))
            response = requests.Response()
            response.status_code = 302 if len(events) == 2 else 200
            response.url = request.url
            response.request = request
            if response.status_code == 302:
                response.headers["Location"] = "/final"
            response._content = b"ok"
            return response

        def close(self):
            pass

    class Recorder(Spacer):
        def wait(self, url):
            events.append(("wait", url))

    with SpacedSession(Recorder()) as session:
        session.mount("https://", Adapter())
        assert session.get("https://www.youtube.com/start").text == "ok"
    assert events == [
        ("wait", "https://www.youtube.com/start"), ("send", "https://www.youtube.com/start"),
        ("wait", "https://www.youtube.com/final"), ("send", "https://www.youtube.com/final"),
    ]


class Track:
    def __init__(self, language, generated, text):
        self.language_code = language
        self.is_generated = generated
        self.text = text
        self.calls = 0

    def fetch(self):
        self.calls += 1
        return [SimpleNamespace(text=self.text)]

    def translate(self, *_args):
        pytest.fail("translated tracks must not be requested")


def run_tracks(monkeypatch, tracks):
    class Api:
        def __init__(self, http_client):
            assert http_client.trust_env is False

        def list(self, video_id):
            assert video_id == "abc"
            return tracks

    monkeypatch.setattr("catchup.transcripts.youtube.api_factory", Api)
    return fetch_captions("abc", Spacer())


def test_manual_track_in_original_auto_language_preferred(monkeypatch):
    other = Track("zh", False, "Translated")
    auto = Track("en", True, "Automatic English")
    manual = Track("en", False, "Manual English")
    assert run_tracks(monkeypatch, [other, auto, manual]) == ("found", "Manual English")
    assert [t.calls for t in (other, auto, manual)] == [0, 0, 1]


def test_different_digest_language_does_not_change_track(monkeypatch):
    auto = Track("en", True, "English")
    manual = Track("zh", False, "Chinese subtitles")
    assert run_tracks(monkeypatch, [manual, auto]) == ("found", "English")
    assert manual.calls == 0 and auto.calls == 1


def test_only_manual_track_fallback_and_no_track(monkeypatch):
    manual = Track("es", False, "Spoken Spanish")
    assert run_tracks(monkeypatch, [manual]) == ("found", "Spoken Spanish")
    assert run_tracks(monkeypatch, []) == ("caption_wait", None)


@pytest.mark.parametrize("exception,status", [
    (errors.TranscriptsDisabled("abc"), "caption_wait"),
    (errors.NoTranscriptFound("abc", ["en"], None), "caption_wait"),
    (errors.VideoUnplayable("abc", None, []), "unplayable_wait"),
    (errors.RequestBlocked("abc"), "blocked"),
    (errors.IpBlocked("abc"), "blocked"),
    (errors.PoTokenRequired("abc"), "blocked"),
    (errors.VideoUnavailable("abc"), "captions_failed"),
    (errors.AgeRestricted("abc"), "captions_failed"),
    (KeyError("missing tracks"), "captions_failed"),
])
def test_exception_mapping_without_logging_content(monkeypatch, caplog, exception, status):
    class Api:
        def __init__(self, http_client):
            pass

        def list(self, video_id):
            raise exception

    monkeypatch.setattr("catchup.transcripts.youtube.api_factory", Api)
    assert fetch_captions("abc", Spacer()) == (status, None)
    assert "abc" in caplog.text
    assert type(exception).__name__ in caplog.text
