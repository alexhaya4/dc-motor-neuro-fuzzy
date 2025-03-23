import numpy as np
import time
import RPi.GPIO as GPIO
import json
import os

class DataCollector:
    def __init__(self, motor_pin1, motor_pin2, motor_pwm_pin, ir_sensor_pin, existing_pwm=None):
        self.MOTOR_PIN1 = motor_pin1
        self.MOTOR_PIN2 = motor_pin2
        self.MOTOR_PWM_PIN = motor_pwm_pin
        self.IR_SENSOR_PIN = ir_sensor_pin
        self.pulses_per_revolution = 1  # Adjust based on your setup
        self.max_rpm = 100  # Adjust based on your motor
        
        # Setup GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.MOTOR_PIN1, GPIO.OUT)
        GPIO.setup(self.MOTOR_PIN2, GPIO.OUT)
        GPIO.setup(self.MOTOR_PWM_PIN, GPIO.OUT)
        GPIO.setup(self.IR_SENSOR_PIN, GPIO.IN)
        
        # Use existing PWM or create new one
        if existing_pwm:
            self.motor_pwm = existing_pwm
            self.owns_pwm = False
        else:
            self.motor_pwm = GPIO.PWM(self.MOTOR_PWM_PIN, 100)  # 100 Hz frequency
            self.motor_pwm.start(0)  # Start with 0% duty cycle
            self.owns_pwm = True
        
        # Set motor direction to forward
        GPIO.output(self.MOTOR_PIN1, GPIO.HIGH)
        GPIO.output(self.MOTOR_PIN2, GPIO.LOW)
        
        # For storing training data
        self.training_data = []
        
    def measure_speed(self, duration=0.5):
        """Measure speed by counting pulses for the specified duration."""
        pulse_count = 0
        last_state = GPIO.input(self.IR_SENSOR_PIN)
        
        start_time = time.time()
        end_time = start_time + duration
        
        while time.time() < end_time:
            current_state = GPIO.input(self.IR_SENSOR_PIN)
            # Detect falling edge (transition from HIGH to LOW)
            if current_state == 0 and last_state == 1:
                pulse_count += 1
            last_state = current_state
            # Small delay to prevent CPU hogging
            time.sleep(0.0001)
        
        # Calculate RPM
        duration_actual = time.time() - start_time
        rpm = (pulse_count / self.pulses_per_revolution) / duration_actual * 60
        return rpm
    
    def collect_data_point(self, target_speed, pwm_value, error, delta_error, error_scale, delta_error_scale, output_scale):
        """Collect a single data point for training."""
        actual_speed = self.measure_speed()
        normalized_speed = min(100, max(0, (actual_speed / self.max_rpm) * 100))
        
        data_point = {
            'target_speed': target_speed,
            'actual_speed': normalized_speed,
            'raw_speed': actual_speed,
            'pwm': pwm_value,
            'error': error,
            'delta_error': delta_error,
            'error_scale': error_scale,
            'delta_error_scale': delta_error_scale,
            'output_scale': output_scale
        }
        
        self.training_data.append(data_point)
        return data_point
    
    def collect_training_data_auto(self):
        """Automatically collect training data across different speeds and conditions."""
        print("Starting automatic data collection...")
        target_speeds = [10, 20, 30, 40, 50, 60, 70, 80, 90]
        
        # For tracking error changes
        prev_error = 0
        
        for target in target_speeds:
            print(f"Testing target speed: {target}%")
            
            # Test with different PWM values around the target
            for pwm_offset in [-20, -10, 0, 10, 20]:
                pwm = max(0, min(100, target + pwm_offset))
                print(f"  Setting PWM to {pwm}%")
                
                # Apply PWM
                self.motor_pwm.ChangeDutyCycle(pwm)
                
                # Wait for speed to stabilize
                time.sleep(2)
                
                # Measure actual speed
                actual_speed = self.measure_speed()
                normalized_speed = min(100, max(0, (actual_speed / self.max_rpm) * 100))
                
                # Calculate error and delta_error
                error = target - normalized_speed
                delta_error = error - prev_error
                prev_error = error
                
                # Start with default scale values
                error_scale = 1.0
                delta_error_scale = 1.0
                output_scale = 1.0
                
                # Adjust scales based on performance (this is simplified)
                if abs(error) > 20:
                    error_scale = 1.5  # Increase error scaling for large errors
                
                if abs(delta_error) > 10:
                    delta_error_scale = 1.3  # Increase delta error scaling for rapid changes
                
                if abs(error) < 5:
                    output_scale = 0.9  # Decrease output scaling for fine-tuning
                
                # Collect data point
                data_point = self.collect_data_point(
                    target, pwm, error, delta_error, 
                    error_scale, delta_error_scale, output_scale
                )
                
                print(f"  Data point: Target={target}%, Actual={actual_speed:.2f} RPM, Error={error:.2f}")
                
                # Short delay
                time.sleep(0.5)
            
            # Stop motor briefly between speed targets
            self.motor_pwm.ChangeDutyCycle(0)
            time.sleep(1)
        
        print(f"Data collection complete. Collected {len(self.training_data)} data points.")
        return self.training_data
    
    def save_training_data(self, filename="training_data.json"):
        """Save collected training data to a file."""
        with open(filename, 'w') as f:
            json.dump(self.training_data, f, indent=2)
        print(f"Training data saved to {filename}")
    
    def cleanup(self):
        """Clean up GPIO and stop motor."""
        self.motor_pwm.ChangeDutyCycle(0)
        if self.owns_pwm:
            self.motor_pwm.stop()
        # Don't call GPIO.cleanup() here as other components are using GPIO
        print("Motor stopped")

if __name__ == "__main__":
    # Define pin constants
    MOTOR_PIN1 = 17  # Connect to IN1 of L298N
    MOTOR_PIN2 = 18  # Connect to IN2 of L298N
    MOTOR_PWM_PIN = 12  # Connect to ENA of L298N
    IR_SENSOR_PIN = 23  # Connect to output pin of IR sensor
    
    collector = DataCollector(MOTOR_PIN1, MOTOR_PIN2, MOTOR_PWM_PIN, IR_SENSOR_PIN)
    
    try:
        collector.collect_training_data_auto()
        collector.save_training_data()
    except KeyboardInterrupt:
        print("Data collection interrupted")
    finally:
        collector.cleanup()
