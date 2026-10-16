# Setup and operation

Start with the [README](../README.md) for the project scope, visual overview and validation status.

## Raspberry Pi setup

Use Raspberry Pi 3/4, 64-bit Raspberry Pi OS and Python 3.11 or 3.12. Pi 5 support is not established. ARM Qt bindings come from the operating system, so the hardware installer creates a virtual environment with access to system packages.

```bash
sudo apt install python3-venv python3-dev python3-pyqt5 build-essential
./install.sh --hardware
cp .env.example .env
```

The OS interpreter and its PyQt5 package must use a supported Python version. An OS image with a different default Python is not covered by this setup.

### Wiring and calibration

Disconnect motor power before checking wiring. The following are configuration defaults, expressed as BCM GPIO numbers:

| Signal | Default pin |
| --- | ---: |
| L298N IN1 | 17 |
| L298N IN2 | 18 |
| L298N ENA | 12 |
| IR sensor output | 23 |

Provide a suitable motor supply and a common reference with the Pi. Verify sensor-output voltage compatibility with the Pi. The maintained speed path uses one sensor; the second configured sensor pin is reserved. Use a physical power disconnect.

Review `.env` against the actual rig:

| Setting | Meaning |
| --- | --- |
| `MOTOR_MAX_RPM` | Calibrated RPM corresponding to 100% displayed speed |
| `MOTOR_PULSES_PER_REV` | Sensor pulses per mechanical revolution |
| `MOTOR_PWM_FREQ` | PWM frequency in hertz |
| `MOTOR_MIN_PULSE_WIDTH` | Debounce interval in milliseconds |
| `GPIO_*` | Distinct, valid BCM pins for the connected driver and sensor |
| `CONTROLLER_PI_*`, `CONTROLLER_PID_*` | Gains requiring validation for the motor and load |

Defaults are examples, not calibration results. Target and displayed speed are percentages of configured maximum RPM; commanded PWM is duty cycle in percent.

```bash
./run.sh
```

Output starts at zero. Enabling requires a fresh sensor sample. Stop, stale feedback, controller replacement and shutdown disable output. A separate watchdog disables PWM when writes stall. These software paths still require validation on the actual driver and motor.

## Collect data and train

Collection operates the connected motor. Complete the wiring and calibration checks first.

```bash
.venv/bin/python improved_data_collection.py
.venv/bin/python train_networks.py --data data/training_data.json --models models
```

The collector records actual PWM writes and measured GPIO feedback. Scaling-factor labels are heuristic and identified as such in dataset metadata. They are not measured optimal gains. The collector and trainer share a dataset schema; invalid shapes, non-finite values and out-of-range inputs are rejected.

| Model | Role |
| --- | --- |
| `error_scale.keras` | Scale the error entering fuzzy inference |
| `delta_error_scale.keras` | Scale the change in error entering fuzzy inference |
| `output_scale.keras` | Scale the fuzzy control output |

Each model has a SHA-256 sidecar. Newly trained models contain their input normalization, so callers supply raw percentages. Checksum-verified legacy `.h5` models can also load. Use trusted files; integrity checks are not author authentication. A missing or invalid requested model causes explicit fuzzy-only operation.

`data_collection.py` is a compatibility adapter. Its `DataCollector` alias now takes `config` and `hardware`, replacing the old positional GPIO/PWM constructor. `NeuralFuzzyController` and `NeuroFuzzyController` delegate to the maintained implementation.

## Relay tuning

```bash
.venv/bin/python auto_tuner.py
```

This operates the motor. The tuner uses measured relay crossings to derive candidate Ziegler-Nichols gains, disables output on exit and fails when usable oscillations are absent. It does not prove that the resulting gains are stable or optimal for another speed, load or sampling interval.

Saving gains updates `.env`. Restart the application to apply them. Relay tuning does not create validated scaling-factor labels for neural training.

## Interpret performance metrics

Missing observations are unavailable rather than zero. Settling requires an observed in-band tail lasting at least one second and resets after an excursion or a target change. Steady-state observations are gathered after five seconds. No composite performance score is defined.

Use recorded measurements, repeatable load conditions and the exact software commit when comparing controllers. The repository does not contain a validated comparative hardware benchmark for the maintenance revision.

## Copy source to a Pi

```bash
./deploy_to_pi.sh USER@HOST
```

Replace `USER@HOST` with the Pi's SSH address. The script copies source into `dc-motor-neuro-fuzzy/`; it does not install packages or start the motor remotely. It excludes environments, `.env`, models, datasets and logs. Install on the Pi afterward with `./install.sh --hardware`.

Windows users can use the batch wrapper through WSL. Windows-to-Pi transfer has not been validated in the software test environment.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| Installer rejects Python | Select Python 3.11 or 3.12 with `PYTHON=python3.12 ./install.sh`. |
| Qt cannot open a display | Run in a graphical session or WSLg; `QT_QPA_PLATFORM=offscreen` is for tests, not interactive use. |
| Hardware is unavailable on a desktop | Use `./run.sh --offline`. |
| Neural mode shows fuzzy-only | Check the configured models directory and all requested model/sidecar pairs. |
| Output is disabled after a timeout | Inspect feedback, controller errors and logs before explicitly rearming. |
| Reported speed is inconsistent | Verify pulses per revolution, maximum RPM, sensor voltage, debounce and sensor alignment. |
