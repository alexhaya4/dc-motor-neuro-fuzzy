# Contributing

Changes should make the maintained control path easier to reproduce, operate or verify. Explain the observed problem, the resulting behavior and the evidence supporting the change. Keep generated recordings, environments, private configuration and trained models out of source commits.

## Development setup

Use Python 3.11 or 3.12. From the repository root:

```bash
./install.sh
.venv/bin/python -m pip install --require-hashes -r requirements-dev.txt
```

## Required checks

```bash
.venv/bin/python -m pytest
.venv/bin/python -m ruff check --select E9,F .
bash -n install.sh run.sh deploy_to_pi.sh
.venv/bin/python -m pip check
.venv/bin/python -m pip_audit --disable-pip --require-hashes -r requirements.txt
.venv/bin/python -m pip_audit --disable-pip --require-hashes -r requirements-pi.txt
git diff --check
```

The test configuration sets Qt offscreen and limits TensorFlow worker threads. Tests under `tests/` use GPIO adapters and never actuate a physical motor. Hardware operation goes through the configured application, collector or relay tuner and their shared output handling.

CI runs the software suite on Python 3.11 and 3.12, audits dependency locks and runs CodeQL. Describe hardware checks separately from software checks; passing GPIO adapter tests does not establish that wiring, timing or shutdown works on a physical rig.

## Dependency maintenance

Direct pins live in `requirements.in`, `requirements-dev.in` and `requirements-pi.in`. Their `.txt` counterparts contain complete, hash-locked resolutions. Preserve compatibility with both supported Python versions. Dependabot uses `.python-version` to select the Python 3.11 baseline rather than defaulting to an unsupported interpreter.

With [uv](https://docs.astral.sh/uv/) installed, regenerate all affected locks:

```bash
uv pip compile requirements.in --index-url https://pypi.org/simple --python-version 3.11 --universal --generate-hashes -o requirements.txt
uv pip compile requirements-dev.in --index-url https://pypi.org/simple --python-version 3.11 --universal --generate-hashes -o requirements-dev.txt
uv pip compile requirements-pi.in --index-url https://pypi.org/simple --python-version 3.11 --universal --generate-hashes -o requirements-pi.txt
```

Review Dependabot changes to every affected lock. Dependabot's pip updater uses pip-compile, while the commands above use uv's universal resolver. Check cross-platform markers and hashes, then run both Python CI jobs. Do not remove hash enforcement or suppress an audit failure to merge an update.

## Controller and model changes

Add regression coverage for changed behavior, especially stale feedback, stop paths, output bounds, model scaling or persistence. Keep the training schema, model filenames and controller loader consistent. Describe label provenance accurately and use separate recording sessions for training and evaluation when reporting experimental results.

## Documentation and media

Use actual screenshots for interface figures. Label simulations and conceptual animations explicitly. Hardware performance claims need preserved measurements, calibration, load conditions and the exact commit. Keep historical paper claims separate from the behavior of current code.

Original code and repository documentation use the [MIT license](LICENSE). Preserve upstream notices when including third-party material, and follow the [paper's CC BY 4.0 terms](LICENSES/README.md) when reusing its text or figures. Contributions must be material you have permission to submit under the applicable terms.

For vulnerabilities, follow [SECURITY.md](SECURITY.md).

## Releases

Update `VERSION`, the software version and date in `CITATION.cff`, and the matching dated section in `CHANGELOG.md` together. Keep the README release link current. The paper's preferred citation keeps its published version and DOI.

On a push to `main` that changes `VERSION`, CI publishes a GitHub source release only after both Python jobs and CodeQL pass. The tag points to the checked commit, and release notes come from the matching changelog section. Existing tags must resolve to that same commit; the release step never moves a tag.
