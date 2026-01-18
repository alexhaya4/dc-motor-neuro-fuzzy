# Advanced Features Implementation Guide

## 🎉 New Advanced Features Added!

This guide explains all the new advanced plotting and educational features added to the DC Motor Control System.

---

## 📊 Advanced Plotting System

### Overview

The new `advanced_plotting.py` module provides:
- **Multiple trace plotting** (PWM, P/I/D terms)
- **Export functionality** (PNG, CSV, JSON, MATLAB)
- **FFT analysis** (frequency domain)
- **Phase portraits** (error vs error rate)
- **Controller comparison** (side-by-side)

### 1. Multi-Trace Plot Widget

#### Features

**Configurable Traces:**
- ✅ Target Speed (blue dashed)
- ✅ Actual Speed (green solid)
- ✅ Error Area (red fill)
- ✅ PWM Output (magenta)
- ✅ P Term (cyan dotted)
- ✅ I Term (yellow dotted)
- ✅ D Term (orange dotted)

**Usage:**

```python
from advanced_plotting import AdvancedPlotWidget

# Create widget
plot_widget = AdvancedPlotWidget()

# Add sample data
plot_widget.add_sample(
    time=1.5,
    target=70.0,
    actual=68.5,
    error=1.5,
    pwm=75.0,
    p_term=0.9,    # From PID controller
    i_term=0.15,   # From PID controller
    d_term=0.05    # From PID controller
)

# Update plot
plot_widget.update_plot()
```

**Toggle Traces:**
Use checkboxes to show/hide specific traces:
- Useful for focusing on specific aspects
- All traces stored, just visibility toggled
- Real-time updates

---

### 2. Export Functionality

#### Save Plot as PNG

```python
# Save high-resolution plot
plot_widget.save_plot()  # Opens file dialog
# Saves at 300 DPI for publication quality
```

#### Export Data to CSV

```python
# Export to CSV (Excel compatible)
plot_widget.export_csv()
```

**CSV Format:**
```csv
Time(s),Target(%),Actual(%),Error(%),PWM(%),P_Term,I_Term,D_Term
0.0,50.0,0.0,50.0,50.0,25.0,0.0,0.0
0.1,50.0,5.2,44.8,52.5,22.4,0.45,2.2
...
```

#### Export Data to JSON

```python
# Export structured data
plot_widget.export_json()
```

**JSON Format:**
```json
{
  "metadata": {
    "controller": "PID",
    "start_time": "2026-01-16T10:30:00",
    "export_time": "2026-01-16T10:35:00",
    "samples": 3000
  },
  "data": {
    "time": [0.0, 0.1, 0.2, ...],
    "target_speed": [50.0, 50.0, 50.0, ...],
    "actual_speed": [0.0, 5.2, 12.8, ...],
    "error": [50.0, 44.8, 37.2, ...],
    "pwm_output": [50.0, 52.5, 55.0, ...],
    "p_term": [25.0, 22.4, 18.6, ...],
    "i_term": [0.0, 0.45, 0.95, ...],
    "d_term": [0.0, 2.2, 3.6, ...]
  }
}
```

#### Export Data to MATLAB

```python
# Export MATLAB .m file
plot_widget.export_matlab()
```

**MATLAB Format:**
```matlab
% Motor Control Data - PID
% Exported: 2026-01-16T10:35:00

time = [0.000000 0.100000 0.200000 ...];
target_speed = [50.000000 50.000000 50.000000 ...];
actual_speed = [0.000000 5.200000 12.800000 ...];
% ... more arrays

% Plot example
figure;
plot(time, target_speed, 'b--', time, actual_speed, 'g-');
xlabel('Time (s)');
ylabel('Speed (%)');
legend('Target', 'Actual');
grid on;
```

---

### 3. FFT Analysis Widget

#### Purpose

Analyze system behavior in frequency domain:
- **Dominant frequencies**: Identify oscillations
- **Stability analysis**: Check for resonance
- **Noise analysis**: See frequency content

