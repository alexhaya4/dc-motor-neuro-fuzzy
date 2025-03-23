import RPi.GPIO as GPIO
import time
import threading

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

# Global variables for speed measurement
pulse_count = 0
speed_rpm = 0
running = True

# Constants for speed calculation
PULSES_PER_REVOLUTION = 1  # Adjust based on your reflective strip setup
SAMPLE_TIME_SECONDS = 1.0  # Time window to count pulses

# Callback function for IR sensor detection
def count_pulse(channel):
    global pulse_count
    pulse_count += 1

# Function to calculate speed in a separate thread
def calculate_speed():
    global pulse_count, speed_rpm, running
    
    while running:
        # Reset counter
        pulse_count = 0
        
        # Wait for the sample period
        time.sleep(SAMPLE_TIME_SECONDS)
        
        # Calculate RPM: (pulses / pulses_per_rev) / sample_time * 60
        rpm = (pulse_count / PULSES_PER_REVOLUTION) / SAMPLE_TIME_SECONDS * 60
        speed_rpm = rpm
        
        print(f"Speed: {speed_rpm:.2f} RPM, Pulses: {pulse_count}")

# Setup interrupt for IR sensor
GPIO.add_event_detect(IR_SENSOR_PIN, GPIO.FALLING, callback=count_pulse)

# Start speed calculation thread
speed_thread = threading.Thread(target=calculate_speed)
speed_thread.daemon = True  # Thread will terminate when main program exits
speed_thread.start()

try:
    print("Testing motor speed sensing...")
    
    # Run motor at different speeds and observe RPM
    speeds = [30, 50, 70, 90]
    
    # Forward direction
    GPIO.output(MOTOR_PIN1, GPIO.HIGH)
    GPIO.output(MOTOR_PIN2, GPIO.LOW)
    
    for duty_cycle in speeds:
        print(f"\nSetting motor to {duty_cycle}% duty cycle")
        motor_pwm.ChangeDutyCycle(duty_cycle)
        time.sleep(5)  # Allow speed to stabilize and get multiple readings
    
    # Stop the motor
    print("\nStopping motor")
    motor_pwm.ChangeDutyCycle(0)
    time.sleep(2)
    
    print("\nSpeed sensor test complete")
    
except KeyboardInterrupt:
    print("Test interrupted")
finally:
    running = False  # Signal the speed calculation thread to exit
    motor_pwm.stop()
    GPIO.cleanup()
    print("GPIO cleaned up")
