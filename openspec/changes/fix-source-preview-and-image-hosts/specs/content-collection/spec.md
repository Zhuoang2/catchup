# Spec Delta

## MODIFIED Requirements

### Requirement: Keep image candidates for items
For each entry of a website feed, and for each YouTube video, the system SHALL keep up to 8 image candidates in the order they appear: images in the entry's HTML, with their alt text and figure caption; image `media:content`; `media:thumbnail`; and image enclosures. Only `http` and `https` images are kept. Avatars, site icons, channel images, `data:` URLs, and 1×1 images MUST NOT be kept. Podcast cover art MUST NOT be kept. Keeping candidates MUST NOT fetch any image.

An image whose address names this computer or a device on a local network MUST NOT be kept. This applies to every item that keeps image candidates, including X posts and pages saved from the browser. An image is left out when its host is:
- an IP address that is not public: loopback, private, link-local, shared, reserved, multicast, or unspecified, including an IPv4 address written inside an IPv6 address;
- a number that a browser reads as an IPv4 address but that is not written as four plain decimal parts, such as `2130706433`, `0x7f.1`, or `127.1`;
- `localhost` or a name under it, a name without a dot, or a name under `localdomain`, `local`, `internal`, `intranet`, `private`, `corp`, `home`, `home.arpa`, or `lan`, with or without a trailing dot;
- anything other than ASCII letters, digits, hyphens, underscores, and dots, such as a percent-encoded or full-width host.

An image whose address contains a backslash (`\`) MUST NOT be kept either: browsers read it as `/`, and may then request a different host than the address seems to name.

Keeping candidates MUST NOT look up host names.

#### Scenario: Post with screenshots
- **WHEN** a website entry's HTML contains two screenshots with alt text and a figure caption
- **THEN** both are kept as candidates in order, with their alt text and caption

#### Scenario: Author avatar in the feed
- **WHEN** a WordPress feed item's `media:content` holds the author's Gravatar avatar and one post image
- **THEN** only the post image is kept

#### Scenario: Image on a private address
- **WHEN** a website entry's HTML contains `http://192.168.1.1/cam.jpg` and `https://cdn.example.com/chart.png`
- **THEN** only `https://cdn.example.com/chart.png` is kept

#### Scenario: Image on a numeric host form
- **WHEN** a website entry's HTML contains `http://2130706433/x.png`, which a browser requests from 127.0.0.1
- **THEN** that image is not kept

#### Scenario: Image on a local name
- **WHEN** a website entry's HTML contains `http://localhost:631/p.png`, `http://printer/p.png`, `http://nas.local/p.jpg`, and `http://localhost.localdomain/p.png`
- **THEN** none of them is kept

#### Scenario: Image address with a backslash
- **WHEN** a website entry's HTML contains `http://192.168.1.1\@cdn.example.com/a.png`, which a browser requests from 192.168.1.1
- **THEN** that image is not kept

#### Scenario: Page saved from the browser with a local image
- **WHEN** a page saved from the browser lists `http://[::1]:9000/i.png` and a public image
- **THEN** only the public image is kept
