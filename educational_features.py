"""
Educational Features and Interactive Tutorials
Provides tooltips, explanations, and guided learning
"""

from typing import Dict, List
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QDialog, QDialogButtonBox, QTabWidget, QScrollArea
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont

from logger_utils import get_logger

logger = get_logger(__name__)


class ControlTheoryExplainer:
    """
    Provides educational explanations for control theory concepts
    """

    EXPLANATIONS = {
        'pi_controller': {
            'title': 'PI Controller',
            'short': 'Proportional-Integral controller combines immediate response (P) with accumulated error correction (I)',
            'detailed': """
**PI Controller - How It Works**

A PI controller combines two components:

**Proportional (P) Term:**
- Responds instantly to current error
- Output = Kp × error
- Larger error → larger correction
- Problem: Cannot eliminate steady-state error

**Integral (I) Term:**
- Accumulates error over time
- Output = Ki × ∫(error·dt)
- Eliminates steady-state error
- Problem: Can cause overshoot

**Combined:**
Output = Kp × error + Ki × ∫(error·dt)

**When to Use:**
- Systems without much noise
- When you need zero steady-state error
- When derivative action would amplify noise too much

**Tuning Guidelines:**
- Start with Kp only, increase until oscillation
- Add Ki to eliminate steady-state error
- If it overshoots too much, reduce Ki
            """,
            'formula': 'u(t) = Kp·e(t) + Ki·∫e(τ)dτ',
            'parameters': {
                'Kp': 'Proportional gain - controls immediate response strength',
                'Ki': 'Integral gain - controls accumulated error correction speed'
            }
        },

        'pid_controller': {
            'title': 'PID Controller',
            'short': 'Proportional-Integral-Derivative controller adds predictive action (D) to PI control',
            'detailed': """
**PID Controller - The Industry Standard**

Adds derivative action to PI control:

**Proportional (P) Term:**
- Immediate response to current error
- Output = Kp × error

**Integral (I) Term:**
- Eliminates steady-state error
- Output = Ki × ∫(error·dt)

**Derivative (D) Term:**
- Predicts future error based on rate of change
- Output = Kd × d(error)/dt
- Reduces overshoot and improves stability
- Problem: Amplifies noise

**Combined:**
Output = Kp × error + Ki × ∫(error·dt) + Kd × d(error)/dt

**When to Use:**
- Systems with low noise
- When you need fast response without overshoot
- When you can filter derivative term

**Tuning Guidelines (Ziegler-Nichols):**
1. Set Ki=0, Kd=0
2. Increase Kp until sustained oscillation (Ku)
3. Measure oscillation period (Tu)
4. Set: Kp=0.6·Ku, Ki=1.2·Ku/Tu, Kd=0.075·Ku·Tu
            """,
            'formula': 'u(t) = Kp·e(t) + Ki·∫e(τ)dτ + Kd·de(t)/dt',
            'parameters': {
                'Kp': 'Proportional gain - immediate response strength',
                'Ki': 'Integral gain - steady-state error elimination speed',
                'Kd': 'Derivative gain - predictive damping strength'
            }
        },

        'fuzzy_controller': {
            'title': 'Fuzzy Logic Controller',
            'short': 'Uses human-like reasoning with "if-then" rules instead of mathematical equations',
            'detailed': """
**Fuzzy Logic Controller - Human-Like Control**

Unlike PID which uses precise math, fuzzy logic uses linguistic rules:

**How It Works:**

1. **Fuzzification:**
   Convert crisp inputs to fuzzy sets
   Error = 10% → "Small Positive" (0.7 membership)

2. **Rule Evaluation:**
   IF error is "Large Negative" AND change is "Fast Positive"
   THEN output is "Large Increase"

3. **Aggregation:**
   Combine all fired rules

4. **Defuzzification:**
   Convert fuzzy output to crisp PWM value

**Advantages:**
✓ Works without mathematical model
✓ Handles nonlinearities naturally
✓ Uses expert knowledge
✓ Robust to parameter changes

**Disadvantages:**
✗ Harder to tune systematically
✗ No guarantee of stability
✗ Requires expert knowledge

**When to Use:**
- System is too complex to model
- Human operators have good intuition
- System has nonlinearities
- Mathematical model is uncertain
            """,
            'formula': 'IF error is X AND Δerror is Y THEN output is Z',
            'parameters': {
                'Membership Functions': 'Define fuzzy sets (Small, Medium, Large)',
                'Rule Base': 'IF-THEN rules encoding expert knowledge',
                'Defuzzification': 'Method to convert fuzzy output to crisp value'
            }
        },

        'anfis_controller': {
            'title': 'ANFIS - Adaptive Neuro-Fuzzy Controller',
            'short': 'Combines fuzzy logic with neural network learning for adaptive control',
            'detailed': """
**ANFIS - Adaptive Neuro-Fuzzy Inference System**

Combines the best of both worlds:
- Fuzzy Logic: Human-readable rules
- Neural Networks: Learning from data

**How It Works:**

1. **Base Fuzzy Controller:**
   Traditional fuzzy system with rules

2. **Neural Network Adaptation:**
   Three neural networks learn optimal scaling:
   - Error scaling network
   - Delta-error scaling network
   - Output scaling network

3. **Training:**
   Networks learn from optimal control examples
   Adapts to motor characteristics automatically

4. **Operation:**
   Fuzzy controller output × learned scaling factors

**Advantages:**
✓ Learns optimal parameters from data
✓ Adapts to system changes
✓ Combines rules with learning
✓ Better performance than pure fuzzy

**Why It's Better:**
- PID: Fixed parameters, needs manual tuning
- Fuzzy: Fixed rules, no learning
- ANFIS: Learns and adapts automatically

**Training Requirements:**
- Collect data across operating range
- Use well-tuned baseline controller
- Train neural networks offline
- Deploy trained models
            """,
            'formula': 'output = fuzzy_output × neural_scaling_factor',
            'parameters': {
                'Error Scale Network': 'Learns optimal error term scaling',
                'Delta-Error Scale Network': 'Learns optimal derivative scaling',
                'Output Scale Network': 'Learns optimal output scaling',
                'Training Data': 'Examples of good control across speeds'
            }
        },

        'anti_windup': {
            'title': 'Anti-Windup Protection',
            'short': 'Prevents integral term from accumulating excessively when output saturates',
            'detailed': """
**Anti-Windup - Why It's Critical**

**The Problem:**
When motor is at 100% PWM but speed hasn't reached target:
- Error continues to exist
- Integral keeps accumulating
- Integral becomes huge
- When target is reached, integral takes forever to wind down
- System overshoots badly

**Example Without Anti-Windup:**
Target = 90%, Motor maxes at 80%
Error = 10% persists for 30 seconds
Integral = 10 × 30 = 300 (huge!)
When load decreases and motor can reach 90%:
Controller still thinks integral=300 is needed
Massive overshoot to 120%+

**Solution - Clamping:**
```python
if integral > integral_limit:
    integral = integral_limit
if integral < -integral_limit:
    integral = -integral_limit
```

**Solution - Conditional Integration:**
```python
if output < 100 and output > 0:
    integral += error * dt  # Only integrate when not saturated
```

**Result:**
✓ No excessive integral buildup
✓ Smooth recovery from saturation
✓ No overshoot after saturation
            """,
            'formula': 'integral = clamp(integral + error·dt, -limit, +limit)',
            'parameters': {
                'integral_limit': 'Maximum allowed integral accumulation',
                'saturation_check': 'Only integrate when output is not saturated'
            }
        },

        'derivative_filtering': {
            'title': 'Derivative Filtering',
            'short': 'Smooths derivative term to reduce noise amplification',
            'detailed': """
**Derivative Filtering - Taming Noise**

**The Problem:**
Derivative = change in error / change in time
If sensor has noise:
- Error jumps randomly
- Derivative explodes
- Controller output oscillates wildly
- System becomes unstable

**Example:**
Time:  0.00s  0.01s  0.02s
Error: 10.0%  10.2%  9.8%   (noisy sensor)
Raw Derivative: 0 → 20 → -40  (huge swings!)

**Solution - Low-Pass Filter:**
Use exponential moving average:
```python
alpha = 0.1  # Filter strength (0=heavy filter, 1=no filter)
filtered_derivative = alpha × raw_derivative + (1-alpha) × previous_derivative
```

**Result:**
Time:  0.00s  0.01s  0.02s  0.03s
Filtered: 0 → 2.0 → 0.2 → 0.18  (smooth!)

**Tuning Alpha:**
- α = 0.01: Very smooth, slow response
- α = 0.1: Balanced (recommended)
- α = 0.5: Fast response, some noise
- α = 1.0: No filtering (use raw)

**Trade-off:**
More filtering → Smoother but slower
Less filtering → Faster but noisier
            """,
            'formula': 'D_filtered = α·D_raw + (1-α)·D_prev',
            'parameters': {
                'alpha': 'Filter coefficient (0=heavy filtering, 1=no filtering)',
                'cutoff_frequency': 'Alternative: specify cutoff in Hz'
            }
        },

        'performance_metrics': {
            'title': 'Performance Metrics',
            'short': 'Quantitative measures of controller performance',
            'detailed': """
**How to Evaluate Controller Performance**

**1. Overshoot:**
   Maximum amount system exceeds target
   Overshoot = (Peak - Target) / Target × 100%

   Good: <10%
   Acceptable: 10-25%
   Poor: >25%

**2. Settling Time:**
   Time until error stays within ±5% of target

   Good: <2 seconds
   Acceptable: 2-5 seconds
   Poor: >5 seconds

**3. Steady-State Error:**
   Average error after system has settled

   Good: <1%
   Acceptable: 1-3%
   Poor: >3%

**4. Rise Time:**
   Time to go from 10% to 90% of target

   Good: <1 second
   Acceptable: 1-2 seconds
   Poor: >2 seconds

**Performance Score Calculation:**
```python
overshoot_score = max(0, 100 - overshoot_percent × 3)
settling_score = max(0, 100 - settling_time × 10)
ss_error_score = max(0, 100 - ss_error × 20)

overall_score = (overshoot_score + settling_score + ss_error_score) / 3
```

**Trade-offs:**
- Fast rise time often causes overshoot
- Zero overshoot usually means slow response
- Best controller balances all metrics
            """,
            'formula': 'Score = f(overshoot, settling_time, ss_error)',
            'parameters': {
                'overshoot': 'Maximum deviation above target (%)',
                'settling_time': 'Time to reach ±5% band (seconds)',
                'ss_error': 'Average error after settling (%)',
                'rise_time': 'Time from 10% to 90% of target'
            }
        },

        'ziegler_nichols': {
            'title': 'Ziegler-Nichols Tuning',
            'short': 'Systematic method to find PID parameters automatically',
            'detailed': """
**Ziegler-Nichols Tuning Method**

**Classic Method (Ultimate Gain):**

1. **Set Ki=0, Kd=0 (P only)**
2. **Increase Kp until sustained oscillation**
   - System oscillates continuously
   - Note the gain: Ku (ultimate gain)
   - Measure period: Tu (ultimate period)

3. **Calculate PID parameters:**
   - Kp = 0.6 × Ku
   - Ki = 1.2 × Ku / Tu
   - Kd = 0.075 × Ku × Tu

**Relay Method (Safer):**

1. **Apply relay feedback**
   IF error > 0: output = target + amplitude
   IF error < 0: output = target - amplitude

2. **Observe oscillations**
   System will oscillate naturally
   Measure oscillation amplitude and period

3. **Calculate:**
   Ku = 4 × relay_amplitude / (π × oscillation_amplitude)
   Tu = oscillation_period

4. **Apply formulas above**

**Why It Works:**
- Based on frequency response theory
- Ku and Tu characterize system dynamics
- Formulas give aggressive but stable tuning

**Limitations:**
- Can be too aggressive (high overshoot)
- Assumes linear system
- May need detuning (multiply Kp by 0.8)

**Our Implementation:**
The auto_tuner.py uses relay method for safety
            """,
            'formula': 'Kp=0.6·Ku, Ki=1.2·Ku/Tu, Kd=0.075·Ku·Tu',
            'parameters': {
                'Ku': 'Ultimate gain - Kp value that causes sustained oscillation',
                'Tu': 'Ultimate period - period of sustained oscillation',
                'Relay Amplitude': 'Size of on-off steps in relay test'
            }
        }
    }

    @classmethod
    def get_explanation(cls, topic: str) -> Dict:
        """Get explanation for a topic"""
        return cls.EXPLANATIONS.get(topic, {
            'title': 'Unknown Topic',
            'short': 'No explanation available',
            'detailed': 'No detailed explanation available.',
            'formula': '',
            'parameters': {}
        })

    @classmethod
    def get_all_topics(cls) -> List[str]:
        """Get list of all available topics"""
        return list(cls.EXPLANATIONS.keys())


