# Changelog

All notable changes to the DC Motor Neuro-Fuzzy Control System.

## [Unreleased]

- Resolve the invalid dependency pin, add missing fuzzy/graph packages, and separate hash-locked runtime, development and GPIO dependencies for Python 3.11/3.12.
- Make software tests, dependency audits and static checks fail CI when they find failures; pin current Actions and repair Dependabot configuration.
- Remove import-time GPIO activation from the compatibility launcher and add explicit offline inspection without random sensor readings.
- Correct sensor freshness, late-output races, zero-setpoint behavior, shutdown ordering, PWM display, GUI startup and plot time limits.
- Add a separate output watchdog and validate motor configuration and distinct GPIO pins.
- Unify neural model filenames, input normalization, output scaling, integrity checks and Keras/HDF5 loading. Replace duplicate heuristic-neural implementations with maintained adapters.
- Route collection and relay tuning through real motor I/O with cleanup; identify heuristic labels, share the trainer schema, and fail unsuccessful relay tuning without fabricated gains.
- Replace first-crossing settling estimates and missing-data zero scores with explicitly available observation-based metrics.
- Repair installation, source transfer and training entry points. The programmatic DataCollector signature now takes config/hardware rather than positional GPIO pins.
- Add regression coverage for these behaviors. Physical rig validation remains separate from software tests.

### Repository cleanup

- Add editable control-loop and neural-scaling schematics alongside the animated signal-flow overview.
- Remove obsolete implementation reports, duplicate operating guides, unused prototype interfaces and unused icon assets.
- Remove legacy standalone GPIO scripts that bypassed configuration and the maintained watchdog/output path, plus the obsolete uninstaller and editor-specific assistant settings.
- Retain the documented compatibility entry points and the active software test suite.
- Remove unused imports and stale performance-scoring constants; check all Pyflakes rules in CI.
- Consolidate the code's MIT notices, document the paper's CC BY 4.0 terms and add citation and dependency-license metadata.

Earlier source and documentation remain available in [Git history](https://github.com/alexhaya4/dc-motor-neuro-fuzzy/commits/main/). The [Zenodo preprint](https://doi.org/10.5281/zenodo.20124685) remains the archived research reference.