#### Usage

```python
from advanced_plotting import FFTAnalysisWidget

# Create widget
fft_widget = FFTAnalysisWidget()

# Link to data source
fft_widget.set_data_source(plot_widget)

# Perform analysis
fft_widget.analyze()
```

#### Interpretation

**Low Dominant Frequency (< 0.5 Hz):**
- ✅ Stable system
- ✅ Smooth control
- Good controller tuning

**Medium Frequency (0.5-2 Hz):**
- ⚠️ Some oscillation
- May need detuning
- Check Kd parameter

**High Frequency (> 2 Hz):**
- ❌ Unstable system
- ❌ Excessive oscillation
- Reduce Kp, increase Kd

**Example Output:**
```
Dominant Frequency: 0.35 Hz
Interpretation: Stable, well-tuned system
```

---

### 4. Phase Portrait Widget

#### Purpose

Visualize system dynamics:
- **Error vs Error Rate** phase plot
- **Convergence analysis**: Spiral to origin = good
- **Stability**: Check trajectory shape

#### Usage

```python
from advanced_plotting import PhasePlotWidget

# Create widget
phase_widget = PhasePlotWidget()

# Link to data source
phase_widget.set_data_source(plot_widget)

# Update plot
phase_widget.update_plot()
```

#### Interpretation

**Tight Spiral to Origin:**
- ✅ Excellent convergence
- ✅ Fast settling
- ✅ No overshoot

**Wide Spiral:**
- ⚠️ Slow convergence
- Need higher Kp

**Oscillating Circle:**
- ❌ Sustained oscillation
- ❌ Unstable
- Reduce Kp, increase Kd

**Straight Line to Origin:**
- ✅ Critically damped
- ✅ No overshoot
- Optimal tuning

---

### 5. Controller Comparison Widget

#### Purpose

Compare multiple controller runs side-by-side:
- **Performance comparison**: See which is best
- **Parameter tuning**: Compare before/after
- **Controller selection**: Choose optimal one

#### Usage

```python
from advanced_plotting import ComparisonWidget

# Create widget
comparison_widget = ComparisonWidget()

# Link to data source
comparison_widget.set_data_source(plot_widget)

# Add current run
comparison_widget.add_current_recording()
# Name: "PID_10:30:45"

# Run another controller
# ... switch to Fuzzy, run test ...
comparison_widget.add_current_recording()
# Name: "Fuzzy_10:32:15"

# Or load from file
comparison_widget.load_recording()
```

#### Features

**Four Subplots:**

1. **Speed Comparison**
   - All controller responses overlaid
   - See which reaches target fastest

2. **Error Comparison**
   - Compare error trajectories
   - Identify overshoot and oscillation

3. **PWM Comparison**
   - See control effort differences
   - Identify aggressive vs smooth control

4. **Metrics Bar Chart**
   - Overshoot comparison
   - Settling time comparison
   - Steady-state error comparison

**Metrics Calculated:**
```python
{
    'overshoot': 15.2,       # Maximum error (%)
    'settling_time': 2.8,    # Time to ±5% band (s)
    'ss_error': 1.3          # Average error after settling (%)
}
```

---

## 🎓 Educational Features

### Overview

The new `educational_features.py` module provides:
- **Interactive tooltips** with control theory explanations
- **Full explanation dialogs** for deep learning
- **Interactive tutorial** for beginners
- **Quick reference panel** for all topics

### 1. Control Theory Explainer

#### Available Topics

**Controllers:**
- `pi_controller` - PI Controller basics
- `pid_controller` - PID Controller complete guide
- `fuzzy_controller` - Fuzzy Logic introduction
- `anfis_controller` - ANFIS neural-fuzzy system

**Concepts:**
- `anti_windup` - Integral windup prevention
- `derivative_filtering` - Noise reduction
- `performance_metrics` - How to evaluate controllers
- `ziegler_nichols` - Automatic tuning method

