# Spec Delta

## Purpose

Lets the user follow Bilibili uploaders (UP 主) as sources, read through an RSSHub instance that the instance's operator runs and configures. CatchUp itself never contacts Bilibili, and summarizes videos only from the subtitles RSSHub provides.

## ADDED Requirements

### Requirement: Recognize Bilibili uploader addresses
The system SHALL treat a pasted address as a Bilibili uploader address, before looking for any feed, when it is one of these:
- `space.bilibili.com/<mid>`, over HTTP or HTTPS, with or without a further path (such as `/video` or `/upload/video`), a query, or a fragment;
- `m.bilibili.com/space/<mid>`;
- the configured RSSHub address followed by `/bilibili/user/video/<mid>`, with or without one more path segment and a query.

`<mid>` is the uploader's numeric id: 1 to 20 digits. Host names ignore letter case and a trailing dot.

Every other address on a Bilibili host is not an uploader address, and the system MUST report "not a Bilibili uploader" for it, with the message "Paste the uploader's space address, such as https://space.bilibili.com/2267573.". This includes video pages, `b23.tv` short links, other Bilibili pages, and space addresses whose id is not numeric. Bilibili hosts are `bilibili.com`, `b23.tv`, `hdslb.com`, and `bilivideo.com`, with any subdomain. Recognizing or refusing an address MUST NOT make any request.

#### Scenario: Space address
- **WHEN** the user pastes `https://space.bilibili.com/2267573/video?tid=0`
- **THEN** the system treats it as the uploader `2267573`, and requests nothing from Bilibili

#### Scenario: Mobile space address
- **WHEN** the user pastes `https://m.bilibili.com/space/2267573`
- **THEN** the system treats it as the uploader `2267573`

#### Scenario: RSSHub route address
- **WHEN** RSSHub is configured at `http://rsshub:1200`, and the user pastes `http://rsshub:1200/bilibili/user/video/2267573?format=json`
- **THEN** the system treats it as the uploader `2267573`

#### Scenario: Video page
- **WHEN** the user pastes `https://www.bilibili.com/video/BV1xx411c7mD`
- **THEN** the system reports that the address is not a Bilibili uploader, asks for the space address, requests nothing, and saves nothing

#### Scenario: Short link
- **WHEN** the user pastes `https://b23.tv/abc123`
- **THEN** the system reports that the address is not a Bilibili uploader, and does not resolve the short link

### Requirement: Read uploaders through the RSSHub address the operator sets
The instance SHALL read Bilibili uploaders only through the RSSHub address set in its environment as `CATCHUP_RSSHUB_URL`. The address MUST be an HTTP or HTTPS URL with a host. A path prefix is allowed. It MUST NOT have a user name, password, query, or fragment. An invalid address MUST stop the instance from starting, with a message that names `CATCHUP_RSSHUB_URL`. A trailing `/` is ignored.

For an uploader, the system SHALL request `<address>/bilibili/user/video/<mid>?format=json` and read the answer as JSON Feed. The request MUST carry CatchUp's User-Agent, use the feed size limit, and follow the run's per-host spacing.

The configured address's origin (scheme, host, and port) is the only origin allowed to resolve to a private or loopback address, and only for these uploader requests. A redirect from it MUST be checked like any other address, so a redirect to a private or loopback address is refused, including one back to the same origin. The same host on another port, and any other private or loopback address, MUST still be refused.

When no address is set, a pasted Bilibili uploader address MUST be refused with "Following Bilibili uploaders needs an RSSHub address (CATCHUP_RSSHUB_URL). See the README.", and a check of a saved Bilibili source MUST fail with the same message. Other Bilibili addresses are still reported as not a Bilibili uploader.

#### Scenario: RSSHub next to CatchUp in Docker
- **WHEN** `CATCHUP_RSSHUB_URL` is `http://rsshub:1200`, and `rsshub` resolves to a private Docker network address
- **THEN** the uploader request connects to that address

#### Scenario: Redirect from RSSHub to a private address
- **WHEN** the configured RSSHub answers an uploader request with a redirect to `http://10.0.0.5/feed`
- **THEN** the system does not follow it, and reports that the address is not allowed

#### Scenario: Same host on another port
- **WHEN** RSSHub is configured at `http://localhost:1200`, and the user pastes `http://localhost:8080/feed`
- **THEN** the system refuses it as an address that is not allowed

#### Scenario: No RSSHub address
- **WHEN** no RSSHub address is set, and the user pastes `https://space.bilibili.com/2267573`
- **THEN** the system says that following Bilibili uploaders needs an RSSHub address, and requests nothing

#### Scenario: Invalid RSSHub address
- **WHEN** `CATCHUP_RSSHUB_URL` is `ftp://rsshub:1200`
- **THEN** the instance does not start, and the message names `CATCHUP_RSSHUB_URL`

### Requirement: Preview and follow a Bilibili uploader
The preview of an uploader SHALL show:
- the uploader's name: RSSHub's feed title without its ` 的 bilibili 空间` ending;
- the uploader's space address `https://space.bilibili.com/<mid>`;
- the kind "Bilibili uploader";
- that videos are summarized from subtitles read through the user's RSSHub, and that videos without subtitles are listed without a summary;
- up to five recent videos (title, link, and publish date).

Confirming SHALL save the source with the stable address `bilibili:uploader:<mid>`, so a new RSSHub address keeps the source. An uploader that is already followed MUST be reported as a duplicate, whichever form of its address was pasted. The first-add rules for website feeds apply: only videos published within the first-add window are new, at most the first-add maximum.

When RSSHub answers with an HTTP error, or with something that is not a JSON Feed, the preview MUST report "RSSHub could not read this uploader.", with the HTTP status when there is one, and save nothing. A rate-limit answer (HTTP 429, or 503 with Retry-After) is reported as rate limiting instead, as for other sources, and also saves nothing.

