# Spec Delta

## ADDED Requirements

### Requirement: Run RSSHub next to CatchUp with an optional Compose file
The project SHALL provide an optional Compose override file, `compose.rsshub.yaml`, that adds an RSSHub service for Bilibili uploaders. The default `compose.yaml` MUST stay unchanged, so an instance without the override starts no RSSHub and downloads no RSSHub image. With the override:
- the RSSHub service runs on Compose's private network and MUST NOT publish a port on the host;
- CatchUp's service gets `CATCHUP_RSSHUB_URL=http://rsshub:1200`;
- RSSHub reads its own optional settings, such as a Bilibili cookie, from `.env.rsshub`, which git ignores and the image build leaves out, like `.env`.

The README SHALL show how to add the override to `COMPOSE_FILE`, with and without the source-build override, and SHALL name the RSSHub image it uses and that it is a third-party download.

#### Scenario: Default start
- **WHEN** the user starts CatchUp with only `compose.yaml`
- **THEN** no RSSHub service starts, and Bilibili addresses are refused with the message that RSSHub is not set up

#### Scenario: Start with the override
- **WHEN** `.env` sets `COMPOSE_FILE=compose.yaml:compose.rsshub.yaml` and the user starts CatchUp with the documented command
- **THEN** RSSHub runs without a host port, and CatchUp reads Bilibili uploaders through `http://rsshub:1200`

#### Scenario: RSSHub settings stay local
- **WHEN** the working copy has a `.env.rsshub` file and the image is built
- **THEN** git does not track `.env.rsshub`, and the image does not contain it
