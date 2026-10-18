# Browser-tab icon: implementation checks

2026-10-18, branch `add-browser-tab-icon`. Commands ran from `frontend/` unless noted.

| Check | Actual result |
| --- | --- |
| `npm ci` | Installed 124 packages from the lockfile; 0 vulnerabilities reported. |
| `npm test -- --run src/install.test.ts` before adding links | Expected red: **1 failed, 3 passed** in 1 file (4 tests). The SVG icon link was missing. |
| `npm test -- --run` after adding links | **166 passed** in **13 files**. |
| `npm run build` | Passed TypeScript and Vite build; **41 modules** transformed. |
| `node --input-type=module -e "..."` (assert SVG and PNG icon links in `dist/index.html`) | Passed; the built HTML retains both links. |
| `openspec validate add-browser-tab-icon --strict` (repository root) | Valid. |
| `test -f docs/process/test-report-add-browser-tab-icon.md` (repository root) before writing the report | Expected red: exit status 1 (report absent). |
| `test -f docs/process/test-report-add-browser-tab-icon.md` after writing it | Passed. |

An extra exact-string check on `dist/index.html` failed because Vite retained the HTML's `/>` link endings; the earlier attribute-aware check and a repeated regex check both passed. The exact-string check was too strict, not an icon failure.

**Manual check not performed:** opening the app in a browser tab and seeing the CatchUp icon instead of the default icon. The asset and built-HTML checks do not verify browser rendering.
