import RPi.GPIO as GPIO
import time
import sys

# Define pin constants
MOTOR_PIN1 = 17  # Connect to IN1 of L298N
MOTOR_PIN2 = 18  # Connect to IN2 of L298N
MOTOR_PWM_PIN = 12  # Connect to ENA of L298N
IR_SENSOR_PIN = 23  # Connect to output pin of IR sensor

def setup():
    # Setup GPIO
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(MOTOR_PIN1, GPIO.OUT)
    GPIO.setup(MOTOR_PIN2, GPIO.OUT)
    GPIO.setup(MOTOR_PWM_PIN, GPIO.OUT)
    GPIO.setup(IR_SENSOR_PIN, GPIO.IN)
    
    # Create PWM object
    motor_pwm = GPIO.PWM(MOTOR_PWM_PIN, 100)  # 100 Hz frequency
    motor_pwm.start(0)  # Start with 0% duty cycle
    
    # Set motor direction to forward
    GPIO.output(MOTOR_PIN1, GPIO.HIGH)
    GPIO.output(MOTOR_PIN2, GPIO.LOW)
    
    return motor_pwm

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
    duration_actual = time.time() - start_time
    pulses_per_revolution = 1  # Adjust based on your setup
    rpm = (pulse_count / pulses_per_revolution) / duration_actual * 60
    return rpm, pulse_count

def main():
    motor_pwm = setup()
    print("DC Motor Control Test")
    print("---------------------")
    print("This program will test your motor by running it at different speeds")
    print("and measuring the rotation speed with the IR sensor.")
    
    try:
        # Test different PWM values
        for pwm in [0, 20, 40, 60, 80, 100, 80, 60, 40, 20, 0]:
            print(f"\nSetting PWM to {pwm}%")
            motor_pwm.ChangeDutyCycle(pwm)
            time.sleep(2)  # Wait for speed to stabilize
            
            # Measure speed multiple times
            for i in range(3):
                rpm, pulses = measure_speed()
                print(f"  Measured: {rpm:.2f} RPM (Pulses: {pulses})")
                time.sleep(0.2)
        
        print("\nTest complete")
        
    except KeyboardInterrupt:
        print("\nTest interrupted")
    finally:
        motor_pwm.stop()
        GPIO.cleanup()
        print("Motor stopped and GPIO cleaned up")

if __name__ == "__main__":
    main()