#### Usage

```python
from educational_features import ControlTheoryExplainer

# Get explanation
explanation = ControlTheoryExplainer.get_explanation('pid_controller')

print(explanation['title'])      # "PID Controller"
print(explanation['short'])      # One-line summary
print(explanation['detailed'])   # Full explanation
print(explanation['formula'])    # Mathematical formula
print(explanation['parameters']) # Parameter descriptions
```

### 2. Tooltip Widget

#### Usage

```python
from educational_features import TooltipWidget

# Create tooltip
tooltip = TooltipWidget(
    text="Kp controls immediate response",
    topic='pid_controller'
)

# Tooltip appears on hover
# Shows short explanation
```

### 3. Explanation Dialog

#### Features

- **Full-screen modal dialog**
- **Rich text formatting**
- **Formula display**
- **Parameter reference**
- **Easy navigation**

#### Usage

```python
from educational_features import ExplanationDialog

# Show explanation
dialog = ExplanationDialog('pid_controller', parent=self)
dialog.exec_()
```

**Dialog Contains:**
- Title (large, bold)
- Short summary
- Mathematical formula (highlighted)
- Detailed explanation (scrollable)
- Parameter reference
- OK button

### 4. Interactive Tutorial

#### Features

**7-Step Tutorial:**
1. Welcome and overview
2. Choosing controllers
3. Understanding the display
4. Tuning PID parameters
5. Analyzing performance
6. Exporting data
7. Congratulations and next steps

#### Usage

```python
from educational_features import InteractiveTutorial

# Create tutorial widget
tutorial = InteractiveTutorial()

# Show in dialog
dialog = QDialog()
layout = QVBoxLayout(dialog)
layout.addWidget(tutorial)
dialog.exec_()
```

**Features:**
- Step counter (1 of 7)
- Previous/Next navigation
- Progress indicator
- Close button
- Scrollable content

### 5. Educational Panel

#### Quick Reference Panel

```python
from educational_features import EducationalPanel

# Create panel
panel = EducationalPanel()

# Add to GUI tab
tab_widget.addTab(panel, "📚 Learn")
```

**Features:**
- Quick topic buttons
- One-click explanations
- "Start Tutorial" button
- Clean, organized layout

---

## 🚀 Integration Guide

### Integrating into Existing GUI

#### Step 1: Add Advanced Plotting Tab

```python
from advanced_plotting import AdvancedPlottingTabWidget

class ModernMotorGUI(QMainWindow):
    def __init__(self):
        super().__init__()

        # Create advanced plotting widget
        self.advanced_plots = AdvancedPlottingTabWidget()

        # Add to main tab widget
        self.main_tabs.addTab(self.advanced_plots, "📊 Advanced Plots")
```

#### Step 2: Feed Data to Plots

```python
def update_display(self):
    """Update display with current values"""
    # ... existing code ...

    # Get PID terms (if using PID controller)
    if isinstance(self.current_controller, PIDController):
        p_term = self.current_controller.kp * error
        i_term = self.current_controller.ki * self.current_controller.integral
        d_term = self.current_controller.kd * self.current_controller.derivative
    else:
        p_term = i_term = d_term = 0.0

    # Add sample to advanced plots
    self.advanced_plots.add_sample(
        time=time.time() - self.start_time,
        target=target,
        actual=current,
        error=error,
        pwm=pwm,
        p_term=p_term,
        i_term=i_term,
        d_term=d_term
    )

    # Update plots
    self.advanced_plots.update_plots()
```

#### Step 3: Add Educational Panel

```python
from educational_features import EducationalPanel

class ModernMotorGUI(QMainWindow):
    def __init__(self):
        super().__init__()

        # Create educational panel
        self.edu_panel = EducationalPanel()

        # Add to main tab widget
        self.main_tabs.addTab(self.edu_panel, "📚 Learn")
```

#### Step 4: Add Help Buttons

