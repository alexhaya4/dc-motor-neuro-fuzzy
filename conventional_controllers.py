import time

class PIController:
    def __init__(self, kp=1.0, ki=0.5):
        self.kp = kp  # Proportional gain
        self.ki = ki  # Integral gain
        
        # For controller state
        self.integral = 0
        self.prev_error = 0
        self.prev_time = time.time()
        
        # Limits
        self.integral_limit = 100  # Anti-windup limit
    
    def compute_output(self, target_speed, current_speed):
        # Time delta
        current_time = time.time()
        dt = current_time - self.prev_time
        self.prev_time = current_time
        
        # Calculate error
        error = target_speed - current_speed
        
        # Update integral term with anti-windup
        self.integral += error * dt
        self.integral = max(min(self.integral, self.integral_limit), -self.integral_limit)
        
        # Calculate output
        p_term = self.kp * error
        i_term = self.ki * self.integral
        
        output = p_term + i_term
        
        # Limit output to 0-100 range
        output = max(min(output, 100), 0)
        
        # Store error for next iteration
        self.prev_error = error
        
        return output
    
    def reset(self):
        """Reset controller state"""
        self.integral = 0
        self.prev_error = 0
        self.prev_time = time.time()


class PIDController:
    def __init__(self, kp=1.0, ki=0.5, kd=0.2):
        self.kp = kp  # Proportional gain
        self.ki = ki  # Integral gain
        self.kd = kd  # Derivative gain
        
        # For controller state
        self.integral = 0
        self.prev_error = 0
        self.prev_time = time.time()
        
        # Limits
        self.integral_limit = 100  # Anti-windup limit
    
    def compute_output(self, target_speed, current_speed):
        # Time delta
        current_time = time.time()
        dt = current_time - self.prev_time
        self.prev_time = current_time
        
        # Calculate error
        error = target_speed - current_speed
        
        # Update integral term with anti-windup
        self.integral += error * dt
        self.integral = max(min(self.integral, self.integral_limit), -self.integral_limit)
        
        # Calculate derivative term
        if dt > 0:  # Avoid division by zero
            derivative = (error - self.prev_error) / dt
        else:
            derivative = 0
        
        # Calculate output
        p_term = self.kp * error
        i_term = self.ki * self.integral
        d_term = self.kd * derivative
        
        output = p_term + i_term + d_term
        
        # Limit output to 0-100 range
        output = max(min(output, 100), 0)
        
        # Store error for next iteration
        self.prev_error = error
        
        return output
    
    def reset(self):
        """Reset controller state"""
        self.integral = 0
        self.prev_error = 0
        self.prev_time = time.time()