class TooltipWidget(QLabel):
    """
    Educational tooltip that appears on hover
    """

    def __init__(self, text: str, topic: str = None, parent=None):
        super().__init__(parent)

        self.setText(text)
        self.setWordWrap(True)
        self.setStyleSheet("""
            QLabel {
                background-color: #FFFACD;
                border: 2px solid #FFD700;
                border-radius: 6px;
                padding: 10px;
                color: #333;
                font-size: 12px;
            }
        """)

        if topic:
            explanation = ControlTheoryExplainer.get_explanation(topic)
            self.setToolTip(explanation['short'])

        self.setMaximumWidth(300)


class ExplanationDialog(QDialog):
    """
    Full-screen explanation dialog for deep learning
    """

    def __init__(self, topic: str, parent=None):
        super().__init__(parent)

        self.topic = topic
        self.explanation = ControlTheoryExplainer.get_explanation(topic)

        self.setWindowTitle(self.explanation['title'])
        self.setMinimumSize(700, 500)

        self.init_ui()

    def init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout(self)

        # Title
        title = QLabel(self.explanation['title'])
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignCenter)

        # Short description
        short_desc = QLabel(self.explanation['short'])
        short_desc.setWordWrap(True)
        short_desc.setStyleSheet("color: #555; font-size: 13px; padding: 10px;")

        # Formula
        if self.explanation.get('formula'):
            formula = QLabel(f"Formula: {self.explanation['formula']}")
            formula.setStyleSheet("""
                background-color: #F0F0F0;
                padding: 10px;
                border-radius: 6px;
                font-family: 'Courier New';
                font-size: 14px;
                color: #0066CC;
            """)
            formula.setAlignment(Qt.AlignCenter)

        # Detailed explanation
        detailed = QTextEdit()
        detailed.setReadOnly(True)
        detailed.setPlainText(self.explanation['detailed'])
        detailed.setStyleSheet("font-size: 12px; padding: 10px;")

        # Parameters section
        if self.explanation.get('parameters'):
            params_text = "**Key Parameters:**\n\n"
            for param, desc in self.explanation['parameters'].items():
                params_text += f"• **{param}**: {desc}\n"

            params = QTextEdit()
            params.setReadOnly(True)
            params.setPlainText(params_text)
            params.setMaximumHeight(150)
            params.setStyleSheet("background-color: #E8F4F8; font-size: 11px; padding: 10px;")

        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok)
        button_box.accepted.connect(self.accept)

        # Layout
        layout.addWidget(title)
        layout.addWidget(short_desc)
        if self.explanation.get('formula'):
            layout.addWidget(formula)
        layout.addWidget(QLabel("Detailed Explanation:"))
        layout.addWidget(detailed)
        if self.explanation.get('parameters'):
            layout.addWidget(QLabel("Parameters:"))
            layout.addWidget(params)
        layout.addWidget(button_box)


