import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Circle, Rectangle, Polygon

# Create a figure with a specified size
plt.figure(figsize=(4, 4), facecolor='#3498db')

# Add a motor-like icon
ax = plt.gca()
ax.set_xlim(0, 10)
ax.set_ylim(0, 10)
ax.set_aspect('equal')
ax.axis('off')

# Add a motor casing
motor_body = Rectangle((2, 3), 6, 4, facecolor='#7f8c8d', edgecolor='black', linewidth=2)
ax.add_patch(motor_body)

# Add a motor shaft
shaft = Rectangle((8, 4.5), 2, 1, facecolor='#2c3e50', edgecolor='black', linewidth=2)
ax.add_patch(shaft)

# Add a motor rotor
rotor = Circle((5, 5), 1.5, facecolor='#e74c3c', edgecolor='black', linewidth=2)
ax.add_patch(rotor)

# Add some neural network nodes in the background
for i in range(3):
    for j in range(3):
        node = Circle((i*2 + 2, j*1.5 + 2), 0.3, facecolor='white', alpha=0.5)
        ax.add_patch(node)

# Add some connections between nodes
for i in range(3):
    for j in range(3):
        for k in range(3):
            if np.random.rand() > 0.7:
                plt.plot([i*2 + 2, k*2 + 2], [j*1.5 + 2, (j+1)%3*1.5 + 2], 'w-', alpha=0.2, linewidth=0.5)

# Add text
plt.text(5, 8.5, "DC Motor Control", horizontalalignment='center', fontsize=14, color='white', fontweight='bold')
plt.text(5, 1, "Neuro-Fuzzy System", horizontalalignment='center', fontsize=10, color='white')

# Save the figure
plt.savefig('icon.png', dpi=100, bbox_inches='tight', pad_inches=0.1)
plt.close()

print("Icon created successfully!")
