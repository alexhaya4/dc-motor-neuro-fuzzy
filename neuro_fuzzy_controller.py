import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl

class NeuroFuzzyController:
    def __init__(self):
        # Initialize the fuzzy controller part
        self._initialize_fuzzy_controller()
        
        # Initialize neural network for scaling factors adaptation
        self._initialize_neural_network()
        
        # Initial scaling factors
        self.error_scale = 1.0
        self.delta_error_scale = 1.0
        self.output_scale = 1.0
        
        # For storing previous values
        self.prev_error = 0
        self.prev_speed = 0
    
    def _initialize_fuzzy_controller(self):
        """Initialize the fuzzy logic controller."""
        # Create fuzzy variables
        self.error = ctrl.Antecedent(np.arange(-100, 101, 1), 'error')
        self.delta_error = ctrl.Antecedent(np.arange(-100, 101, 1), 'delta_error')
        self.pwm_output = ctrl.Consequent(np.arange(0, 101, 1), 'pwm_output')
        
        # Define membership functions for inputs
        self.error['NB'] = fuzz.trapmf(self.error.universe, [-100, -100, -80, -40])
        self.error['NS'] = fuzz.trimf(self.error.universe, [-60, -30, 0])
        self.error['ZE'] = fuzz.trimf(self.error.universe, [-20, 0, 20])
        self.error['PS'] = fuzz.trimf(self.error.universe, [0, 30, 60])
        self.error['PB'] = fuzz.trapmf(self.error.universe, [40, 80, 100, 100])
        
        self.delta_error['NB'] = fuzz.trapmf(self.delta_error.universe, [-100, -100, -80, -40])
        self.delta_error['NS'] = fuzz.trimf(self.delta_error.universe, [-60, -30, 0])
        self.delta_error['ZE'] = fuzz.trimf(self.delta_error.universe, [-20, 0, 20])
        self.delta_error['PS'] = fuzz.trimf(self.delta_error.universe, [0, 30, 60])
        self.delta_error['PB'] = fuzz.trapmf(self.delta_error.universe, [40, 80, 100, 100])
        
        # Define membership functions for output
        self.pwm_output['VL'] = fuzz.trimf(self.pwm_output.universe, [0, 0, 25])
        self.pwm_output['LO'] = fuzz.trimf(self.pwm_output.universe, [0, 25, 50])
        self.pwm_output['ME'] = fuzz.trimf(self.pwm_output.universe, [25, 50, 75])
        self.pwm_output['HI'] = fuzz.trimf(self.pwm_output.universe, [50, 75, 100])
        self.pwm_output['VH'] = fuzz.trimf(self.pwm_output.universe, [75, 100, 100])
        
        # Define rules based on the research papers
        self.rules = [
            ctrl.Rule(self.error['NB'] & self.delta_error['NB'], self.pwm_output['VL']),
            ctrl.Rule(self.error['NB'] & self.delta_error['NS'], self.pwm_output['VL']),
            ctrl.Rule(self.error['NB'] & self.delta_error['ZE'], self.pwm_output['LO']),
            ctrl.Rule(self.error['NB'] & self.delta_error['PS'], self.pwm_output['LO']),
            ctrl.Rule(self.error['NB'] & self.delta_error['PB'], self.pwm_output['ME']),
            
            ctrl.Rule(self.error['NS'] & self.delta_error['NB'], self.pwm_output['VL']),
            ctrl.Rule(self.error['NS'] & self.delta_error['NS'], self.pwm_output['LO']),
            ctrl.Rule(self.error['NS'] & self.delta_error['ZE'], self.pwm_output['ME']),
            ctrl.Rule(self.error['NS'] & self.delta_error['PS'], self.pwm_output['ME']),
            ctrl.Rule(self.error['NS'] & self.delta_error['PB'], self.pwm_output['HI']),
            
            ctrl.Rule(self.error['ZE'] & self.delta_error['NB'], self.pwm_output['LO']),
            ctrl.Rule(self.error['ZE'] & self.delta_error['NS'], self.pwm_output['ME']),
            ctrl.Rule(self.error['ZE'] & self.delta_error['ZE'], self.pwm_output['ME']),
            ctrl.Rule(self.error['ZE'] & self.delta_error['PS'], self.pwm_output['ME']),
            ctrl.Rule(self.error['ZE'] & self.delta_error['PB'], self.pwm_output['HI']),
            
            ctrl.Rule(self.error['PS'] & self.delta_error['NB'], self.pwm_output['LO']),
            ctrl.Rule(self.error['PS'] & self.delta_error['NS'], self.pwm_output['ME']),
            ctrl.Rule(self.error['PS'] & self.delta_error['ZE'], self.pwm_output['HI']),
            ctrl.Rule(self.error['PS'] & self.delta_error['PS'], self.pwm_output['HI']),
            ctrl.Rule(self.error['PS'] & self.delta_error['PB'], self.pwm_output['VH']),
            
            ctrl.Rule(self.error['PB'] & self.delta_error['NB'], self.pwm_output['ME']),
            ctrl.Rule(self.error['PB'] & self.delta_error['NS'], self.pwm_output['HI']),
            ctrl.Rule(self.error['PB'] & self.delta_error['ZE'], self.pwm_output['VH']),
            ctrl.Rule(self.error['PB'] & self.delta_error['PS'], self.pwm_output['VH']),
            ctrl.Rule(self.error['PB'] & self.delta_error['PB'], self.pwm_output['VH'])
        ]
        
        # Create control system
        self.control_system = ctrl.ControlSystem(self.rules)
        self.controller = ctrl.ControlSystemSimulation(self.control_system)
    
    def _initialize_neural_network(self):
        """
        Create a simple neural network for scaling factor adaptation.
        For a full implementation, this would be trained on real data.
        Here we use a simple model for demonstration.
        """
        # For a real implementation, we would load pre-trained models from files
        # Here we'll create simple models with pre-defined weights that simulate adaptation
        
        # Define a very simple model for demonstration
        # In a real implementation, you would load proper trained models
        
        # Neural network for error scaling factor
        self.error_model = lambda target, actual: 1.0 + 0.01 * abs(target - actual)
        
        # Neural network for delta error scaling factor
        self.delta_error_model = lambda target, actual: 1.0 + 0.02 * abs(actual - self.prev_speed)
        
        # Neural network for output scaling factor
        self.output_model = lambda target, actual: 1.0 + 0.05 * abs(target - actual) / (target + 0.001)
    
    def compute_output(self, target_speed, current_speed):
        """
        Compute the controller output based on target and current speed.
        
        Args:
            target_speed: Target speed (normalized 0-100)
            current_speed: Current speed (normalized 0-100)
            
        Returns:
            PWM duty cycle (0-100)
        """
        # Calculate error
        error = target_speed - current_speed
        
        # Calculate change in error
        delta_error = error - self.prev_error
        self.prev_error = error
        
        # Update scaling factors using neural networks
        self.error_scale = self.error_model(target_speed, current_speed)
        self.delta_error_scale = self.delta_error_model(target_speed, current_speed)
        self.output_scale = self.output_model(target_speed, current_speed)
        
        # Apply scaling factors
        scaled_error = error * self.error_scale
        scaled_delta_error = delta_error * self.delta_error_scale
        
        # Clamp inputs to the defined universe
        scaled_error = max(min(scaled_error, 100), -100)
        scaled_delta_error = max(min(scaled_delta_error, 100), -100)
        
        # Set the inputs to the fuzzy controller
        self.controller.input['error'] = scaled_error
        self.controller.input['delta_error'] = scaled_delta_error
        
        # Compute the fuzzy result
        try:
            self.controller.compute()
            # Apply output scaling factor
            pwm = self.controller.output['pwm_output'] * self.output_scale
            # Ensure output is within 0-100
            pwm = max(min(pwm, 100), 0)
            
            # Store current speed for next iteration
            self.prev_speed = current_speed
            
            return pwm
        except:
            # Return a safe default value if computation fails
            return 0