class InteractiveTutorial(QWidget):
    """
    Step-by-step interactive tutorial
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.current_step = 0
        self.steps = [
            {
                'title': 'Welcome to DC Motor Control',
                'content': """
Welcome to the DC Motor Control System!

This tutorial will guide you through:
1. Understanding different controllers
2. Tuning parameters
3. Analyzing performance
4. Using advanced features

Click "Next" to begin.
                """
            },
            {
                'title': 'Step 1: Choose a Controller',
                'content': """
**Choosing the Right Controller**

You have 4 options:

1. **PI Controller** - Simple, reliable
   - Good for most applications
   - Easy to understand
   - Needs manual tuning

2. **PID Controller** - Industry standard
   - Best for noisy systems
   - Excellent performance
   - Requires careful tuning

3. **Fuzzy Controller** - Human-like logic
   - No mathematical model needed
   - Robust to changes
   - Good default performance

4. **ANFIS** - Intelligent adaptive ⭐
   - Learns from data
   - Best overall performance
   - Requires training data

**Try This:**
Switch between controllers using the dropdown
and observe how each responds to speed changes.
                """
            },
            {
                'title': 'Step 2: Understanding the Display',
                'content': """
**Dashboard Elements**

**Speed Gauge:**
- Shows current motor speed
- Green = good
- Red = error

