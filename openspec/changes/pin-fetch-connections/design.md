# Design

## Context

The motivation is in proposal.md ("Why"). Today, in `backend/src/catchup/net/safe_fetch.py`:
- `_check_address(url)` (`:73-101`) parses the URL, refuses X hosts, resolves the host with `socket.getaddrinfo(host, port, type=SOCK_STREAM)`, and refuses the URL when any answer is not public. A NAT64 address (`64:ff9b::/96`) is judged by the IPv4 address it embeds. It raises `FetchError("fetch_failed", "The source host could not be resolved.")` or `FetchError("blocked_address", "The source address is not allowed.")`.
- `safe_fetch()` calls `_check_address` before every request, including every redirect hop. It does this before it uses up the fetch budget and before it waits for host spacing. Then it sends the request with `httpx.Client(follow_redirects=False, trust_env=False, ...)`.
- `httpx` passes the request to `httpcore`, whose network backend calls `socket.create_connection((host, port))`. That resolves the host a second time. Nothing checks this second answer.

A probe on 2026-11-09 (`httpx` 0.28.1, `httpcore` 1.0.9, `respx` 0.23.1; no real network) found:
- `httpx.HTTPTransport` takes no network backend. Its connection pool keeps one in the private attribute `_pool._network_backend`. Replacing it before the first request works: every new connection then goes through the replacement.
- `httpcore.SyncBackend` is public. Its `connect_tcp(host, port, timeout, local_address, socket_options)` receives the URL's host: an IDNA (punycode) name, or an IPv6 literal without brackets. It also receives the connect timeout.
- Calling `super().connect_tcp("<ip>", port, ...)` connects to that address. The `Host` header and the TLS `server_hostname` (SNI, used for certificate checks) are still the URL's host name.
- An exception raised inside `connect_tcp` comes out of `client.stream()` unchanged. A `FetchError` stays a `FetchError`, and it is not an `httpx.HTTPError`.
- `OSError` and socket timeouts become `httpx.ConnectError` and `httpx.ConnectTimeout` only when they come from `super().connect_tcp()`. A raw `OSError` that an override raises itself is not mapped. It would then escape `safe_fetch`'s `except httpx.…` clauses.
- `respx` intercepts requests at the connection pool, before the network backend. The existing tests that use `respx` (237 `respx.mock` blocks in 17 files) never reach `connect_tcp`. They are unaffected, and they cannot test this change.

## Goals / Non-Goals

**Goals:**
- Every connection `safe_fetch` opens goes to an address that passed the address rule at the moment of connecting.
- One address rule, in one place.
- Error codes, messages, the fetch budget, host spacing, redirects, and certificate checks stay as they are.

**Non-Goals:**
- YouTube caption requests, the X API client, and the model client (see proposal.md, "Impact").
- Proxies. `trust_env=False` already turns off proxies from the environment.
- Checking a connection that is reused for the next request to the same origin. It was opened to a checked address.

## Decisions

### D1. Check again when the connection is opened, in a network backend

A subclass of `httpcore.SyncBackend` (for example `_PublicOnlyBackend`) overrides `connect_tcp(host, port, timeout=None, local_address=None, socket_options=None)`:
1. Resolve `host` and `port`, and apply the address rule to every answer (D2). A failure raises the same `FetchError` as `_check_address`.
2. Try the checked answers in the order the resolver returned them. For each answer, call `super().connect_tcp(<answer's IP>, port, timeout, local_address, socket_options)` and return the stream from the first one that connects.
3. If an attempt raises `httpcore.ConnectError` or `httpcore.ConnectTimeout`, try the next answer. When none connects, re-raise the last error. `httpx` turns it into `httpx.ConnectError` or `httpx.ConnectTimeout`, and `safe_fetch` reports `fetch_failed` as today.

The override never opens a socket itself. Only `super().connect_tcp` connects, so `httpcore` keeps mapping `OSError` and timeouts (probe). `socket.create_connection` with an IP literal does not use DNS.

`_check_address` still runs before every request and every redirect hop. It reports bad URLs, X hosts, unresolvable hosts, and blocked addresses before a request uses up the run's fetch budget or waits for host spacing. No existing test protected this order. The review added `test_address_check_runs_before_budget_and_spacing` for it.

