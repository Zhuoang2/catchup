## ADDED Requirements

### Requirement: Saved digests keep their images
A saved digest SHALL record, for each summarized item, the URLs and alt texts of the images its summary chose, at the time it was saved. Reopening the digest MUST show the same images, and MUST NOT choose images again. Digests saved before images were recorded are shown without images.

#### Scenario: Reopen a digest with images
- **WHEN** a saved digest's item chose one screenshot, and the item's source is later deleted
- **THEN** reopening the digest still shows that screenshot under the item