**Status Indicators:**
- Motor: Running state
- Sensor: IR sensor status
- Controller: Controller state

**Metrics:**
- Target: Desired speed
- Actual: Current speed
- Error: Difference (Target - Actual)
- PWM: Motor drive signal (0-100%)

**Performance:**
- Overshoot: How much it overshoots
- Settling Time: Time to stabilize
- SS Error: Steady-state accuracy
- Score: Overall rating (0-100)

**Try This:**
Watch how metrics change as you adjust target speed.
                """
            },
            {
                'title': 'Step 3: Tuning PID',
                'content': """
**PID Tuning Basics**

**Kp (Proportional):**
- Controls immediate response
- Higher = faster but more overshoot
- Start: Try 0.5-1.0

**Ki (Integral):**
- Eliminates steady-state error
- Higher = faster correction but more overshoot
- Start: Try 0.1-0.3

**Kd (Derivative):**
- Reduces overshoot
- Higher = more damping but sensitive to noise
- Start: Try 0.05-0.15

**Tuning Process:**
1. Set Ki=0, Kd=0
2. Increase Kp until slight oscillation
3. Add Ki to remove steady-state error
4. Add Kd if there's too much overshoot

**Try This:**
Go to the "Tuning" tab and experiment!
Or use the Auto-Tuner for automatic setup.
                """
            },
            {
                'title': 'Step 4: Analyzing Performance',
                'content': """
