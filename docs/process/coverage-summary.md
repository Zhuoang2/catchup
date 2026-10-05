# Test coverage summary

2026-10-03, after task 4.1: `cd backend && uv run pytest --cov=catchup --cov-report=term` passed 113 tests. Backend statement coverage: **95% overall** (736/778), **100%** for `collection.py` (57/57). `cd frontend && npm test -- --run` passed 9 tests. This is an interim snapshot; the full spec-scenario report belongs to task 7.2.

2026-10-04, improve-source-reliability: `cd backend && uv run pytest --cov=catchup --cov-report=term` passed **197 tests**, **96% overall** (1201/1256); changed-module coverage and all 11 delta scenarios are mapped in `test-report-improve-source-reliability.md`. `cd frontend && npm test -- --run` passed **22 tests**.

2026-10-04, add-docker-packaging: `cd backend && uv run pytest --cov=catchup --cov-report=term` passed **206 tests**, **96% overall** (1214/1269); `cli.py`, `config.py`, and `db.py` are at **100%** and `main.py` at **99%**. `cd frontend && npm test -- --run` passed **22 tests**. All 10 deployment scenarios are mapped in `test-report-add-docker-packaging.md`; newer-image migration and GHCR publishing need later verification.

2026-10-05, add-podcast-and-video-sources: `cd backend && uv run pytest --cov=catchup --cov-report=term` passed **327 tests**, **96% overall** (1708/1782). The new `transcripts/convert.py` has **91%**, `transcripts/youtube.py` **98%**, and `digest/runner.py` **99%** statement coverage. `cd frontend && npm test -- --run` passed **34 tests**, and the frontend build passed. Docker build and smoke passed; see `test-report-add-podcast-and-video-sources.md`.
