"""Opt-in, spaced YouTube caption requests and original-language track selection."""

import logging

import requests
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._transcripts import TranscriptList
from youtube_transcript_api._errors import (
    NoTranscriptFound, PoTokenRequired, RequestBlocked,
    TranscriptsDisabled, VideoUnplayable,
)

from catchup.net.host_spacing import HostSpacer
from catchup.net.safe_fetch import user_agent

logger = logging.getLogger(__name__)
api_factory = YouTubeTranscriptApi


class SpacedSession(requests.Session):
    def __init__(self, spacer: HostSpacer):
        super().__init__()
        self.trust_env = False
        self.spacer = spacer

    def request(self, method, url, **kwargs):
        headers = kwargs.pop("headers", {}) or {}
        kwargs["headers"] = {**headers, "User-Agent": user_agent()}
        kwargs.setdefault("timeout", (10, 30))
        return super().request(method, url, **kwargs)

    def send(self, request, **kwargs):
        self.spacer.wait(request.url)
        return super().send(request, **kwargs)


def _primary(language: str) -> str:
    return language.split("-", 1)[0].lower()


def _player_language(captions_json: dict) -> str | None:
    audio_tracks = captions_json.get("audioTracks")
    index = captions_json.get("defaultAudioTrackIndex")
    if not isinstance(audio_tracks, list) or type(index) is not int or not 0 <= index < len(audio_tracks):
        return None
    audio = audio_tracks[index]
    captions = captions_json.get("captionTracks")
    caption_index = audio.get("defaultCaptionTrackIndex")
    if (isinstance(captions, list) and type(caption_index) is int
            and 0 <= caption_index < len(captions)):
        language = captions[caption_index].get("languageCode")
        if isinstance(language, str) and language.strip():
            return language
    audio_id = audio.get("audioTrackId")
    if isinstance(audio_id, str):
        return audio_id.split(".", 1)[0] or None
    return None


def _inferred_language(tracks: list) -> str | None:
    manual = [track for track in tracks if not track.is_generated]
    auto = [track for track in tracks if track.is_generated]
    generated_languages = {_primary(track.language_code) for track in auto}
    match = next((track for track in manual if _primary(track.language_code) in generated_languages), None)
    if match is not None:
        return match.language_code
    if len(auto) == 1:
        return auto[0].language_code
    if len(manual) == 1:
        return manual[0].language_code
    return None


def choose_track(tracks, language: str):
    listed = list(tracks)
    primary = _primary(language)
    return next((track for track in listed if not track.is_generated
                 and _primary(track.language_code) == primary), None) or next(
                     (track for track in listed if track.is_generated
                      and _primary(track.language_code) == primary), None,
                 )


def _join_snippets(snippets) -> str:
    paragraphs: list[str] = []
    for snippet in snippets:
        if not isinstance(snippet.text, str) or not snippet.text.strip():
            continue
        text = snippet.text.strip()
        if not paragraphs or text.startswith(("- ", ">>")):
            paragraphs.append(text)
        else:
            paragraphs[-1] += " " + text
    return "\n\n".join(paragraphs)


def fetch_captions(video_id: str, spacer: HostSpacer) -> tuple[str, str | None]:
    try:
        with SpacedSession(spacer) as session:
            api = api_factory(http_client=session)
            captions_json = api._fetcher._fetch_captions_json(video_id)
            tracks = list(TranscriptList.build(api._fetcher._http_client, video_id, captions_json))
            if not tracks:
                return "caption_wait", None
            try:
                language = _player_language(captions_json)
            except Exception:
                language = None
            if not language:
                language = _inferred_language(tracks)
            if not language:
                return "captions_failed", None
            track = choose_track(tracks, language)
            if track is None:
                return "caption_wait", None
            snippets = track.fetch()
            text = _join_snippets(snippets)
            if not text:
                return "caption_wait", None
            return "found", text
    except (TranscriptsDisabled, NoTranscriptFound) as exc:
        logger.warning("Caption track unavailable for video %s (%s)", video_id, type(exc).__name__)
        return "caption_wait", None
    except VideoUnplayable as exc:
        logger.warning("Video not playable for captions %s (%s)", video_id, type(exc).__name__)
        return "unplayable_wait", None
    except (RequestBlocked, PoTokenRequired) as exc:
        logger.warning("Captions blocked for video %s (%s)", video_id, type(exc).__name__)
        return "blocked", None
    except Exception as exc:
        logger.warning("Caption fetch failed for video %s (%s)", video_id, type(exc).__name__)
        return "captions_failed", None