**Reading the Plots**

**Real-Time Plot:**
- Blue dashed line = Target
- Green solid line = Actual speed
- Red area = Error
- Watch for overshoot and settling

**FFT Analysis:**
- Shows frequency content
- High frequencies = oscillations
- Low dominant frequency = stable

**Phase Portrait:**
- Error vs Error Rate
- Spiral to origin = converging
- Circle = sustained oscillation
- Good controller → tight spiral

**Controller Comparison:**
- Compare multiple runs
- See which controller is best
- Analyze trade-offs

**Try This:**
Run each controller for 30 seconds
and compare their performance!
                """
            },
            {
                'title': 'Step 5: Export and Analysis',
                'content': """
**Exporting Your Data**

**Save Plot (PNG):**
- High-resolution image
- For reports and presentations

**Export CSV:**
- Raw time-series data
- Open in Excel/Python
- For detailed analysis

**Export JSON:**
- Structured data format
- Includes metadata
- For programming analysis

**Export MATLAB:**
- Direct import to MATLAB
- Includes plot commands
- For advanced analysis

**Try This:**
Run a test, then export your results.
Analyze in your preferred tool!
                """
            },
            {
                'title': 'Congratulations!',
                'content': """
**You've Completed the Tutorial!**

You now know:
✓ How to choose controllers
✓ How to read the dashboard
✓ How to tune PID parameters
✓ How to analyze performance
✓ How to export data

**Next Steps:**

1. Experiment with different controllers
2. Try the auto-tuner
3. Collect training data for ANFIS
4. Compare controller performance
5. Export and analyze your results

**Tips:**
- Start simple (PI or Fuzzy)
- Always check performance metrics
- Save good configurations
- Export data for later analysis

