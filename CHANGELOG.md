# Changelog

## [Unreleased]

### Fixed

- Restore the original CodeQL analysis identity and its security-and-quality queries so findings from the earlier configuration are evaluated against current source.
- Combine the positive-output and PWM-range test assertions to remove a redundant comparison without reducing coverage.
- Retain downloadable CodeQL reports and fail the scan job on reported findings, including quality notes.

## [2.0.0] - 2026-10-17

This release repairs the maintained motor-control and training paths, updates dependencies, and consolidates the repository around the working application. It is a source release for Python 3.11 and 3.12.

### Fixed

- Correct stale-feedback handling, delayed-output races, zero-setpoint behavior and shutdown ordering. Add an independent GPIO write watchdog.
- Remove fabricated telemetry. Offline inspection opens the actual interface with motor start disabled and measurements unavailable.
- Unify neural model filenames, embedded input normalization, scaling-factor ranges and checksum-verified loading. New training saves native Keras models with SHA-256 sidecars.
- Use measured feedback and actual PWM writes for data collection and relay tuning. Report missing measurements as unavailable and fail relay tuning when usable oscillations are absent.
- Correct plotting time limits, GUI startup, configuration validation and launch/transfer scripts.
- Repair Dependabot's Python selection and make the PID response test independent of runner speed.

### Dependencies and verification

- Replace invalid pins and add missing graph/fuzzy dependencies. Provide complete hash-locked runtime, development and Raspberry Pi requirements.
- Test Python 3.11 and 3.12 in CI, audit runtime and GPIO dependency locks, and run CodeQL.
- Enforce all Pyflakes rules, including unused imports and variables. Test, lint and audit failures fail CI.
- Include 128 software tests covering controllers, control races, watchdogs, GPIO adapters, actual TensorFlow training/model round trips, metrics and offline Qt startup.
- Publish versioned source releases from the checked commit after the required jobs pass.

### Documentation and repository cleanup

- Rewrite the README and add focused operating and contribution guides.
- Add custom control-loop and neural-scaling schematics, an actual interface screenshot and a redesigned animation with a rotating motor, optical readout, moving PWM trace and a highlighted feedback sequence.
- Remove obsolete implementation reports, duplicate guides, disconnected prototype interfaces, legacy direct-GPIO scripts, unused icon assets, the old uninstaller and assistant-specific editor settings.
- Consolidate the code's MIT notices, document the preprint's CC BY 4.0 terms, and add citation metadata and third-party license notices.

### Migration

- Use `./run.sh` on the configured Pi or `./run.sh --offline` to inspect the interface. Retired standalone GPIO scripts and the separate simulation interface are no longer included.
- `DataCollector` now accepts `config` and `hardware`, replacing the older positional GPIO/PWM constructor. Use `improved_data_collection.py` for the maintained collection path.
- The older launcher and controller import names remain compatibility adapters.
- Keep trusted model files with their matching SHA-256 sidecars. Missing or invalid requested models cause explicit fuzzy-only operation.
- Set calibrated maximum RPM, pulses per revolution, debounce, PWM frequency and controller gains in `.env` before running hardware.

### Validation limits

Physical motor validation and quantitative controller comparisons remain outstanding for this revision. GPIO tests use adapters and do not establish electrical safety or real-time guarantees. Collection currently supplies heuristic scaling labels, not experimentally optimized neural training targets. Windows-to-Pi transfer has not been verified in the software test environment.

The [Zenodo preprint](https://doi.org/10.5281/zenodo.20124685) keeps its original version 1.0.0 and DOI. Cite the paper for the research description and record the software tag or exact Git commit used for an experiment.

Earlier source and documentation remain available in [Git history](https://github.com/alexhaya4/dc-motor-neuro-fuzzy/commits/main/).