```python
# Add help buttons next to parameters
help_btn = QPushButton("?")
help_btn.setMaximumWidth(30)
help_btn.clicked.connect(
    lambda: ExplanationDialog('pid_controller', self).exec_()
)
```

---

## 📈 Usage Examples

### Example 1: Compare PI vs PID vs Fuzzy

```python
# 1. Select PI controller
self.controller_combo.setCurrentText("PI")
time.sleep(30)  # Let it run

# 2. Add to comparison
self.comparison_widget.add_current_recording()

# 3. Select PID controller
self.controller_combo.setCurrentText("PID")
time.sleep(30)

# 4. Add to comparison
self.comparison_widget.add_current_recording()

# 5. Select Fuzzy
self.controller_combo.setCurrentText("Fuzzy")
time.sleep(30)

# 6. Add to comparison
self.comparison_widget.add_current_recording()

# 7. View results
self.comparison_widget.update_comparison()
# See side-by-side comparison!
```

### Example 2: Tune PID with FFT

```python
# 1. Set initial parameters
kp, ki, kd = 1.0, 0.2, 0.1

# 2. Run for 30 seconds
time.sleep(30)

# 3. Check FFT
self.fft_widget.analyze()

# If dominant frequency > 1 Hz:
#   - Reduce Kp
#   - Increase Kd

# 4. Adjust and repeat
kp = 0.8  # Reduced
kd = 0.15  # Increased

# 5. Run again
time.sleep(30)

# 6. Check FFT again
self.fft_widget.analyze()
# Should see lower dominant frequency
```

### Example 3: Export for Analysis

```python
# 1. Run comprehensive test
# Set target = 70%
# Let system stabilize for 60 seconds

# 2. Export all formats
self.plot_widget.save_plot()          # PNG for report
self.plot_widget.export_csv()         # CSV for Excel
self.plot_widget.export_json()        # JSON for Python
self.plot_widget.export_matlab()      # MATLAB for advanced analysis

# 3. Analyze in Python
import json
import pandas as pd

with open('motor_data.json', 'r') as f:
    data = json.load(f)

df = pd.DataFrame(data['data'])

# Calculate additional metrics
overshoot = df['error'].max()
settling_idx = df[df['error'].abs() < 5].index[0]
settling_time = df.loc[settling_idx, 'time']

print(f"Overshoot: {overshoot:.2f}%")
print(f"Settling Time: {settling_time:.2f}s")
```

### Example 4: Educational Mode

```python
# For teaching/demos

# 1. Start interactive tutorial
self.edu_panel.show_tutorial()

# 2. Students follow 7 steps
# - Learn about controllers
# - Understand metrics
# - Try tuning
# - Analyze results

# 3. Quick reference during experiments
# Click "📖 PID Controller" for instant explanation

# 4. Deep dive on demand
# "?" buttons show detailed explanations
```

---

## 🎨 Visualization Tips

### Best Practices

**1. Start with Multi-Trace Plot:**
- Enable Target, Actual, Error Area
- Watch system behavior
- Disable PWM/P/I/D initially

**2. Add PWM Trace When Tuning:**
- See controller output
- Identify saturation (PWM at 0% or 100%)
- Check smoothness

**3. Add P/I/D Terms for Debugging:**
- See which term dominates
- Identify integral windup (I term keeps growing)
- Check derivative noise (D term spikes)

**4. Use FFT to Check Stability:**
- After tuning changes
- Look for high-frequency content
- Dominant frequency should be < 0.5 Hz

**5. Use Phase Plot for Convergence:**
- Should spiral tightly to origin
- No limit cycles (circles)
- Start (green) far from origin, end (red) at origin

**6. Compare Controllers:**
- Run each for same duration
- Same target speed
- Fair comparison

---

## 🔧 Configuration

### Customizing Plots

#### Change Colors

