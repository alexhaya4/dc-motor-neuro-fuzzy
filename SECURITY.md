# Security

Report vulnerabilities through [GitHub private vulnerability reporting](https://github.com/alexhaya4/dc-motor-neuro-fuzzy/security/advisories).

## Code scanning

CodeQL runs the security-and-quality query suite on pushes, pull requests and a weekly schedule. The analysis category remains stable so new scans update earlier findings. Any reported finding fails the scan job; SARIF reports are available as the `codeql-results` Actions artifact.

## Dependencies

Install the hash-locked requirements for the intended environment. The installer explicitly enforces pip hash checking and does not perform unpinned package-manager upgrades. Runtime and GPIO locks are checked with `pip-audit` in CI; findings fail the job. Update the input files and regenerate the corresponding lock files together. A clean dependency audit covers known package advisories at the time of the check.

## Models and training data

Load models only from trusted sources. The maintained controller requires SHA-256 sidecars and Keras safe-mode loading. Checksums detect changes relative to a sidecar; they do not authenticate the model's author. Keep model files and their sidecars together. Legacy HDF5 models are accepted only with matching sidecars; new training saves native `.keras` models.

Training data is limited by bytes actually read, schema-checked and checked for finite numeric values. Scaling labels must lie in the ranges the networks can represent. Heuristic collection labels are identified as such in the saved dataset.

## Motor operation

The supported hardware path starts disabled, requires fresh feedback to enable control, and writes zero on stop, expired feedback and shutdown. A separate software watchdog disables output if writes stall. These are software protections, not an independent hardware emergency stop. Use an appropriate driver, power supply and physical disconnect for the motor rig. Software tests do not establish electrical safety or validate a particular motor's tuning.

Offline inspection never opens GPIO, enables a motor or generates sensor readings. Raspberry Pi installations need OS-maintained Qt packages and GPIO permissions; do not make device files world-writable.
