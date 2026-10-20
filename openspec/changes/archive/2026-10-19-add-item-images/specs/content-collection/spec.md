## ADDED Requirements

### Requirement: Keep image candidates for items
For each entry of a website feed, and for each YouTube video, the system SHALL keep up to 8 image candidates in the order they appear: images in the entry's HTML, with their alt text and figure caption; image `media:content`; `media:thumbnail`; and image enclosures. Only `http` and `https` images are kept. Avatars, site icons, channel images, `data:` URLs, and 1×1 images MUST NOT be kept. Podcast cover art MUST NOT be kept. Keeping candidates MUST NOT fetch any image.

#### Scenario: Post with screenshots
- **WHEN** a website entry's HTML contains two screenshots with alt text and a figure caption
- **THEN** both are kept as candidates in order, with their alt text and caption

#### Scenario: Author avatar in the feed
- **WHEN** a WordPress feed item's `media:content` holds the author's Gravatar avatar and one post image
- **THEN** only the post image is kept
