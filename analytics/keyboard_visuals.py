import os
import logging

from keyboard import Keyboard

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import psycopg2
import pandas as pd
import pandas.io.sql as psql
from IPython.display import display

logging.basicConfig()
logger = logging.getLogger()
logger.setLevel(logging.INFO)
conn = psycopg2.connect(dbname="typeracer", user="typescraper")

base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
image_dir = os.path.join(base_dir, "images/keyboard_diagrams")

q_kb = Keyboard(os.path.join(base_dir, "configs/qwerty/qwerty_config.json"))
d_kb = Keyboard(os.path.join(base_dir, "configs/dvorak/dvorak_config.json"))
c_kb = Keyboard(os.path.join(base_dir, "configs/colemak/colemak_config.json"))

qwerty = psql.read_sql("select * from qwerty", conn)
dvorak = psql.read_sql("select * from dvorak", conn)


### Keyboard Layout Heatmaps
logger.info("Fetching count data...")
counts = psql.read_sql(
    """
        select ch, count(ch) from keystrokes
        join users on keystrokes.user_id = users.user_id
        where ch != ''
        group by ch
    """,
    conn,
)
logger.info("Fetched count data")

q_kb.make_heatmap(
    dict(zip(counts.ch, counts["count"])),
    alpha=0.8,
    interpolation='gaussian'
)
plt.show()
q_kb.save(os.path.join(image_dir, "keyboard_diagrams/qwerty_heatmap.png"))
logger.info("Generated QWERTY heatmap")

d_kb.make_heatmap(
    dict(zip(counts.ch, counts["count"])),
    alpha=0.8,
    interpolation='gaussian'
)
plt.show()
d_kb.save(os.path.join(image_dir, "keyboard_diagrams/dvorak_heatmap.png"))
logger.info("Generated Dvorak heatmap")

c_kb.make_heatmap(
    dict(zip(counts.ch, counts["count"])),
    alpha=0.8,
    interpolation='gaussian'
)
plt.show()
c_kb.save(os.path.join(image_dir, "keyboard_diagrams/colemak_heatmap.png"))
logger.info("Generated Colemak heatmap")


### Keyboard Digit/Row Labels
colors = {
   'L1': 'm',
   'L2': 'r',
   'L3': 'y',
   'L4': 'g', 
   'R0': 'c',
   'R1': 'b',
   'R2': 'tab:orange' ,
   'R3': 'tab:purple' ,
   'R4': 'lime' ,
}

finger = {
    0: "thumb",
    1: "index",
    2: "middle",
    3: "ring",
    4: "pinky",
}

## Digit Labels
legend_elements = []
for key, group in qwerty.groupby(['hand', 'digit']):
    i = key[0] + str(key[1])
    h = "right" if key[0] == 'R' else "left"
    f = h + " " + finger[key[1]]
    color = colors[i]
    legend_elements.append(
        Line2D(
            [0],
            [0],
            color='w',
            markerfacecolor=color,
            alpha=0.5,
            marker='o',
            markersize=15,
            label=f
        )
    )
    for ch in group.ch.tolist():
        if ch == None or ch in q_kb.left_shift or ch in q_kb.right_shift:
            continue
        q_kb.fill_color(ch, color)
q_kb.make_colormap()
leg = q_kb.ax.legend(
    handles=legend_elements,
    loc='lower center',
    ncol=5,
    shadow=False,
    bbox_to_anchor=(.5, -.2),
    prop={'size': 12},
)
leg.get_frame().set_edgecolor('black')
plt.show()
q_kb.save(os.path.join(image_dir, "digits.png"))
logger.info("Generated Digit Visualization")


## Row Labels
row_colors = ['c', 'g', 'y', 'r', 'm']
for row, group in qwerty.groupby("row"):
    i = row + 2
    color = row_colors[i]
    for ch in group.ch.tolist():
        if ch == None or ch in q_kb.left_shift or ch in q_kb.right_shift:
            continue
        q_kb.fill_color(ch, color)
q_kb.make_colormap()
legend_elements = [
    Line2D([0], [0], color='w', markerfacecolor='m', alpha=0.5, marker='o', markersize=15, label='2'),
    Line2D([0], [0], color='w', markerfacecolor='r', alpha=0.5, marker='o', markersize=15, label='1'),
    Line2D([0], [0], color='w', markerfacecolor='y', alpha=0.5, marker='o', markersize=15, label='0'),
    Line2D([0], [0], color='w', markerfacecolor='g', alpha=0.5, marker='o', markersize=15, label='-1'),
    Line2D([0], [0], color='w', markerfacecolor='c', alpha=0.5, marker='o', markersize=15, label='-2'),
]
leg = q_kb.ax.legend(
    handles=legend_elements,
    loc='lower center',
    ncol=5,
    shadow=False,
    bbox_to_anchor=(.5, -.12),
    prop={'size': 12},
)
leg.get_frame().set_edgecolor('black')
plt.show()
q_kb.save(os.path.join(image_dir, "rows.png"))
logger.info("Generated Row Visualization")
