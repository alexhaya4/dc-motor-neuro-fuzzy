"""Limits and default timing shared by the maintained control and training paths."""

# Speed and Control Limits
MAX_SPEED_PERCENT = 100.0
MIN_SPEED_PERCENT = 0.0
MAX_PWM_DUTY_CYCLE = 100.0
MIN_PWM_DUTY_CYCLE = 0.0

# Numerical Stability
MIN_TIMESTEP_SECONDS = 1e-6  # Minimum time delta to prevent division by zero

# Performance Metrics
SETTLING_TIME_TOLERANCE_PERCENT = 5.0  # Within 5% of target is considered "settled"
STEADY_STATE_SAMPLES = 50  # Number of samples to collect for steady-state analysis
STEADY_STATE_START_TIME_SEC = 5.0  # Start collecting steady-state data after 5 seconds

# PID Controller
DEFAULT_DERIVATIVE_FILTER_ALPHA = 0.1  # Exponential moving average filter for derivative term

# Fuzzy Logic
FUZZY_UNIVERSE_MIN = -100.0
FUZZY_UNIVERSE_MAX = 100.0
FUZZY_ERROR_CLAMP_MIN = -100.0
FUZZY_ERROR_CLAMP_MAX = 100.0

# Neural Network Scaling Factors
NN_ERROR_SCALE_MIN = 0.5
NN_ERROR_SCALE_MAX = 2.0
NN_DELTA_ERROR_SCALE_MIN = 0.5
NN_DELTA_ERROR_SCALE_MAX = 2.0
NN_OUTPUT_SCALE_MIN = 0.5
NN_OUTPUT_SCALE_MAX = 1.5

# Thread and Sensor Configuration
SPEED_SENSOR_SMOOTHING_SAMPLES = 5  # Number of samples for moving average
SPEED_MEASUREMENT_DURATION_SEC = 0.5  # Duration to count pulses
SENSOR_POLL_INTERVAL_SEC = 0.1  # 100ms between sensor readings
CONTROL_LOOP_INTERVAL_SEC = 0.01  # 100Hz control loop (10ms)
SPEED_SENSOR_SLEEP_MICROSEC = 0.0001  # 100 microseconds for IR sensor polling

# GUI and Plotting
PLOT_MAX_POINTS = 300  # 30 seconds at 10Hz = 300 points

# File and Security Limits
MAX_LOG_FILE_READ_BYTES = 100_000  # Read only last 100KB of log files
MODEL_CHECKSUM_ALGORITHM = 'sha256'  # Algorithm for model file verification
MAX_JSON_FILE_SIZE_BYTES = 10_000_000  # 10MB max for JSON training data

# GPIO Pin Limits (Raspberry Pi BCM mode)
VALID_GPIO_PIN_MIN = 2
VALID_GPIO_PIN_MAX = 27
VALID_GPIO_PINS = list(range(VALID_GPIO_PIN_MIN, VALID_GPIO_PIN_MAX + 1))

# Watchdog Configuration
WATCHDOG_TIMEOUT_SEC = 1.0  # Disable motor if no update in 1 second
WATCHDOG_CHECK_INTERVAL_SEC = 0.1  # Check watchdog every 100ms
