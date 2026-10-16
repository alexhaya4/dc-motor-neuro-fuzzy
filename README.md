# Neuro-Fuzzy DC Motor Control

[![Software checks](https://github.com/alexhaya4/dc-motor-neuro-fuzzy/actions/workflows/security-audit.yml/badge.svg)](https://github.com/alexhaya4/dc-motor-neuro-fuzzy/actions/workflows/security-audit.yml)
[MIT license](LICENSE)

A Python application for studying DC motor-speed control with PI, PID, Mamdani fuzzy and neural-tuned fuzzy controllers. The maintained hardware path uses a Raspberry Pi, an L298N driver and an IR pulse sensor. The desktop interface displays measured speed and commanded PWM.

**Validation scope:** software tests cover controller behavior, real TensorFlow training and model round trips, GPIO protocol handling, watchdog behavior and offline Qt startup. GPIO tests use test adapters; they do not validate a physical motor rig. Raspberry Pi installation, sensor calibration and controller tuning must be checked on the target hardware.

## Install and inspect without hardware

Use Python 3.11 or 3.12 on a 64-bit system.

```bash
git clone https://github.com/alexhaya4/dc-motor-neuro-fuzzy.git
cd dc-motor-neuro-fuzzy
./install.sh
./run.sh --offline
```

Offline inspection opens the interface with motor controls disabled. It does not open GPIO or generate speed readings. `python dc_motor_gui.py` delegates to the same maintained launcher.

## Run on a Raspberry Pi

The GPIO backend targets Raspberry Pi 3/4 with 64-bit Raspberry Pi OS. Raspberry Pi 5 support is not established. On ARM, Qt comes from the operating system; the installer creates a virtual environment that can access it.

```bash
sudo apt install python3-venv python3-dev python3-pyqt5 build-essential
./install.sh --hardware
cp .env.example .env
```

Review `.env` before enabling the motor. Set the measured maximum RPM, sensor pulses per revolution, debounce interval, PWM frequency and controller gains for the actual rig. The supplied values are configuration defaults, not a calibration or a validated tuning result.

| Connection | Default BCM GPIO |
| --- | ---: |
| L298N IN1 | 17 |
| L298N IN2 | 18 |
| L298N ENA | 12 |
| IR sensor output | 23 |

The driver and motor require an appropriate power supply and a common reference with the Pi. Verify sensor-output voltage compatibility with the Pi before connection. The maintained path uses one sensor; the second configured pin is reserved.

```bash
./run.sh
```

Output starts at zero. Enabling requires a fresh sensor sample. Stop, stale feedback, controller replacement and shutdown disable output. An independent software watchdog disables output when PWM writes stall. Use a physical disconnect as well; software tests do not establish electrical safety or real-time guarantees.

## Collect data and train

```bash
.venv/bin/python improved_data_collection.py
.venv/bin/python train_networks.py --data data/training_data.json --models models
```

Collection uses measured GPIO feedback and actual PWM writes. Scaling-factor labels are heuristic and identified in the dataset metadata. They are not measured optimal gains or evidence that neural tuning improves control. The collector writes the same schema consumed by the trainer.

Training stores `error_scale.keras`, `delta_error_scale.keras` and `output_scale.keras` with SHA-256 sidecars. Input normalization is part of newly trained models, and the controller uses the trainer's filenames and output scaling. Checksum-verified legacy `.h5` files can also load. Only load trusted models; sidecars check file consistency, not authorship. Without a complete set of requested models, the interface explicitly reports fuzzy-only operation.

`data_collection.py` delegates to the maintained collector. Its Python `DataCollector` alias now takes `config` and `hardware`, replacing the old positional GPIO/PWM constructor. The older `NeuralFuzzyController` and `NeuroFuzzyController` import names delegate to the maintained controller; heuristic functions no longer masquerade as neural networks.

## Relay tuning

```bash
.venv/bin/python auto_tuner.py
```

This operates the connected motor. It derives candidate Ziegler-Nichols gains from observed relay crossings, always disables output on exit, and fails if usable oscillations are absent. Candidate gains still need validation for the motor, load and sampling interval. Saving gains updates `.env`; restart the application to apply them.

Performance metrics distinguish missing data from zero error. Settling requires an observed in-band tail lasting at least one second, and resets after an excursion or target change. A composite performance score is not reported because no validated scoring protocol is defined.

## Development

```bash
.venv/bin/python -m pip install --require-hashes -r requirements-dev.txt
.venv/bin/python -m pytest
.venv/bin/python -m ruff check --select E9,F63,F7,F82 .
.venv/bin/python -m pip_audit --disable-pip --require-hashes -r requirements.txt
```

CI tests Python 3.11 and 3.12, runs the Qt checks offscreen, audits both runtime and GPIO dependency locks, and runs CodeQL. Test, lint and audit failures fail the workflow. Plain `pytest` collects only `tests/`; root-level hardware diagnostic scripts are manual utilities.

Runtime, development and Pi dependencies have separate hash-locked files. Direct versions are maintained in the corresponding `.in` files. NumPy and SciPy pins retain Python 3.11 compatibility. Regenerate each lock after changing its input:

```bash
uv pip compile requirements.in --python-version 3.11 --universal --generate-hashes -o requirements.txt
uv pip compile requirements-dev.in --python-version 3.11 --universal --generate-hashes -o requirements-dev.txt
uv pip compile requirements-pi.in --python-version 3.11 --universal --generate-hashes -o requirements-pi.txt
```

`integration_example.py` is a separate mathematical simulation example, not a hardware recording. Advanced plotting and educational modules are separate components; the maintained launcher does not claim that every historical prototype is integrated. Earlier implementation-summary documents describe historical work and may not match the current entry points.

## Copy source to a Pi

```bash
./deploy_to_pi.sh USER@HOST
```

Replace `USER@HOST` with the Pi's SSH address. The script copies source to `dc-motor-neuro-fuzzy/`; it does not start a motor or install packages remotely. It excludes local environments, `.env`, models, datasets and logs. Run `./install.sh --hardware` on the Pi afterward. Windows users can invoke the accompanying batch wrapper through WSL.

## Citation

If you use this software in your research, please cite it as:

> A. O. Haya, "A Neural-Tuned Fuzzy Controller for DC Motor Speed Regulation: An Open-Source Educational Platform on Raspberry Pi," Zenodo, May 11, 2026, version 1.0.0, doi: 10.5281/zenodo.20124685.

<details>
<summary>BibTeX</summary>

```bibtex
@software{haya2026neuraltunefuzzy,
  author       = {Haya, A. O.},
  title        = {A Neural-Tuned Fuzzy Controller for DC Motor Speed Regulation: An Open-Source Educational Platform on Raspberry Pi},
  year         = {2026},
  month        = may,
  publisher    = {Zenodo},
  version      = {1.0.0},
  doi          = {10.5281/zenodo.20124685},
  url          = {https://doi.org/10.5281/zenodo.20124685}
}
```

</details>
