# Tasks

Implementer notes:
- **Read first.** Read `proposal.md`, `design.md` (D1–D4, including the probe findings under "Context"), and `specs/source-management/spec.md`. If something looks wrong or contradictory, stop and report instead of redesigning.
- **Work test-first with the `tdd` skill** (D-016). First write the verification items of 1.1 as failing tests and watch them fail. Then implement 1.2 until they pass. The seams are the ones in design D4: a replaced `socket.getaddrinfo`, a replaced `socket.create_connection`, a replaced `ssl.SSLContext.wrap_socket`, and a loopback listener in the test. They count as agreed.
- **Test rules.**
  - No real network and no real sleeps.
  - `tests/conftest.py` replaces `socket.getaddrinfo` and `socket.socket.connect` for every test. Replace `getaddrinfo` again inside each new test with `monkeypatch`. Only test 5 needs the real `connect`: capture `socket.socket.connect` when the test module is imported, and restore it with `monkeypatch` inside that test.
  - Answers from the replaced `getaddrinfo` use the shape of the existing `resolve` fixture: `(socket.AF_INET, socket.SOCK_STREAM, 6, "", (address, port))`.
  - Leave every existing test unchanged. `respx` intercepts before the network backend (design "Context"), so the existing tests must keep passing as they are.
  - Close every socket a test creates, including the listener and the unconnected socket of test 4.
- **Out of scope:**
  - every caller of `safe_fetch`;
  - `transcripts/youtube.py`, `sources/x_api.py`, `llm/client.py`;
  - `frontend/` and `extension/`;
  - dependency versions (`pyproject.toml`, `uv.lock`).
- **Commits.** Commit after each task group. Do not push, tag, or open a PR.

## 1. Connect only to checked addresses

- [x] 1.1 In `backend/tests/test_safe_fetch.py`, add these failing tests. Unless a test says otherwise:
  - the URL is `http://public.example/feed`;
  - `socket.create_connection` is replaced by a fake with the signature `(address, *args, **kwargs)`. `httpcore` calls it as `create_connection(address, timeout, source_address=...)`. The fake appends `address` to a list and then raises `OSError`. A fake that returns `None` or raises any other error makes the test fail from a mock error.
  1. **DNS answer changes after the check** (spec scenario). The lookup answers `8.8.8.8` on its first call and `127.0.0.1` on every later call. Assert:
     - `safe_fetch` raises `FetchError` with code `blocked_address` and the message "The source address is not allowed.";
     - the fake was never called.
  2. **Connects to the checked address.** The lookup answers `8.8.8.8`, and the fake raises `OSError`. Assert:
     - the recorded addresses are exactly `[("8.8.8.8", 80)]`;
     - `FetchError` has code `fetch_failed` and the message "The source could not be fetched."
  3. **Tries each checked answer in order.** The lookup answers `["8.8.8.8", "8.8.4.4"]`. The fake raises `TimeoutError` for `8.8.8.8`, and `OSError` for `8.8.4.4` and for any other address. Assert:
     - the recorded addresses are `[("8.8.8.8", 80), ("8.8.4.4", 80)]`;
     - `FetchError` has code `fetch_failed` and the message "The source could not be fetched."
  4. **HTTPS keeps the host name.** The URL is `https://public.example/feed`, and the lookup answers `8.8.8.8`. The fake returns an unconnected `socket.socket()`. Replace `ssl.SSLContext.wrap_socket` with a function `(self, sock, *args, **kwargs)`. It records the `server_hostname` keyword, `self.verify_mode == ssl.CERT_REQUIRED`, and `self.check_hostname`, then raises `ssl.SSLError`. Assert:
     - the recorded address is `("8.8.8.8", 443)`;
     - the recorded `server_hostname` is `"public.example"`;
     - certificate checks are on: the recorded `verify_mode` check and `check_hostname` are both `True`;
     - `FetchError` has code `fetch_failed`.
  5. **A response through the checked address.** Start a listener on `127.0.0.1` (port 0) in the test. The listener reads one request and answers `HTTP/1.1 200 OK` with `Content-Length: 6`, `Connection: close`, and the body `pinned`. The lookup answers `8.8.8.8`. The fake records its `address`, then connects to the listener with the real `connect` and returns that socket. Assert:
     - `safe_fetch(...).content == b"pinned"`;
     - the recorded addresses are `[("8.8.8.8", 80)]`;
     - the request the listener received has the header `Host: public.example`.

     Use a daemon thread with socket timeouts, so a failure cannot hang the test run.
  6. **Unresolvable when connecting.** The lookup answers `8.8.8.8` on its first call and raises `socket.gaierror` on later calls. Assert:
     - `FetchError` has code `fetch_failed` and the message "The source host could not be resolved.";
     - the fake was never called.
  7. **Mixed answers when connecting.** The lookup answers `8.8.8.8` on its first call and `["8.8.8.8", "10.0.0.1"]` on every later call. Assert:
     - `FetchError` has code `blocked_address`;
     - the fake was never called.

  A NAT64 answer at connect time (connecting to the IPv6 address as returned) is not tested. It is marginal under D-023.

  Verify: all seven tests fail before 1.2 for the expected reason. Today the fake receives `("public.example", <port>)`, so tests 2–5 fail on the recorded address. Tests 1 and 7 fail on the error code and because the fake was called. Test 6 fails on the message ("The source could not be fetched.") and because the fake was called. No test may fail because of a mock error.
