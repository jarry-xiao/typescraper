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

layouts = {}

qwerty_data = psql.read_sql("select * from qwerty", conn)
qwerty_data["temp"] = 1
qwerty = pd.merge(qwerty_data, qwerty_data, on="temp", how="outer", suffixes=["_prev", ""])
del qwerty["temp"]
layouts["qwerty"] = qwerty
dvorak_data = psql.read_sql("select * from dvorak", conn)
dvorak_data["temp"] = 1
dvorak = pd.merge(dvorak_data, dvorak_data, on="temp", how="outer", suffixes=["_prev", ""])
del dvorak["temp"]
layouts["dvorak"] = dvorak

def get_user_data(user):
    if user in qwerty_users.user_id.tolist():
        layout = layouts["qwerty"]
    elif user in dvorak_users.user_id.tolist():
        layout = layouts["dvorak"]
    else:
        return None
    query = """
        with no_mistakes as (
            select race_id, ch_index, count(ms) as c, max(seq_index) m_i
            from keystrokes
            where user_id = %s
            group by race_id, ch_index
        )
         select ch_prev, ch, ms
         from keystrokes k join no_mistakes n
         on k.race_id = n.race_id and k.ch_index = n.ch_index
         where user_id = %s and forward and forward_prev and mod(c, 2) = 1 and seq_index = m_i
    """
    df = psql.read_sql(query, conn, params=[user, user])
    df = df[df.ms < df.ms.quantile(.99)]
    df = df.merge(layout, on=["ch_prev", "ch"], how="right")
    df = df[~df.shifted & ~df.shifted_prev]
    df["trans"] = df["ch_prev"] + " -> " + df["ch"]
    return df


def get_smoothed_frequencies(df, remapped_layout="dvorak"):
    keys = [f"{k}{s}" for k in ["hand", "digit", "shifted", "row"] for s in ["", "_prev"]]
    dd_group = df[df.hand != df.hand_prev].groupby(["digit", "digit_prev"]).ms.agg(["mean", "std", "count"])
    dr_group = df[df.hand != df.hand_prev].groupby(["row", "row_prev"]).ms.agg(["mean", "std", "count"])
    sd_group = df[df.hand == df.hand_prev].groupby(["digit", "digit_prev"]).ms.agg(["mean", "std", "count"])
    sr_group = df[df.hand == df.hand_prev].groupby(["row", "row_prev"]).ms.agg(["mean", "std", "count"])
    
    df_stats = df.groupby(["ch_prev", "ch", "trans"] + keys).ms.agg(["mean", "std", "count", "sum"]).reset_index()
    d_df_stats = df_stats[df_stats.hand != df_stats.hand_prev]
    d_df_stats = d_df_stats.merge(dd_group, on=["digit", "digit_prev"], suffixes=["", "_d"])
    d_df_stats = d_df_stats.merge(dr_group, on=["row", "row_prev"], suffixes=["", "_r"])

    s_df_stats = df_stats[df_stats.hand == df_stats.hand_prev]
    s_df_stats = s_df_stats.merge(sd_group, on=["digit", "digit_prev"], suffixes=["", "_d"])
    s_df_stats = s_df_stats.merge(sr_group, on=["row", "row_prev"], suffixes=["", "_r"])
    df_stats = pd.concat([d_df_stats, s_df_stats])
    
    layout = layouts[remapped_layout]
    df_remap = df.merge(layout[~layout.shifted & ~layout.shifted_prev], on=keys, suffixes=["", "_d"], how="right")
    df_remap["trans"] = df_remap["ch_prev_d"] + " -> " + df_remap["ch_d"]
    df_remap = df_remap.groupby(["ch_prev_d", "ch_d", "trans"] + keys).ms.agg(["mean", "std", "count"]).reset_index()

    d_df_remap = df_remap[df_remap.hand != df_remap.hand_prev]
    d_df_remap = d_df_remap.merge(dd_group, on=["digit", "digit_prev"], suffixes=["", "_d"])
    d_df_remap = d_df_remap.merge(dr_group, on=["row", "row_prev"], suffixes=["", "_r"])

    s_df_remap = df_remap[df_remap.hand == df_remap.hand_prev]
    s_df_remap = s_df_remap.merge(sd_group, on=["digit", "digit_prev"], suffixes=["", "_d"])
    s_df_remap = s_df_remap.merge(sr_group, on=["row", "row_prev"], suffixes=["", "_r"])

    df_remap = pd.concat([d_df_remap, s_df_remap])
    df_remap = df_remap.rename(columns={"ch_d": "ch", "ch_prev_d": "ch_prev"})
    return df_stats, df_remap


def score_results(df_stats, df_remap):
    c = df_stats.merge(df_remap, on=["trans"])
    c["sum_y"] = c["mean_y"] * c["count_y"] + c["mean_d_y"] * c["count_d_y"] + c["mean_r_y"] * c["count_d_y"]
    c["total_y"] = c["count_y"] + c["count_d_y"] + c["count_r_y"]
    c["score_y"] = c["sum_y"] * c["count_x"] / c["total_y"]
    c["sum_x"] = c["mean_x"] * c["count_x"] + c["mean_d_x"] * c["count_d_x"] + c["mean_r_x"] * c["count_d_x"]
    c["total_x"] = c["count_x"] + c["count_d_x"] + c["count_r_x"]
    c["score_x"] = c["sum_x"] * c["count_x"] / c["total_x"]
    return c.score_x.sum(), c.score_y.sum(), c["sum"].sum()


res = []
for user in qwerty_users.user_id.tolist():
    df = get_user_data(user)
    df_stats, df_remap = get_smoothed_frequencies(df, "dvorak")
    qs, ds, actual = score_results(df_stats, df_remap)
    print(user)
    print(qs, ds, actual) 
    print(ds/qs)
    print()
    res.append([qs, ds, actual, "qwerty"])

for user in dvorak_users.user_id.tolist():
    df = get_user_data(user)
    df_stats, df_remap = get_smoothed_frequencies(df, "qwerty")
    ds, qs, actual = score_results(df_stats, df_remap)
    print(user)
    print(qs, ds, actual) 
    print(qs/ds)
    print()
    res.append([qs, ds, actual, "dvorak"])

res = pd.DataFrame(res, columns=["QScore", "DScore", "Actual", "Type"])
display(res)
from IPython import embed
embed()
