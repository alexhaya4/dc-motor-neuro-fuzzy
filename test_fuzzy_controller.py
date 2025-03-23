import RPi.GPIO as GPIO
import time
from fuzzy_controller import FuzzyController

# Set GPIO numbering mode
GPIO.setmode(GPIO.BCM)

# Define pin constants
MOTOR_PIN1 = 17  # Connect to IN1 of L298N
MOTOR_PIN2 = 18  # Connect to IN2 of L298N
MOTOR_PWM_PIN = 12  # Connect to ENA of L298N
IR_SENSOR_PIN = 23  # Connect to output pin of IR sensor

# Setup GPIO pins
GPIO.setup(MOTOR_PIN1, GPIO.OUT)
GPIO.setup(MOTOR_PIN2, GPIO.OUT)
GPIO.setup(MOTOR_PWM_PIN, GPIO.OUT)
GPIO.setup(IR_SENSOR_PIN, GPIO.IN)

# Setup PWM on the enable pin
motor_pwm = GPIO.PWM(MOTOR_PWM_PIN, 100)  # 100 Hz frequency
motor_pwm.start(0)  # Start with 0% duty cycle

def measure_speed(duration=0.5):
    """Measure speed by counting pulses for the specified duration."""
    pulse_count = 0
    last_state = GPIO.input(IR_SENSOR_PIN)
    
    start_time = time.time()
    end_time = start_time + duration
    
    while time.time() < end_time:
        current_state = GPIO.input(IR_SENSOR_PIN)
        # Detect falling edge (transition from HIGH to LOW)
        if current_state == 0 and last_state == 1:
            pulse_count += 1
        last_state = current_state
        # Small delay to prevent CPU hogging
        time.sleep(0.0001)
    
    # Calculate RPM
    pulses_per_revolution = 1  # Adjust based on your setup
    rpm = (pulse_count / pulses_per_revolution) / duration * 60
    
    return rpm

def rpm_to_normalized_value(rpm, max_rpm=100):
    """Convert RPM to a normalized value (0-100)."""
    return min(100, max(0, (rpm / max_rpm) * 100))

try:
    # Initialize fuzzy controller
    fuzzy_controller = FuzzyController()
    
    # Set target speed (in normalized units)
    target_speed = 50  # 50% of max speed
    
    # For storing previous error for delta_error calculation
    prev_error = 0
    
    # Set direction to forward
    GPIO.output(MOTOR_PIN1, GPIO.HIGH)
    GPIO.output(MOTOR_PIN2, GPIO.LOW)
    
    print("Starting fuzzy controller test...")
    print(f"Target speed: {target_speed}%")
    
    # Control loop
    for i in range(30):  # Run for 30 iterations
        # Measure current speed
        current_rpm = measure_speed()
        current_speed = rpm_to_normalized_value(current_rpm)
        
        # Calculate error and delta_error
        error = target_speed - current_speed
        delta_error = error - prev_error
        prev_error = error
        
        # Compute fuzzy controller output
        pwm_output = fuzzy_controller.compute_output(error, delta_error)
        
        # Apply PWM output to motor
        motor_pwm.ChangeDutyCycle(pwm_output)
        
        # Print current status
        print(f"Iteration {i+1}: Speed={current_rpm:.2f} RPM ({current_speed:.2f}%), " +
              f"Error={error:.2f}, DeltaError={delta_error:.2f}, PWM={pwm_output:.2f}%")
        
        # Short delay
        time.sleep(1)
    
    # Change target speed after 30 iterations
    target_speed = 75  # 75% of max speed
    print(f"\nChanging target speed to {target_speed}%")
    
    for i in range(30):  # Run for another 30 iterations
        # Measure current speed
        current_rpm = measure_speed()
        current_speed = rpm_to_normalized_value(current_rpm)
        
        # Calculate error and delta_error
        error = target_speed - current_speed
        delta_error = error - prev_error
        prev_error = error
        
        # Compute fuzzy controller output
        pwm_output = fuzzy_controller.compute_output(error, delta_error)
        
        # Apply PWM output to motor
        motor_pwm.ChangeDutyCycle(pwm_output)
        
        # Print current status
        print(f"Iteration {i+31}: Speed={current_rpm:.2f} RPM ({current_speed:.2f}%), " +
              f"Error={error:.2f}, DeltaError={delta_error:.2f}, PWM={pwm_output:.2f}%")
        
        # Short delay
        time.sleep(1)
    
    # Stop the motor
    print("\nStopping motor")
    motor_pwm.ChangeDutyCycle(0)
    
except KeyboardInterrupt:
    print("Test interrupted")
finally:
    motor_pwm.stop()
    GPIO.cleanup()
    print("GPIO cleaned up")
