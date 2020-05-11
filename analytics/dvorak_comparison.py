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

logger.info("Fetching user data...")
users = psql.read_sql(
    """
        select username, users.user_id, type, n from users join ( 
            select user_id, count(user_id) as n
            from keystrokes
            group by keystrokes.user_id
        ) counts on counts.user_id = users.user_id
    """,
    conn
)
logger.info("Retrieved user data")

dvorak_users = users[users.type == 'dvorak']
qwerty_users = users[users.type == 'qwerty']

base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
image_dir = os.path.join(base_dir, "images")

q_kb = Keyboard(os.path.join(base_dir, "configs/qwerty/qwerty_config.json"))
d_kb = Keyboard(os.path.join(base_dir, "configs/dvorak/dvorak_config.json"))

qwerty_data = psql.read_sql("select * from qwerty", conn)
qwerty_data["temp"] = 1
qwerty = pd.merge(qwerty_data, qwerty_data, on="temp", how="outer", suffixes=["_prev", ""])
del qwerty["temp"]
dvorak_data = psql.read_sql("select * from dvorak", conn)
dvorak_data["temp"] = 1
dvorak = pd.merge(dvorak_data, dvorak_data, on="temp", how="outer", suffixes=["_prev", ""])
del dvorak["temp"]