- **Why.** The rule now applies to the address the connection actually uses, for every connection the client opens. The backend keeps no state between calls.
- **Cost.** One more DNS lookup for each new connection. The system resolver normally caches it, and a connection to the same origin is reused within one `safe_fetch` call.
- **Alternative: pin to the answers from `_check_address`.** This saves the second lookup. But `safe_fetch` would have to hand per-host state to the pool, and the backend would need a rule for a host that was never checked. Rejected: more state for no security gain.
- **Alternative: rewrite the URL to the IP and set the host name by hand** (the `Host` header and the `sni_hostname` request extension). Rejected: `response.url` would show the IP (`FetchResponse.url` is stored and joined with redirect targets), IPv6 literals need brackets, and every `respx` route would need to change.
- **Alternative: patch `socket.getaddrinfo` while a request runs.** Rejected: it is global for the whole process, and runs fetch in several threads.

### D2. One address rule

The per-answer rule moves out of `_check_address` into one helper, for example `_public_answers(host, port)`. It returns the checked `getaddrinfo` answers, and both `_check_address` and the backend call it:
- It resolves with `socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)`.
- `OSError` or `UnicodeError` from the lookup, or an empty answer list, raises `FetchError("fetch_failed", "The source host could not be resolved.")`.
- Every answer must pass, as today. A NAT64 answer is judged by its embedded IPv4 address. Mixed public and non-public answers are refused with `FetchError("blocked_address", "The source address is not allowed.")`.

`_check_address` keeps the URL parsing and the X host check, and then calls the helper with `parts.hostname` and the port.

The backend connects to `answer[4][0]`, the address exactly as the resolver returned it. For a NAT64 answer, that is the IPv6 address, not the embedded IPv4 one.

### D3. Wiring

`safe_fetch` builds its client through one small factory:
- `transport = httpx.HTTPTransport(trust_env=False)`, which matches what `httpx.Client(trust_env=False)` builds today;
- `transport._pool._network_backend = _PublicOnlyBackend()`;
- `httpx.Client(transport=transport, follow_redirects=False, trust_env=False, headers={"User-Agent": user_agent()})`.

Nothing else in `safe_fetch()` changes.

`_pool._network_backend` is private to `httpx` and `httpcore`. If an upgrade renames it, assigning to it would silently do nothing. Tests fail in that case (tasks 1.1, tests 1–7), and `uv.lock` pins the versions that were checked.

### D4. Test seams

`respx` cannot test this change (probe). The new tests in `backend/tests/test_safe_fetch.py` use other seams:
- **DNS.** Replace `socket.getaddrinfo` with a lookup that can answer differently on each call. The existing `resolve` fixture returns one fixed map.
- **Connect.** Replace `socket.create_connection` with a fake that records the `address` it is given. Depending on the test, the fake then:
  - raises `OSError`;
  - returns an unconnected `socket.socket()` for the TLS test (the test closes it);
  - or connects to a loopback listener in the test. `tests/conftest.py` replaces `socket.socket.connect` for every test, so this test restores the real method, captured when the test module is imported.

No test uses the real network.

## Risks / Trade-offs

- [A private `httpx` attribute] → A test fails if connections stop going through the backend, and `uv.lock` pins the versions. An upgrade of `httpx` or `httpcore` must keep that test green.
- [A second DNS lookup for each new connection] → Normally cached, and small next to the fetch itself.
- [A host whose public answers differ between the two lookups, such as round-robin DNS] → Both sets are checked, so the fetch works.
- [A host that answers public first and non-public at connect time] → Refused as `blocked_address`. This is the case the change exists for.
- [Each answer gets the full connect timeout] → Same as `socket.create_connection` today. The 30-second fetch deadline still applies between steps.

## Migration Plan

Backend only. No data migration. Roll back by reverting the commit.

At review, Claude Code runs the Docker smoke script (`scripts/docker-smoke.sh`) and a live check on a test container (not 8800):
1. Preview a public HTTPS feed, and one that redirects. This checks that real certificate checks still pass when the connection goes to an IP.
2. Preview `http://127.0.0.1/`, and check that it is refused as not allowed.

DNS rebinding itself is checked only by the unit tests. A live rebinding check would need an outside DNS service.
