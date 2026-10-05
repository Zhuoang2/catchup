"""Convert published transcript formats to readable spoken text."""

import json
import re
from html import unescape

from trafilatura import extract

from catchup.sources.feeds import plain_text

TIMING = re.compile(r"^\s*(?:\d{2,}:)?\d{2}:\d{2}[.,]\d{3}\s*-->")
SRT_START = re.compile(r"^\d+\r?\n\d{2,}:\d{2}:\d{2},\d{3}\s*-->", re.M)
VOICE = re.compile(r"<v(?:\.[^ >]+)?\s+([^>]+)>", re.I)
SPEAKER = re.compile(r"^([^:\n]{1,60}):\s*(.*)$", re.S)


def _merge_cues(cues: list[str], *, merge_unlabelled: bool = False) -> str:
    paragraphs: list[str] = []
    last_speaker = None
    for cue in cues:
        cue = cue.strip()
        if not cue:
            continue
        match = SPEAKER.match(cue)
        speaker = match[1] if match else None
        body = match[2] if match else cue
        if paragraphs and speaker == last_speaker and (speaker is not None or merge_unlabelled):
            paragraphs[-1] += " " + body
        else:
            paragraphs.append(cue)
        last_speaker = speaker
    return "\n\n".join(paragraphs)


def _timed_cues(text: str, *, vtt: bool) -> str:
    cues: list[str] = []
    for block in re.split(r"\n\s*\n", text.replace("\r\n", "\n").replace("\r", "\n")):
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if not lines:
            continue
        if vtt and lines[0].upper().startswith(("WEBVTT", "NOTE", "STYLE", "REGION")):
            continue
        index = next((i for i, line in enumerate(lines) if TIMING.match(line)), -1)
        if index == -1:
            continue
        spoken = "\n".join(lines[index + 1:])
        spoken = VOICE.sub(lambda m: f"{unescape(m[1].strip())}: ", spoken)
        spoken = unescape(re.sub(r"<[^>]+>", "", spoken)).strip()
        if spoken:
            cues.append(" ".join(spoken.splitlines()))
    return _merge_cues(cues)


def _json_segments(text: str) -> str:
    data = json.loads(text)
    if not isinstance(data, dict) or not isinstance(data.get("segments"), list):
        return ""
    cues = []
    for segment in data["segments"]:
        if not isinstance(segment, dict):
            continue
        body = segment.get("body")
        if isinstance(body, list):
            body = " ".join(str(part.get("body", "")) for part in body if isinstance(part, dict))
        if not isinstance(body, str) or not body.strip():
            continue
        speaker = segment.get("speaker")
        cues.append(f"{speaker}: {body.strip()}" if isinstance(speaker, str) and speaker.strip()
                    else body.strip())
    return _merge_cues(cues, merge_unlabelled=True)


def convert_transcript(body: bytes, declared_type: str | None = None) -> str | None:
    text = body.decode("utf-8-sig", errors="replace").strip()
    if not text:
        return None
    media_type = (declared_type or "").split(";", 1)[0].strip().lower()
    if media_type == "text/vtt":
        kind = "vtt"
    elif media_type in ("application/x-subrip", "application/srt"):
        kind = "srt"
    elif media_type == "application/json":
        kind = "json"
    elif media_type == "text/html":
        kind = "html"
    elif media_type == "text/plain":
        kind = "plain"
    elif text.startswith("WEBVTT"):
        kind = "vtt"
    elif SRT_START.search(text):
        kind = "srt"
    elif text.lstrip().startswith("{"):
        kind = "json"
    else:
        kind = "plain"
    if kind == "vtt":
        result = _timed_cues(text, vtt=True)
    elif kind == "srt":
        result = _timed_cues(text, vtt=False)
    elif kind == "json":
        result = _json_segments(text)
    elif kind == "html":
        result = extract(text) or plain_text(text)
    else:
        result = text
    return result.strip() or None
