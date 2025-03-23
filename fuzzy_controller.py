import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl

class FuzzyController:
    def __init__(self):
        # Create fuzzy variables for error and change in error (inputs)
        self.error = ctrl.Antecedent(np.arange(-100, 101, 1), 'error')
        self.delta_error = ctrl.Antecedent(np.arange(-100, 101, 1), 'delta_error')
        
        # Create fuzzy variable for PWM duty cycle (output)
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
        
        # Define rule base (based on the rule matrix in the research papers)
        self.rules = []
        
        # Rule 1: If error is NB and delta_error is NB, then pwm_output is VL
        self.rules.append(ctrl.Rule(self.error['NB'] & self.delta_error['NB'], self.pwm_output['VL']))
        
        # Rule 2: If error is NB and delta_error is NS, then pwm_output is VL
        self.rules.append(ctrl.Rule(self.error['NB'] & self.delta_error['NS'], self.pwm_output['VL']))
        
        # Rule 3: If error is ZE and delta_error is ZE, then pwm_output is ME
        self.rules.append(ctrl.Rule(self.error['ZE'] & self.delta_error['ZE'], self.pwm_output['ME']))
        
        # Rule 4: If error is PS and delta_error is ZE, then pwm_output is HI
        self.rules.append(ctrl.Rule(self.error['PS'] & self.delta_error['ZE'], self.pwm_output['HI']))
        
        # Rule 5: If error is PB and delta_error is PB, then pwm_output is VH
        self.rules.append(ctrl.Rule(self.error['PB'] & self.delta_error['PB'], self.pwm_output['VH']))
        
        # Add more rules based on the rule matrix from the papers
        self.rules.append(ctrl.Rule(self.error['NB'] & self.delta_error['ZE'], self.pwm_output['LO']))
        self.rules.append(ctrl.Rule(self.error['NS'] & self.delta_error['NS'], self.pwm_output['LO']))
        self.rules.append(ctrl.Rule(self.error['NS'] & self.delta_error['ZE'], self.pwm_output['ME']))
        self.rules.append(ctrl.Rule(self.error['ZE'] & self.delta_error['NS'], self.pwm_output['ME']))
        self.rules.append(ctrl.Rule(self.error['ZE'] & self.delta_error['PS'], self.pwm_output['ME']))
        self.rules.append(ctrl.Rule(self.error['PS'] & self.delta_error['PS'], self.pwm_output['HI']))
        self.rules.append(ctrl.Rule(self.error['PB'] & self.delta_error['ZE'], self.pwm_output['VH']))
        
        # Create control system
        self.control_system = ctrl.ControlSystem(self.rules)
        self.controller = ctrl.ControlSystemSimulation(self.control_system)
    
    def compute_output(self, error, delta_error):
        """
        Compute the fuzzy controller output based on error and change in error.
        
        Args:
            error: Error between target and current speed
            delta_error: Change in error (current error - previous error)
            
        Returns:
            PWM duty cycle (0-100)
        """
        # Clamp inputs to the defined universe
        error = max(min(error, 100), -100)
        delta_error = max(min(delta_error, 100), -100)
        
        # Set the inputs
        self.controller.input['error'] = error
        self.controller.input['delta_error'] = delta_error
        
        # Compute the result
        try:
            self.controller.compute()
            pwm = self.controller.output['pwm_output']
            return max(min(pwm, 100), 0)  # Ensure output is within 0-100
        except:
            # Return a safe default value if computation fails
            return 0
