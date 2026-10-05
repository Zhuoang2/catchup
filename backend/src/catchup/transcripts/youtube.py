"""Opt-in, spaced YouTube caption requests and original-language track selection."""

import logging

import requests
from youtube_transcript_api import YouTubeTranscriptApi
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


def choose_track(tracks):
    listed = list(tracks)
    auto = next((track for track in listed if track.is_generated), None)
    if auto is not None:
        return next((track for track in listed
                     if not track.is_generated and track.language_code == auto.language_code), auto)
    return next((track for track in listed if not track.is_generated), None)


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
            tracks = api_factory(http_client=session).list(video_id)
            track = choose_track(tracks)
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
