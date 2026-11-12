# Proposal

## Why

`safe_fetch` resolves a URL's host and refuses private, loopback, link-local, and other non-public addresses (`backend/src/catchup/net/safe_fetch.py:85-101`). Then `httpx` resolves the host a second time when it opens the connection (`:142`). A host whose DNS answer changes between the two lookups (DNS rebinding) therefore gets past the check: the first answer is public, the second is `127.0.0.1` or a local network address (#68).

The first design accepted this as a residual risk (`openspec/changes/archive/2026-10-03-add-core-digest-flow/design.md:203`). Since D-020, each run fetches up to 8 links from every new item, including items from saved pages and X posts. So any author the user follows can make the next run send GET requests to the user's machine or local network, and the page that comes back is sent to the model provider.

## What Changes

- Every connection that `safe_fetch` opens goes to an address that has just passed the address check. The check runs again when the connection is opened, on the addresses that the connection then uses. A host whose answer changes to a non-public address after the first check is refused with the existing "The source address is not allowed." error, and no connection to that address is attempted.
- The check before each request (and before each redirect) stays. It still reports errors before a request uses up the run's fetch budget or waits for host spacing.
- HTTPS still verifies the certificate for the URL's host name, and requests still send the host name in `Host`.
- No API, data, or UI change. Error codes and messages stay the same.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `source-management`: "Fetch user-supplied URLs safely" now requires that a connection goes only to an address that passed the check, and adds a scenario for a DNS answer that changes after the check.

## Impact

- Code: `backend/src/catchup/net/safe_fetch.py` and `backend/tests/test_safe_fetch.py`. Callers (`collection.py`, `context/gather.py`, `context/robots.py`, `sources/discovery.py`, `api/sources.py`) are unchanged.
- Dependencies: no new package. The change uses `httpcore.SyncBackend` (public) and replaces the network backend of `httpx.HTTPTransport`'s connection pool, which is a private attribute in `httpx` 0.28. A test fails if that wiring stops working after an upgrade.
- Out of scope:
  - YouTube caption requests (YouTube's own hosts);
  - the X API client (fixed host `api.x.com`);
  - the model client, whose base URL the user chooses and may point to a local server on purpose.
- Docs: `docs/technical-spec.md` (the Fetching line), the decision log (D-027), the requirements-changes table, the test report, and the AI usage log.
