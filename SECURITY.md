# Security Policy

## Supported Versions

We release patches for security vulnerabilities in the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 2.2.x   | :white_check_mark: |
| 2.0.x   | :white_check_mark: |
| < 2.0   | :x:                |

## Reporting a Vulnerability

We take the security of DC Motor Control System seriously. If you believe you have found a security vulnerability, please report it to us as described below.

### Where to Report

**Please do NOT report security vulnerabilities through public GitHub issues.**

Instead, please report them via email to: [your-security-email@example.com]

You should receive a response within 48 hours. If for some reason you do not, please follow up via email to ensure we received your original message.

### What to Include

Please include the following information in your report:

- Type of vulnerability (e.g., buffer overflow, SQL injection, cross-site scripting, etc.)
- Full paths of source file(s) related to the manifestation of the vulnerability
- The location of the affected source code (tag/branch/commit or direct URL)
- Any special configuration required to reproduce the issue
- Step-by-step instructions to reproduce the issue
- Proof-of-concept or exploit code (if possible)
- Impact of the issue, including how an attacker might exploit it

### What to Expect

- **Acknowledgment**: We will acknowledge your email within 48 hours
- **Updates**: We will keep you informed about our progress toward a fix
- **Verification**: We will notify you when the vulnerability has been fixed and may ask you to verify the fix
- **Credit**: We will credit you in the security advisory (unless you prefer to remain anonymous)

## Security Best Practices for Users

### Hardware Safety

1. **GPIO Pin Validation**: Ensure all GPIO pin configurations are valid before deployment
2. **Watchdog Timer**: The system includes a watchdog timer that will disable the motor if the control loop hangs (default: 1 second timeout)
3. **Emergency Stop**: Always have physical emergency stop button connected to your motor circuit
4. **Current Limiting**: Implement hardware-level current limiting to protect the motor and driver

### Software Security

1. **Model File Integrity**: The system verifies neural network model files using SHA-256 checksums. Do not disable this verification.
2. **Environment Variables**: Validate all environment variables in `.env` file:
   - GPIO pins must be in valid BCM range (2-27)
   - Paths must be within the project directory
3. **Log Files**: The system limits log file reading to 100KB to prevent memory exhaustion
4. **Dependencies**: Keep dependencies updated, especially TensorFlow which should be on a version with active security support

### Configuration Security

```bash
# Example secure .env configuration
GPIO_MOTOR_IN1=17    # Valid BCM pin
GPIO_MOTOR_IN2=18    # Valid BCM pin
GPIO_MOTOR_ENA=12    # Valid BCM pin
GPIO_IR_SENSOR=23    # Valid BCM pin

# Use absolute paths within project directory
APP_BASE_DIR=/home/pi/DC-Motor_v2.0
APP_MODELS_DIR=/home/pi/DC-Motor_v2.0/models
APP_LOGS_DIR=/home/pi/DC-Motor_v2.0/logs
```

### Known Security Considerations

1. **TensorFlow Version**: The default `requirements.txt` uses TensorFlow 2.15.0. For production deployments, update to the latest version with security patches:
   ```bash
   pip install tensorflow==2.18.0  # or latest
   ```

2. **Keras Model Loading**: The system loads Keras `.h5` model files which can contain pickled Python objects. Only load models from trusted sources.

3. **Development Mode**: When running on non-Raspberry Pi systems, GPIO is mocked. Do not deploy mock GPIO code to production.

## Security Updates

Security updates will be released as patch versions (e.g., 2.2.1, 2.2.2) and documented in:
- `CHANGELOG.md`
- GitHub Security Advisories
- Release notes

## Vulnerability Disclosure Timeline

1. **Day 0**: Vulnerability reported
2. **Day 1-2**: Acknowledgment sent to reporter
3. **Day 3-14**: Investigation and fix development
4. **Day 15-30**: Coordinated disclosure with reporter
5. **Day 30+**: Public disclosure and patch release

## Security Audit History

| Date       | Type          | Findings | Status   |
|------------|---------------|----------|----------|
| 2026-01-24 | Code Audit    | 19 items | Fixed    |

## Contact

For security-related questions or concerns:
- Email: [your-security-email@example.com]
- PGP Key: [Optional - link to PGP key]

---

**Note**: This security policy applies to the DC Motor Control System codebase. For hardware-related safety concerns, consult with a qualified electrical engineer before deployment.
