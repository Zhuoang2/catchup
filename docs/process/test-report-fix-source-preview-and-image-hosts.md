# Test report: fix-source-preview-and-image-hosts

Implementation evidence, recorded as each task group runs. Python 3.12.13;
frontend and extension use Node 22.17.1.

## Setup

In each of `frontend/` and `extension/`:
`export PATH="$HOME/.nvm/versions/node/v22.17.1/bin:$PATH"` then
`npm ci --offline --no-audit --no-fund`, exit 0 (124 and 120 packages respectively).
Backend commands use `uv run`, with no new dependencies added.
All OpenSpec CLI commands are prefixed with `DO_NOT_TRACK=1`.

## Group 1: shared public-address rule and candidates

- Red: `uv run pytest tests/test_public_hosts.py`, exit 2, collection fails with
  `ModuleNotFoundError: No module named 'catchup.net.public_hosts'`, as required.
- Green: `uv run pytest tests/test_public_hosts.py tests/test_safe_fetch.py`,
  122 passed (53 new table cases, 69 existing fetch tests unchanged).
- Red: `uv run pytest tests/test_discovery.py::test_entry_images_on_local_addresses_are_dropped tests/test_extension_api.py::test_capture_drops_images_on_local_addresses`,
  2 failed, both returning local image candidates.
- Green: `uv run pytest`, 1024 passed, including both new candidate tests.
- `NAT64_PREFIX` search found no importers, only its definition and use in
  `safe_fetch.py`; the constant now belongs to `public_hosts.py`.

### Isolated mutations

Each mutation below ran alone with `uv run pytest -q`, exited 1 with the stated
assertion failures, and was restored byte-for-byte. After each restoration,
`git diff` for the affected production files matched the pre-mutation diff.
`table` means `tests/test_public_hosts.py`.

| Mutation | Tests run | Actual result and killing test |
| --- | --- | --- |
| H1 | table | 16 failed, 37 passed; `test_nonpublic_image_address_is_dropped`, private/special IPv4 and IPv6 rows |
| H2 | table | 14 failed, 39 passed; dropped rows including `0x7f.1` and `127.1` |
| H3 | table | 1 failed, 52 passed; `test_public_image_address_is_kept`, `example.com.` |
| H4 | table | 3 failed, 50 passed; dropped full-width IPv4, Unicode domain, and empty-label rows |
| H5 | table | 2 failed, 51 passed; dropped `nas.local` and `nas.local.` rows |
| H6 | table | 2 failed, 51 passed; dropped `printer` and `printer.` rows |
| H7 | table plus `tests/test_safe_fetch.py::test_nat64_embedded_public_address_allowed` | 2 failed, 52 passed; kept public NAT64 row and existing NAT64 fetch test |
| H8 | both new candidate tests named above | 2 failed; feed and capture both retained local images |
| H10 | table | 2 failed, 51 passed; both dropped backslash rows |

H1 retained literal parsing but bypassed `is_public_address` for IPv4 and IPv6.
H2 removed the numeric-last-label branch; H3 omitted trailing-dot removal;
H4 omitted the ASCII-name check; H5 omitted the `local` suffix; H6 allowed
single-label names; H7 omitted NAT64 conversion; H8 restored the old HTTP(S)
scheme-and-host candidate condition; H10 omitted backslash rejection.

## Review-only checks

- Docker build and `scripts/docker-smoke.sh`: not performed, explicitly excluded
  by the implementation request; Claude Code runs them at review.
- Live Sources slow-preview browser check and saved-digest image network check:
  not performed; Claude Code runs them at review.