```python
# In advanced_plotting.py, modify plot() calls:

# Target speed - change from blue to red
self.ax.plot(time, arrays['target_speed'], 'r--', ...)

# Actual speed - change from green to blue
self.ax.plot(time, arrays['actual_speed'], 'b-', ...)
```

#### Change Time Window

```python
# Multi-trace data buffer size
data = MultiTraceData(max_samples=3000)  # 5 minutes at 10Hz

# Or for longer history
data = MultiTraceData(max_samples=6000)  # 10 minutes
```

#### Adjust Plot Limits

```python
# Y-axis limits
self.ax.set_ylim(-20, 120)  # More headroom

# X-axis (time window)
self.ax.set_xlim(max(0, time[-1] - 60), time[-1] + 1)  # 60-second window
```

### Adding New Topics

```python
# In educational_features.py

class ControlTheoryExplainer:
    EXPLANATIONS = {
        # ... existing topics ...

        'my_new_topic': {
            'title': 'My New Topic',
            'short': 'One-line summary',
            'detailed': """
            Full explanation here.

            Can use markdown-like formatting.

            **Bold** for emphasis
            *Italic* for terms

            Lists:
            - Point 1
            - Point 2
            """,
            'formula': 'x = y + z',
            'parameters': {
                'x': 'Output variable',
                'y': 'Input 1',
                'z': 'Input 2'
            }
        }
    }
```

---

## 📚 API Reference

### AdvancedPlotWidget

**Methods:**
```python
add_sample(time, target, actual, error, pwm, p_term, i_term, d_term)
update_plot()
clear_plot()
save_plot()
export_csv()
export_json()
export_matlab()
toggle_trace(trace_name)
```

**Signals:**
```python
export_requested(format: str, filename: str)
```

### FFTAnalysisWidget

**Methods:**
```python
set_data_source(plot_widget: AdvancedPlotWidget)
analyze()
update_plot()
```

### PhasePlotWidget

**Methods:**
```python
set_data_source(plot_widget: AdvancedPlotWidget)
update_plot()
```

### ComparisonWidget

**Methods:**
```python
set_data_source(plot_widget: AdvancedPlotWidget)
add_current_recording()
load_recording()
clear_recordings()
update_comparison()
```

### ControlTheoryExplainer

**Methods:**
```python
get_explanation(topic: str) -> Dict
get_all_topics() -> List[str]
```

### ExplanationDialog

**Constructor:**
```python
ExplanationDialog(topic: str, parent=None)
```

### InteractiveTutorial

**Methods:**
```python
next_step()
previous_step()
update_step()
```

### EducationalPanel

**Methods:**
```python
show_explanation(topic: str)
show_tutorial()
```

---

## 🎉 Summary

### What You Can Now Do

**Advanced Plotting:**
✅ Plot multiple traces simultaneously
✅ Export high-quality plots (PNG)
✅ Export data (CSV, JSON, MATLAB)
✅ Analyze frequency content (FFT)
✅ Visualize phase portraits
✅ Compare multiple controllers

**Educational Features:**
✅ Interactive 7-step tutorial
✅ Detailed explanations for all topics
✅ Quick reference panel
✅ Tooltips with context
✅ Mathematical formulas
✅ Parameter descriptions

**Use Cases:**
✅ Teaching control theory
✅ Research and analysis
✅ Performance optimization
✅ Publication-quality figures
✅ Student projects
✅ Professional presentations

---

## 🚀 Next Steps

1. **Try the interactive tutorial** - Click "🎓 Start Interactive Tutorial"
2. **Explore multi-trace plotting** - Enable P/I/D term traces
3. **Compare controllers** - Run PI, PID, Fuzzy, ANFIS side-by-side
4. **Export your results** - Save plots and data for analysis
5. **Analyze frequency content** - Use FFT to check stability
6. **Learn control theory** - Use quick reference buttons

---

**Version:** 2.1.0
**Date:** 2026-01-16
**Status:** ✅ COMPLETE

**Enjoy your enhanced DC Motor Control System!** 🎉