Happy controlling! 🎉
                """
            }
        ]

        self.init_ui()

    def init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout(self)

        # Tutorial content
        self.title_label = QLabel()
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        self.title_label.setFont(title_font)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)

        self.content_label = QLabel()
        self.content_label.setWordWrap(True)
        self.content_label.setStyleSheet("font-size: 12px; padding: 15px;")
        scroll_area.setWidget(self.content_label)

        # Progress indicator
        self.progress_label = QLabel()
        self.progress_label.setAlignment(Qt.AlignCenter)

        # Navigation buttons
        button_layout = QHBoxLayout()

        self.prev_btn = QPushButton("← Previous")
        self.prev_btn.clicked.connect(self.previous_step)

        self.next_btn = QPushButton("Next →")
        self.next_btn.clicked.connect(self.next_step)

        self.close_btn = QPushButton("Close Tutorial")
        self.close_btn.clicked.connect(self.close)

        button_layout.addWidget(self.prev_btn)
        button_layout.addWidget(self.next_btn)
        button_layout.addWidget(self.close_btn)

        # Layout
        layout.addWidget(self.title_label)
        layout.addWidget(self.progress_label)
        layout.addWidget(scroll_area)
        layout.addLayout(button_layout)

        # Show first step
        self.update_step()

    def update_step(self):
        """Update display for current step"""
        if 0 <= self.current_step < len(self.steps):
            step = self.steps[self.current_step]
            self.title_label.setText(step['title'])
            self.content_label.setText(step['content'])
            self.progress_label.setText(f"Step {self.current_step + 1} of {len(self.steps)}")

            # Update button states
            self.prev_btn.setEnabled(self.current_step > 0)
            self.next_btn.setEnabled(self.current_step < len(self.steps) - 1)

    def next_step(self):
        """Go to next step"""
        if self.current_step < len(self.steps) - 1:
            self.current_step += 1
            self.update_step()

    def previous_step(self):
        """Go to previous step"""
        if self.current_step > 0:
            self.current_step -= 1
            self.update_step()


class EducationalPanel(QWidget):
    """
    Main educational panel with quick access to learning resources
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout(self)

        # Header
        header = QLabel("📚 Learn Control Theory")
        header_font = QFont()
        header_font.setPointSize(14)
        header_font.setBold(True)
        header.setFont(header_font)

        # Quick topics
        topics_group = QWidget()
        topics_layout = QVBoxLayout(topics_group)

        topics = [
            ('PI Controller', 'pi_controller'),
            ('PID Controller', 'pid_controller'),
            ('Fuzzy Logic', 'fuzzy_controller'),
            ('ANFIS', 'anfis_controller'),
            ('Anti-Windup', 'anti_windup'),
            ('Derivative Filtering', 'derivative_filtering'),
            ('Performance Metrics', 'performance_metrics'),
            ('Ziegler-Nichols Tuning', 'ziegler_nichols')
        ]

        for title, topic in topics:
            btn = QPushButton(f"📖 {title}")
            btn.clicked.connect(lambda checked, t=topic: self.show_explanation(t))
            topics_layout.addWidget(btn)

        # Tutorial button
        tutorial_btn = QPushButton("🎓 Start Interactive Tutorial")
        tutorial_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 10px;
                font-size: 13px;
                font-weight: bold;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #45A049;
            }
        """)
        tutorial_btn.clicked.connect(self.show_tutorial)

        # Layout
        layout.addWidget(header)
        layout.addWidget(QLabel("Quick Reference:"))
        layout.addWidget(topics_group)
        layout.addWidget(tutorial_btn)
        layout.addStretch()

    def show_explanation(self, topic: str):
        """Show explanation dialog"""
        dialog = ExplanationDialog(topic, self)
        dialog.exec_()

    def show_tutorial(self):
        """Show interactive tutorial"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Interactive Tutorial")
        dialog.setMinimumSize(800, 600)

        layout = QVBoxLayout(dialog)
        tutorial = InteractiveTutorial(dialog)
        layout.addWidget(tutorial)

        dialog.exec_()


if __name__ == '__main__':
    from PyQt5.QtWidgets import QApplication
    import sys

    app = QApplication(sys.argv)

    # Test educational panel
    panel = EducationalPanel()
    panel.setWindowTitle("Educational Features Demo")
    panel.resize(400, 600)
    panel.show()

    sys.exit(app.exec_())
