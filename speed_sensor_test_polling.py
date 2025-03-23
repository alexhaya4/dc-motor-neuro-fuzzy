import RPi.GPIO as GPIO
import time

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

def measure_speed(duration=1.0):
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
    
    return rpm, pulse_count

try:
    print("Testing motor speed sensing with polling...")
    
    # Run motor at different speeds and observe RPM
    speeds = [30, 50, 70, 90]
    
    # Forward direction
    GPIO.output(MOTOR_PIN1, GPIO.HIGH)
    GPIO.output(MOTOR_PIN2, GPIO.LOW)
    
    for duty_cycle in speeds:
        print(f"\nSetting motor to {duty_cycle}% duty cycle")
        motor_pwm.ChangeDutyCycle(duty_cycle)
        # Let motor speed stabilize
        time.sleep(2)
        
        # Take multiple measurements
        for i in range(3):
            rpm, pulses = measure_speed()
            print(f"Measurement {i+1}: Speed: {rpm:.2f} RPM, Pulses: {pulses}")
            time.sleep(0.5)
    
    # Stop the motor
    print("\nStopping motor")
    motor_pwm.ChangeDutyCycle(0)
    time.sleep(2)
    
    print("\nSpeed sensor test complete")
    
except KeyboardInterrupt:
    print("Test interrupted")
finally:
    motor_pwm.stop()
    GPIO.cleanup()
    print("GPIO cleaned up")
