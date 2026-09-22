# Engineering quality review

## 1. Project Assessment

Reviewed baseline commit `4ce6d8f834307cfbd521f30f1fbc46898675fec9`. All tracked first-party source, documentation,
dependency/configuration files and entrypoints were inspected. Original source
compiled; no tests or CI existed. No database, server, Docker or build system was
present. Original PixelScribe and trading imports required missing environment
dependencies; this was not caused by the changes. Baseline evidence is retained
in the delivered review archive. Validation environment: Windows, Python 3.14.6.

## 2. Major Issues Found

P1: worker-thread Tk calls, duplicate batch starts, cancellation reported as success, PDF page setting read from worker, PNG bytes labeled JPEG, temporary image leaks, stale history mapping.

## 3. Changes Implemented

Consolidated image requests and bounded 429 retries; marshaled worker errors through the queue; snapshotted PDF page limits; normalized image payloads to PNG; added cleanup in finally, graceful shutdown, saved-result paths, history-map cleanup and mixed timestamp sorting; supplied missing requirements. Added behavioral regression tests, a focused CI matrix, and updated
installation/run instructions. No Git history, user data or model resources were deleted.

## 4. Bugs Fixed

The concrete defects listed above are covered by focused regression tests;
external-service behavior is distinguished below from local evidence.

## 5. Architecture Improvements

One request helper for images/PDF pages; main-thread UI boundary preserved. Original FileDescriptor class and entrypoint retained.

## 6. Performance Improvements

No throughput or latency improvement is claimed: no performance benchmark was run.
Resource-lifetime and correctness changes are not reported as measured speedups.

## 7. Testing & Validation

PASS: `11` tests using `python -m unittest discover -s tests -v`.
PASS: `python -m compileall -q .`.
PASS: `python -m pip check` in the shared isolated review environment.
PASS: `python -m ruff check . --select E9,F63,F7,F82` (focused correctness rules).
PASS: `python -m mypy --follow-imports=skip --ignore-missing-imports FileDescriptor.py`
(basic checking, not strict coverage of all unannotated bodies or dependencies).
PASS: `git diff --check`.

PASS: hidden real Tk startup, result/history queue dispatch, history clearing and shutdown. PASS: real Poppler conversion of a generated one-page PDF.

NOT TESTED locally: Python 3.10/3.12 and Linux/macOS. GitHub CI defines Linux
Python 3.10/3.12/3.14 checks; adding a workflow is not evidence that it has run.
No separate packaging/build target exists; bytecode compilation is the build check.

## 8. Remaining Risks

NOT TESTED: real DashScope inference (no API key used or credits spent), long-running cancellation against the remote service, complete manual UI interactions. Remaining legacy UI exception handlers deserve focused manual testing.

## 9. How to Run

From the repository root, use Python 3.10+ and a virtual environment.
Install runtime dependencies with `python -m pip install -r requirements.txt`.

```bash
python FileDescriptor.py
python -m unittest discover -s tests -v
```

## 10. Recommended Next Steps

Run one real image and PDF request with your own DashScope key; exercise cancellation, file saving and exports manually.
