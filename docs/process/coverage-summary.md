# Test coverage summary

2026-10-03, after task 4.1: `cd backend && uv run pytest --cov=catchup --cov-report=term` passed 113 tests. Backend statement coverage: **95% overall** (736/778), **100%** for `collection.py` (57/57). `cd frontend && npm test -- --run` passed 9 tests. This is an interim snapshot; the full spec-scenario report belongs to task 7.2.

2026-10-04, improve-source-reliability: `cd backend && uv run pytest --cov=catchup --cov-report=term` passed **197 tests**, **96% overall** (1201/1256); changed-module coverage and all 11 delta scenarios are mapped in `test-report-improve-source-reliability.md`. `cd frontend && npm test -- --run` passed **22 tests**.
