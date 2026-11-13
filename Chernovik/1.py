# a=[]
# c = int(input())
# b = int(input())
# z = int(input())
# s = int(input())
# a = [c,b,z,s]
# print(min(a))
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle, Wedge
import numpy as np

fig, ax = plt.subplots(figsize=(6, 6))
ax.set_xlim(0, 10)
ax.set_ylim(0, 10)
ax.set_aspect('equal')
ax.axis('off')

# Три слоя торта
ax.add_patch(Rectangle((1, 1), 8, 2, color="#C57943"))   # низ
ax.add_patch(Rectangle((1.3, 3), 7.4, 1.8, color="#FFB6C1"))  # середина
ax.add_patch(Rectangle((1.6, 4.8), 6.8, 1.6, color="#FFFACD")) # верх

# Глазурь каплями
for x in np.linspace(1.6, 8.4, 12):
    ax.add_patch(Wedge((x, 4.8), 0.3, 180, 360, color="#FF1493"))

# Свечка
ax.add_patch(Rectangle((4.7, 6.4), 0.6, 1.5, color="#FFD700"))
# Пламя
ax.add_patch(Circle((5, 8.2), 0.3, color="orange"))

ax.set_title("с днём рождения!", fontsize=16)
plt.show()