#### Scenario: Preview an uploader
- **WHEN** the user pastes `https://space.bilibili.com/2267573`, and RSSHub answers with the feed `Sample Uploader 的 bilibili 空间` and 30 videos
- **THEN** the preview shows "Sample Uploader", `https://space.bilibili.com/2267573`, "Bilibili uploader", and the five most recent videos

#### Scenario: Already followed through another address form
- **WHEN** the uploader `2267573` is followed, and the user pastes `https://m.bilibili.com/space/2267573`
- **THEN** the system reports that the uploader is already followed, and saves nothing

#### Scenario: RSSHub fails for the uploader
- **WHEN** RSSHub answers the uploader request with HTTP 503
- **THEN** the preview reports that RSSHub could not read this uploader (HTTP 503), and saves nothing

### Requirement: Summarize Bilibili videos only from RSSHub's subtitles
Each run SHALL check every followed uploader through RSSHub, and record videos it has not seen before, like website feed entries.

A video's subtitles SHALL come only from the JSON Feed's attachments of type `text/srt` whose address is a `data:` URL. The system decodes the first such attachment locally and reads it as SRT. It MUST NOT request any attachment address.

A video with subtitles SHALL be summarized from the subtitle text. A video without subtitles SHALL wait for the caption wait (`CATCHUP_CAPTION_WAIT_HOURS`, default 24 hours) from when it was first recorded. Each run's check reads it again, and it is summarized once subtitles appear. When the wait ends without subtitles, it goes to Creator updates with the reason "no subtitles from RSSHub". A Bilibili video MUST NOT be summarized from its title or description, and MUST NOT get linked pages, comment context, or image candidates.

#### Scenario: Video with subtitles
- **WHEN** a new video's JSON Feed item has a `text/srt` attachment `data:text/plain;charset=utf-8,1%0A00%3A00%3A01%2C000%20--%3E%2000%3A00%3A04%2C000%0AHello`
- **THEN** the video is summarized from the text "Hello"

#### Scenario: Subtitles appear later
- **WHEN** a video had no subtitles when first recorded, and a check 3 hours later finds a subtitle attachment
- **THEN** the video is summarized from those subtitles in that run

#### Scenario: Subtitle wait ends
- **WHEN** a video still has no subtitles 24 hours after it was first recorded
- **THEN** the next saved digest lists it under Creator updates with the reason "no subtitles from RSSHub", and no model call is made for it

#### Scenario: Attachment with a web address
- **WHEN** a video's only `text/srt` attachment has the address `https://www.bilibili.com/sub.srt`
- **THEN** nothing is requested, and the video waits like a video without subtitles

### Requirement: Never request Bilibili hosts
The system MUST NOT request any address on a Bilibili host (`bilibili.com`, `b23.tv`, `hdslb.com`, or `bilivideo.com`, with any subdomain, ignoring letter case and a trailing dot), for any source and in any stage: as a feed, a probe, an article page, a linked page, a transcript, or a redirect target. Such an address MUST be refused before its host name is looked up. Links to Bilibili hosts MUST NOT be chosen as related links.

#### Scenario: Website entry that links to a Bilibili video
- **WHEN** a website feed's short entry links only to `https://www.bilibili.com/video/BV1xx411c7mD`
- **THEN** that page is not requested, and the entry is summarized from its feed text

#### Scenario: Redirect to Bilibili
- **WHEN** a linked page redirects to `https://www.bilibili.com/video/BV1xx411c7mD`
- **THEN** the system does not request bilibili.com

#### Scenario: A whole run with a Bilibili uploader
- **WHEN** a run checks a followed uploader, summarizes one of its videos, and lists another under Creator updates
- **THEN** no request in the run goes to a Bilibili host

### Requirement: Show Bilibili uploaders by their space address
Wherever a saved Bilibili source or its preview is shown, the system SHALL name its kind "Bilibili uploader", and show the space address `https://space.bilibili.com/<mid>` in place of the internal `bilibili:uploader:<mid>` address. This applies to the Sources page, its preview, and the browser extension's popup. The Sources page preview MUST say that Bilibili's user agreement does not allow automated access, and that the user's RSSHub makes those requests. Home's count of sources by kind SHALL include Bilibili uploaders when there is at least one.

#### Scenario: Sources row
- **WHEN** the uploader `2267573` is followed
- **THEN** its row on the Sources page shows "Bilibili uploader" and `https://space.bilibili.com/2267573`, and not `bilibili:uploader:2267573`

#### Scenario: Popup on a space page
- **WHEN** the user opens the extension's popup on `https://space.bilibili.com/2267573` and chooses "Follow this site"
- **THEN** the popup's preview shows "Bilibili uploader" and the space address, and confirming follows the uploader

### Requirement: State Bilibili's terms where the feature is documented
The README SHALL have a section on Bilibili uploaders that states:
- that CatchUp never contacts Bilibili, and that the user's RSSHub makes the requests;
- that Bilibili's user agreement (section 5.6(3), updated 2025-04-30) forbids getting its content with automated programs without Bilibili's written permission, for any reason, so the user takes that risk;
- that RSSHub gets subtitles only with the user's own logged-in Bilibili cookie, which stays in RSSHub's settings and which CatchUp never asks for or stores;
- that a public RSSHub instance receives the ids of the uploaders the user follows, publishes no terms, and may not return subtitles;
- how to set `CATCHUP_RSSHUB_URL`, and how to start RSSHub with the optional Compose file.

#### Scenario: README states the risk
- **WHEN** the README is read
- **THEN** its Bilibili section names `CATCHUP_RSSHUB_URL`, section 5.6(3) of Bilibili's user agreement, the logged-in cookie, and public instances
