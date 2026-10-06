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


def run_tracks(monkeypatch, tracks, captions=None):
    captions = captions if captions is not None else {"captionTracks": []}

    class Api:
        def __init__(self, http_client):
            assert http_client.trust_env is False
            self._fetcher = SimpleNamespace(
                _http_client=http_client, _fetch_captions_json=self.fetch_json,
            )

        def fetch_json(self, video_id):
            assert video_id == "abc"
            return captions

    monkeypatch.setattr("catchup.transcripts.youtube.api_factory", Api)
    def build(client, video_id, data):
        assert client.trust_env is False and video_id == "abc" and data is captions
        return tracks
    monkeypatch.setattr("catchup.transcripts.youtube.TranscriptList.build", build)
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


def test_dubbed_video_uses_default_audio_caption_index_not_track_order(monkeypatch):
    auto = [Track(language, True, language) for language in
            ("ar", "bg", "de", "el", "es", "fa", "fr", "hi", "id", "it", "ja", "ko", "nl", "pl",
             "pt", "ru", "sv", "th", "tr", "uk", "vi")]
    manual = Track("en", False, "Original English")
    captions = {
        "captionTracks": [{"languageCode": language} for language in
                          [track.language_code for track in auto[:3]] + ["en"] +
                          [track.language_code for track in auto[3:]]],
        "audioTracks": [
            {"audioTrackId": "ar.10", "defaultCaptionTrackIndex": 0},
            {"audioTrackId": "en-US.4", "defaultCaptionTrackIndex": 3},
            {"audioTrackId": "de.10", "defaultCaptionTrackIndex": 2},
        ],
        "defaultAudioTrackIndex": 1,
    }
    assert run_tracks(monkeypatch, [*auto, manual], captions) == ("found", "Original English")
    assert sum(track.calls for track in auto) == 0 and manual.calls == 1
    # Changing audioTracks order is harmless when the index changes with it.
    captions["audioTracks"].insert(0, captions["audioTracks"].pop(1))
    captions["defaultAudioTrackIndex"] = 0
    assert run_tracks(monkeypatch, [*auto, manual], captions) == ("found", "Original English")


def test_default_audio_language_when_caption_index_missing(monkeypatch):
    manual = Track("en", False, "English")
    auto = Track("en-GB", True, "Automatic English")
    captions = {"captionTracks": [{"languageCode": "ar"}, {"languageCode": "en"}],
                "audioTracks": [{"audioTrackId": "ar.10"}, {"audioTrackId": "en-US.4"}],
                "defaultAudioTrackIndex": 1}
    assert run_tracks(monkeypatch, [Track("ar", True, "Arabic"), auto, manual], captions) == (
        "found", "English",
    )
    assert manual.calls == 1 and auto.calls == 0


def test_no_audio_tracks_uses_manual_generated_language_overlap(monkeypatch):
    manual = Track("en-US", False, "Manual English")
    auto = Track("en", True, "Automatic English")
    assert run_tracks(monkeypatch, [Track("ar", True, "Arabic"), auto, manual]) == (
        "found", "Manual English",
    )
    assert manual.calls == 1


def test_undetermined_language_fails_without_fetch(monkeypatch):
    arabic, english = Track("ar", True, "Arabic"), Track("en", True, "English")
    assert run_tracks(monkeypatch, [arabic, english]) == ("captions_failed", None)
    assert arabic.calls == english.calls == 0


def test_invalid_metadata_falls_back_to_public_tracks(monkeypatch):
    captions = {"audioTracks": [None], "defaultAudioTrackIndex": 0}
    manual, generated = Track("en", False, "Manual"), Track("en-US", True, "Generated")
    assert run_tracks(monkeypatch, [manual, generated], captions) == ("found", "Manual")
    assert manual.calls == 1


def test_pinned_library_builds_tracks_from_faked_player_json(monkeypatch):
    captions = {
        "captionTracks": [
            {"languageCode": "ar", "kind": "asr", "baseUrl": "https://www.youtube.com/ar",
             "name": {"runs": [{"text": "Arabic"}]}},
            {"languageCode": "en", "baseUrl": "https://www.youtube.com/en",
             "name": {"runs": [{"text": "English"}]}},
        ],
        "audioTracks": [{"audioTrackId": "en-US.4", "defaultCaptionTrackIndex": 1}],
        "defaultAudioTrackIndex": 0,
    }
    fetched = []

    class Adapter(requests.adapters.BaseAdapter):
        def send(self, request, **kwargs):
            fetched.append((request.url, request.headers["User-Agent"], kwargs["timeout"]))
            response = requests.Response()
            response.status_code = 200
            response.url = request.url
            response._content = b'<transcript><text start="0" dur="1">Spoken English</text></transcript>'
            return response

        def close(self):
            pass

    class Api:
        def __init__(self, http_client):
            http_client.mount("https://", Adapter())
            self._fetcher = SimpleNamespace(
                _http_client=http_client, _fetch_captions_json=lambda video_id: captions,
            )

    monkeypatch.setattr("catchup.transcripts.youtube.api_factory", Api)
    spacer = Spacer()
    assert fetch_captions("abc", spacer) == ("found", "Spoken English")
    assert [url for url, _, _ in fetched] == ["https://www.youtube.com/en"]
    assert spacer.urls == ["https://www.youtube.com/en"]
    assert fetched[0][1].startswith("CatchUp/") and fetched[0][2] == (10, 30)


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
            self._fetcher = SimpleNamespace(_fetch_captions_json=self.fetch_json)

        def fetch_json(self, video_id):
            raise exception

    monkeypatch.setattr("catchup.transcripts.youtube.api_factory", Api)
    assert fetch_captions("abc", Spacer()) == (status, None)
    assert "abc" in caplog.text
    assert type(exception).__name__ in caplog.text
