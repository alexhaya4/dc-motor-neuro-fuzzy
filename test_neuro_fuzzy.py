import RPi.GPIO as GPIO
import time
from neuro_fuzzy_controller import NeuroFuzzyController

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
    # Initialize neuro-fuzzy controller
    controller = NeuroFuzzyController()
    
    # Set direction to forward
    GPIO.output(MOTOR_PIN1, GPIO.HIGH)
    GPIO.output(MOTOR_PIN2, GPIO.LOW)
    
    print("Starting neuro-fuzzy controller test...")
    
    # Test different target speeds
    targets = [30, 50, 70, 40, 60]
    
    for target in targets:
        print(f"\nChanging target speed to {target}%")
        
        # Run for each target for multiple iterations
        for i in range(15):
            # Measure current speed
            current_rpm = measure_speed()
            current_speed = rpm_to_normalized_value(current_rpm)
            
            # Compute controller output
            pwm_output = controller.compute_output(target, current_speed)
            
            # Apply PWM output to motor
            motor_pwm.ChangeDutyCycle(pwm_output)
            
            # Print current status
            print(f"Target={target}%, Speed={current_rpm:.2f} RPM ({current_speed:.2f}%), " +
                  f"PWM={pwm_output:.2f}%, Scales=[{controller.error_scale:.2f}, " +
                  f"{controller.delta_error_scale:.2f}, {controller.output_scale:.2f}]")
            
            # Short delay
            time.sleep(1)
    
    # Test with load changes
    # You can simulate a load change by physically applying resistance to the motor shaft
    print("\nTesting response to load changes at constant target...")
    target = 50
    print(f"Setting target speed to {target}%")
    
    for i in range(20):
        # Measure current speed
        current_rpm = measure_speed()
        current_speed = rpm_to_normalized_value(current_rpm)
        
        # Compute controller output
        pwm_output = controller.compute_output(target, current_speed)
        
        # Apply PWM output to motor
        motor_pwm.ChangeDutyCycle(pwm_output)
        
        # Print current status
        print(f"Target={target}%, Speed={current_rpm:.2f} RPM ({current_speed:.2f}%), " +
              f"PWM={pwm_output:.2f}%, Scales=[{controller.error_scale:.2f}, " +
              f"{controller.delta_error_scale:.2f}, {controller.output_scale:.2f}]")
        
        # Every 5 iterations, ask the user to apply or remove external load
        if i % 5 == 0 and i > 0:
            print("\n>>> Please apply or remove load to the motor now <<<\n")
            time.sleep(2)
        
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
