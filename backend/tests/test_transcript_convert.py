from catchup.transcripts.convert import convert_transcript


VTT = b"""WEBVTT

NOTE skip this metadata
not spoken

00:00:01.000 --> 00:00:03.000
<v Alice>Hello there.</v>

2
00:00:04.000 --> 00:00:05.000
<v Alice>More words.</v>

STYLE
::cue { color: red; }

00:00:06.000 --> 00:00:07.000
<v Bob>Reply.</v>
"""
SRT = b"""1
00:00:01,000 --> 00:00:03,000
Alice: Hello there.

2
00:00:04,000 --> 00:00:05,000
Alice: More words.

3
00:00:06,000 --> 00:00:07,000
Bob: Reply.
"""


def test_vtt_preserves_speakers_and_drops_timing_and_blocks():
    assert convert_transcript(VTT, "text/vtt") == "Alice: Hello there. More words.\n\nBob: Reply."


def test_srt_sniffs_bom_and_ignores_server_type():
    assert convert_transcript(b"\xef\xbb\xbf" + SRT) == "Alice: Hello there. More words.\n\nBob: Reply."
    assert convert_transcript(SRT, "application/srt") == "Alice: Hello there. More words.\n\nBob: Reply."


def test_json_merges_words_and_speakers_with_string_start_times():
    body = b'''{"segments":[{"startTime":"1.0","speaker":"Alice","body":"Hello"},
    {"startTime":"1.1","speaker":"Alice","body":"world"},
    {"startTime":"2.0","speaker":"Bob","body":[{"body":"More"},{"body":"words"}]}]}'''
    assert convert_transcript(body, "application/json") == "Alice: Hello world\n\nBob: More words"


def test_html_and_plain_text():
    assert "Spoken words" in (convert_transcript(
        b"<html><body><main><p>Spoken words from the episode.</p></main></body></html>", "text/html",
    ) or "")
    assert convert_transcript(b"  Raw spoken words  ", "text/plain") == "Raw spoken words"
    assert convert_transcript(b"\xef\xbb\xbf  ") is None
    assert convert_transcript(b'{"segments": []}') is None