- [x] 1.2 Implement design D1–D3 in `backend/src/catchup/net/safe_fetch.py`:
  - the shared address rule helper (D2), now used by `_check_address`;
  - the `httpcore.SyncBackend` subclass (D1);
  - the client factory that installs it (D3).

  Keep `_check_address` before every request and redirect hop, and keep all error codes and messages.

  Verify:
  - the 1.1 tests pass; all of `backend/tests/test_safe_fetch.py` passes unchanged otherwise; `uv run pytest` passes in `backend/`.
  - Each mutation below makes at least the named tests fail. Run each one, watch the tests fail, and restore the code. Record each mutation and the tests that failed in the test report.
    - (M1) Connect with `host` instead of the answer's IP: tests 2–5.
    - (M2) Skip the address rule in the backend, but still resolve: tests 1 and 7.
    - (M3) Do not replace `_pool._network_backend`: tests 1–7.
    - (M4) Stop after the first answer that fails to connect: test 3.
    - (M5) Try the next answer only after `httpcore.ConnectError`, not after `httpcore.ConnectTimeout`: test 3.
    - (M6) In the override, open the socket with `socket.create_connection((ip, port), timeout)` and return `httpcore._backends.sync.SyncStream(sock)`, instead of calling `super().connect_tcp`: tests 2–3.
    - (M7) Build the transport with `verify=False`: test 4.

## 2. Docs, checks, and report

- [ ] 2.1 In `docs/technical-spec.md`, change the **Fetching** line so it says that `safe_fetch` checks addresses again when it connects and connects only to checked addresses. Keep the rest of the line.

  Verify: the line is changed, and the other lines of the file are unchanged.
- [ ] 2.2 Run the full checks:
  - `uv run pytest` in `backend/` (record the count);
  - `DO_NOT_TRACK=1 openspec validate pin-fetch-connections --strict`;
  - if Docker is available: `docker build -t catchup:pin-fetch-connections-local .` from the repository root, then `scripts/docker-smoke.sh catchup:pin-fetch-connections-local`.

  Write the commands and their real results to `docs/process/test-report-pin-fetch-connections.md`:
  - map each scenario of the modified requirement to its tests (the unchanged scenarios map to the existing tests in `test_safe_fetch.py`);
  - record the seven mutations and their results from 1.2;
  - list the live check that Claude Code runs at review (design "Migration Plan") as not performed.

  Add your entry to `docs/process/ai-usage-log.md` after the latest entry, with a faithful prompt excerpt. Leave out the session id; Claude Code adds it at review.

  Verify: every command passes, and the report has the actual numbers.
