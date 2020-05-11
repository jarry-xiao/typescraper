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
image_dir = os.path.join(base_dir, "images")

q_kb = Keyboard(os.path.join(base_dir, "configs/qwerty/qwerty_config.json"))

qwerty = psql.read_sql("select * from qwerty", conn)

def get_char_transitions(user):
    query = """
        select ch_prev, ch, ms, race_date
        from keystrokes
        where forward 
              and forward_prev
              and user_id = %s
              and seq_index > 1
    """
    return psql.read_sql(query, conn, params=[user])


def get_transition_data(user):
    transitions = get_char_transitions(user)
    data = transitions.merge(
        qwerty, left_on="ch_prev", right_on="ch", suffixes=["_next", ""]
    )
    del data["ch"]
    data = data.merge(
        qwerty, left_on="ch_next", right_on="ch", suffixes=["_prev", "_next"]
    )
    del data["ch"]
    return data[data.ms < data.ms.quantile(0.99)]


def get_wpm_data(user):
    query = """
        select race_date, avg(wpm) as wpm, avg(accuracy) as accuracy
        from wpm
        where user_id = %s
        group by race_date
        order by race_date
    """
    return psql.read_sql(query, conn, params=[user])

def get_mistake_data(user):
    query = """
        select date(race_date) as race_date,
               cast(sum(ms * (1 - forward::int)) as float) / sum(ms) as mistake_score
        from keystrokes 
        where user_id = %s
        group by race_date
    """
    return psql.read_sql(query, conn, params=[user])

for user in [12, 6, 19, 8]:
    logger.info(f"Generating graphs for user {user}")
    ts = get_transition_data(user) 
    ts.race_date = pd.to_datetime(ts.race_date.dt.date)
    ts = ts.groupby("race_date").ms.mean().reset_index()
    ts = ts[ts.ms < ts.ms.quantile(.99)]
    score = get_mistake_data(user)
    score.race_date = pd.to_datetime(score.race_date)
    score = score[score.mistake_score < 1]
    wpm = get_wpm_data(user)
    data = wpm.merge(ts, on="race_date").merge(score, on="race_date")
    plt.figure(figsize=(20, 12))
    plt.subplot(2, 2, 1)
    plt.scatter(data.race_date, data.wpm)
    plt.xlabel("Race Date")
    plt.ylabel("WPM")
    plt.title(f"WPM for user {user}")
    plt.subplot(2, 2, 2)
    plt.scatter(data.race_date, data.accuracy)
    plt.xlabel("Race Date")
    plt.ylabel("Accuracy")
    plt.title(f"Accuracy for user {user}")
    plt.subplot(2, 2, 3)
    plt.scatter(data.race_date, data.ms)
    plt.xlabel("Race Date")
    plt.ylabel("Latency (ms)")
    plt.title(f"Latency (ms) for user {user}")
    plt.subplot(2, 2, 4)
    plt.scatter(data.race_date, data.mistake_score)
    plt.xlabel("Race Date")
    plt.ylabel(f"Mistake score for user {user}")
    plt.savefig(os.path.join(image_dir, f"improvement/{user}_stats.png"))
    plt.figure(figsize=(12, 8))
    plt.scatter(data.accuracy, data.wpm, label="normalized accuracy")
    plt.scatter(data.ms, data.wpm, label="normalized ms")
    plt.title(f"Scatter Plot of Latency and Accuracy vs. WPM for User {user}")
    plt.ylabel("WPM") 
    plt.legend()
    plt.savefig(os.path.join(image_dir, f"improvement/{user}_scatter.png"))
    display(data.corr())
