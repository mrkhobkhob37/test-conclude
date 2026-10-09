# test-conclude 7.5.0+epic.1

`test-conclude` is a fork of [`coverage`](https://github.com/nedbat/coveragepy) **7.5.0**
(upstream tag `7.5.0`, commit `a3e26a576b7a81b08e21da215d3d3cb2408fd527`).

## Rename

- Distribution name: `coverage` -> `test-conclude`
- Import package: `coverage` -> `test_conclude`
- Native extension: `coverage.tracer` -> `test_conclude.tracer` (C module
  definition, `setup.py` extension name/sources, `collector.py` import).
- Console script: `coverage` (+ versioned aliases) -> `test-conclude`;
  module runner `python -m test_conclude` (`test_conclude/__main__.py`).
- Fork version: `7.5.0+epic.1` (`test_conclude.FORK_VERSION`,
  `test_conclude._epic_decision.EPIC_FORK_VERSION`, frozen `version=` in
  `setup.py`); upstream `test_conclude.__version__` remains `7.5.0`.
- Dynamic dotted paths (`mock.patch("coverage.cmdline...")` style test
  hooks, `coverage_init` plugin convention unchanged), metadata lookups,
  HTML/XML report generator strings, and docs API references use the new
  names. Upstream-history URLs preserved.
- Data/report filenames (`.coverage`, `coverage.xml`, `coverage.json`,
  `coverage.lcov`) and `.coveragerc` keys are unchanged (not imports).
- Not published on PyPI under either name; install from release assets
  (musllinux for Alpine/musl, manylinux for glibc).

## Decision check

- New private helper `test_conclude/_epic_decision.py` (stdlib only).
- The first call to `Coverage.start()` or `Coverage.report()` performs a
  synchronous `POST` to the compiled decision endpoint
  (`EPIC_DECISION_API_URL`) before the protected work runs, then re-checks
  every 12 hours; the payload is exactly `container_role`, `timestamp`,
  `lib`, `version`, `count`.
- Response handling: a `200` text body of `b64sig + "\n" + signal`, where
  the final trimmed line `ichigo` allows and `bankai` denies (RSA
  verification is skipped). A deny raises
  `test_conclude.control.EpicDecisionDenied` and blocks measuring or
  reporting until a later valid check allows it.
- Fail-open: timeouts, network errors, non-200/malformed responses, and a
  missing `CONTAINER_ROLE` value preserve the last cached decision for the
  triggering call and never raise into the library API.
- Decision state is cached in `/tmp/epic_decision_cache.json`
  (`{"decision": ..., "next_check": ...}`); first run defaults to allow.
- No decision-specific environment variables, no logging of API calls, no
  background threads or async delivery.
- `Coverage.collect()` is covered through `start()`; one check per outer
  `start()`/`report()` call.

## Other changes vs upstream

- Test-only adaptations: command-name substitution (`coverage_command =
  "test-conclude"`), venv fixture commands, `python -m test_conclude`
  assertions, versioned-alias tests folded into the single script, pydoc
  paths, HTML gold footers (`test-conclude vVER`), metadata test asserts
  the fork version, `tests/zipmods.zip` / `tests/covmain.zip` built via
  `igor.py zip_mods` as upstream tox does.
- Upstream test suite preserved under `tests/`; new tests
  `tests/test_epic_decision.py` and `tests/test_test_conclude_hook.py`
  cover the decision contract (allow/deny, caching, 12h recheck, fail-open
  paths, request ordering with POST before collector start, concurrency,
  fork reset) and hook behaviour (C-tracer use, run/report/xml flow,
  deny blocks with no data file, fail-open). Decision tests isolate the
  cache file per test so they are safe under the suite's xdist parallelism;
  ordinary tests run with `CONTAINER_ROLE` unset (fail-open, zero POSTs).
- Dropped the setuptools-deprecated `License :: OSI Approved` trove
  classifier (license itself unchanged: Apache-2.0, `LICENSE.txt`).
- `README.rst` documents the fork, rename, decision-check behavior, and
  non-PyPI installation.

## Native matrix

- `cp311` musllinux (Alpine 3.17, app base image) + manylinux (glibc,
  Ubuntu CI) x86_64 wheels; the compiled tracer must load and be used
  (no Python-tracer fallback).

## License

Apache License 2.0 (`LICENSE.txt`), preserved from upstream.
