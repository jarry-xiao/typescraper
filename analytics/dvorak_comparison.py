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

layouts = {}

qwerty_data = psql.read_sql("select * from qwerty", conn)
qwerty_data["temp"] = 1
qwerty = pd.merge(qwerty_data, qwerty_data, on="temp", how="outer", suffixes=["_prev", ""])
del qwerty["temp"]
q = qwerty[~qwerty.shifted & ~qwerty.shifted_prev]
q = q[((q.row < 2) | (q.col > 10)) & ((q.row_prev < 2) | (q.col_prev > 10))]
q = q[~pd.isnull(q.ch) & ~pd.isnull(q.ch_prev)]
q["row_span"] = q.row - q.row_prev
layouts["qwerty"] = q
dvorak_data = psql.read_sql("select * from dvorak", conn)
dvorak_data["temp"] = 1
dvorak = pd.merge(dvorak_data, dvorak_data, on="temp", how="outer", suffixes=["_prev", ""])
del dvorak["temp"]
d = dvorak[~dvorak.shifted & ~dvorak.shifted_prev]
d = d[((d.row < 2) | (d.col > 10)) & ((d.row_prev < 2) | (d.col_prev > 10))]
d = d[~pd.isnull(d.ch) & ~pd.isnull(d.ch_prev)]
d["row_span"] = d.row - d.row_prev
layouts["dvorak"] = d 
colemak_data = psql.read_sql("select * from colemak", conn)
colemak_data["temp"] = 1
colemak = pd.merge(colemak_data, colemak_data, on="temp", how="outer", suffixes=["_prev", ""])
del colemak["temp"]
c = colemak[~colemak.shifted & ~colemak.shifted_prev]
c = c[((c.row < 2) | (c.col > 10)) & ((c.row_prev < 2) | (c.col_prev > 10))]
c = c[~pd.isnull(c.ch) & ~pd.isnull(c.ch_prev)]
c["row_span"] = c.row - c.row_prev
layouts["colemak"] = c


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
    df["col_diff"] = df.col - df.col_prev
    df["row_diff"] = df.row - df.row_prev
    return df

def get_smoothed_frequencies(df, base_layout="qwerty", remapped_layout="dvorak"):
    keys = [f"{k}{s}" for k in ["hand", "row", "col", "digit"] for s in ["", "_prev"]] + ["row_span"]
    
    d_group = df.groupby(["hand", "hand_prev", "digit", "digit_prev", "row_span"]).ms.agg(["mean", "count"])
    r_group = df.groupby(["hand", "hand_prev", "row_diff", "col_diff"]).ms.agg(["mean", "count"])
    reversed_group = df.groupby(["row_prev", "col_prev", "row", "col"]).ms.agg(["mean", "count", "sum"]).reset_index()
    reversed_group = reversed_group.rename(
        columns={"col_prev": "col", "row": "row_prev", "row_prev": "row", "col": "col_prev"}
    ) 

    df_stats = df.groupby(["ch_prev", "ch", "trans", "row_diff", "col_diff"] + keys).ms.agg(["mean", "count", "sum"]).reset_index()
    base_l = layouts[base_layout]
    neighbors = base_l[(base_l.col == base_l.col_prev) & (base_l.row_span.abs() <= 1)]
    neighbors = neighbors[["ch_prev", "ch"]]
    df_stats = df_stats.merge(reversed_group, on = ["row_prev", "col_prev", "row", "col"], suffixes=["", "_rev"])
    df_stats = df_stats.merge(d_group, on=["hand", "hand_prev", "digit", "digit_prev", "row_span"], suffixes=["", "_d"])
    df_stats = df_stats.merge(r_group, on=["hand", "hand_prev", "row_diff", "col_diff"], suffixes=["", "_r"])
    neighbor_stats = df_stats.merge(neighbors, on=["ch"], suffixes=["", "_n"])
    neighbor_stats = neighbor_stats[["ch_prev", "ch", "ch_prev_n"]] 
    neighbor_stats = neighbor_stats.merge(df_stats, left_on=["ch_prev", "ch_prev_n"], right_on=["ch_prev", "ch"], suffixes=["", "_n"])
    del neighbor_stats["ch_n"] 
    neighbor_stats = neighbor_stats.groupby(["ch_prev", "ch"])[["sum", "count", "sum_rev", "count_rev"]].agg(["sum"]).reset_index()
    neighbor_stats.columns = ["ch_prev", "ch", "sum", "count", "sum_rev", "count_rev"]
    neighbor_stats["mean"] = (neighbor_stats["sum"] + neighbor_stats["sum_rev"]) / (neighbor_stats["count"] + neighbor_stats["count_rev"])
    neighbor_stats = neighbor_stats[["ch_prev", "ch", "mean", "count"]]
    neighbor_ = neighbor_stats.merge(base_l[["ch_prev", "ch", "row", "row_prev", "col", "col_prev"]], on=["ch", "ch_prev"])
    neighbor_ = neighbor_[["row", "row_prev", "col", "col_prev", "mean", "count"]]
    df_stats = df_stats.merge(neighbor_, on=["row", "row_prev", "col", "col_prev"], suffixes=["", "_n"])
    
    neighbor_stats = df_stats.merge(neighbors, on=["ch_prev"], suffixes=["", "_n"])
    neighbor_stats = neighbor_stats[["ch_prev", "ch", "ch_n"]] 
    neighbor_stats = neighbor_stats.merge(df_stats, left_on=["ch_n", "ch"], right_on=["ch_prev", "ch"], suffixes=["", "_n"])
    del neighbor_stats["ch_prev_n"] 
    neighbor_stats = neighbor_stats.groupby(["ch_prev", "ch"])[["sum", "count", "sum_rev", "count_rev"]].agg(["sum"]).reset_index()
    neighbor_stats.columns = ["ch_prev", "ch", "sum", "count", "sum_rev", "count_rev"]
    neighbor_stats["mean"] = (neighbor_stats["sum"] + neighbor_stats["sum_rev"]) / (neighbor_stats["count"] + neighbor_stats["count_rev"])
    neighbor_stats = neighbor_stats[["ch_prev", "ch", "mean", "count"]]
    neighbor_p = neighbor_stats.merge(base_l[["ch_prev", "ch", "row", "row_prev", "col", "col_prev"]], on=["ch", "ch_prev"])
    neighbor_p = neighbor_p[["row", "row_prev", "col", "col_prev", "mean", "count"]]
    df_stats = df_stats.merge(neighbor_p, on=["row", "row_prev", "col", "col_prev"], suffixes=["", "_p"])
    df_stats = df_stats[(df_stats.row != -2) & (df_stats.row_prev != -2)]
    
    
    if not isinstance(remapped_layout, list):
        remapped_layout = [remapped_layout]
        
    remaps = []
    for key in remapped_layout:
        layout = layouts[key]
        keys = [f"{k}{s}" for k in ["hand", "row", "col", "digit"] for s in ["", "_prev"]]
        df_remap = df.merge(layout, on=keys, suffixes=["", "_d"], how="right")
        df_remap["row_span"] = df_remap["row"] - df_remap["row_prev"]
        df_remap["trans"] = df_remap["ch_prev_d"] + " -> " + df_remap["ch_d"]
        df_remap = df_remap.groupby(["ch_prev_d", "ch_d", "trans", "row_diff", "col_diff"] + keys + ["row_span"]).ms.agg(["mean", "count"]).reset_index()
        df_remap = df_remap.merge(reversed_group, on = ["row_prev", "col_prev", "row", "col"], suffixes=["", "_rev"])
        df_remap = df_remap.merge(d_group, on=["hand", "hand_prev", "digit", "digit_prev", "row_span"], suffixes=["", "_d"])
        df_remap = df_remap.merge(r_group, on=["hand", "hand_prev", "row_diff", "col_diff"], suffixes=["", "_r"])
        df_remap = df_remap.merge(neighbor_, on=["row", "row_prev", "col", "col_prev"], suffixes=["", "_n"])
        df_remap = df_remap.merge(neighbor_p, on=["row", "row_prev", "col", "col_prev"], suffixes=["", "_p"])
        df_remap = df_remap.rename(columns={"sum": "sum_rev"})
        df_remap = df_remap[(df_remap.row != -2) & (df_remap.row_prev != -2)]
        remaps.append(df_remap)
    return df_stats, remaps 

    
def score(c):
    data = []
    for i in range(len(c[1])):
        res = c[0].merge(c[1][i], on="trans")
        res = res[(res["sum"] > 0)]

        res.mean_rev_y = res.mean_rev_y.fillna(0)
        res.mean_y = res.mean_y.fillna(0)
        res.mean_n_y = res.mean_n_y.fillna(0)
        res.mean_p_y = res.mean_p_y.fillna(0)
        res.mean_r_y = res.mean_r_y.fillna(0)
        score = res.mean_y * res.count_y 
        score += res.mean_rev_y * res.count_rev_y
        score += res.mean_n_y * res.count_n_y
        score += res.mean_p_y * res.count_p_y
        score += res.mean_r_y * res.count_r_y
        res["new_count_y"] = res.count_y
        res["new_count_y"] += res.count_rev_y
        res["new_count_y"] += res.count_n_y
        res["new_count_y"] += res.count_p_y
        res["new_count_y"] += res.count_r_y
        res["score_y"] = score / res["new_count_y"]
        res["total_y"] = res.score_y * res.count_x 

        res.mean_rev_x = res.mean_rev_x.fillna(0)
        res.mean_x = res.mean_x.fillna(0)
        res.mean_n_x = res.mean_n_x.fillna(0)
        res.mean_p_x = res.mean_p_x.fillna(0)
        res.mean_r_x = res.mean_r_x.fillna(0)
        score = res.mean_x * res.count_x
        score += res.mean_rev_x * res.count_rev_x
        score += res.mean_n_x * res.count_n_x
        score += res.mean_p_x * res.count_p_x
        score += res.mean_r_x * res.count_r_x
        res["new_count_x"] = res.count_x
        res["new_count_x"] += res.count_rev_x
        res["new_count_x"] += res.count_n_x
        res["new_count_x"] += res.count_p_x
        res["new_count_x"] += res.count_r_x
        res["score_x"] = score / res["new_count_x"]
        res["total_x"] = res.score_x * res.count_x 
        
        res = res.sort_values(by="total_y", ascending=False)
        res["gt"] = res.total_y < res.total_x
        print(res["sum"].sum(), res.total_y.sum(), res.total_x.sum())
        print(res.score_y.mean(), res.score_x.mean())
        print(res["gt"].mean())
        if i == 0:
            data.append(res.score_x.mean())
            data.append(res.score_x.sum())
            data.append(res["mean_x"].sum())
        data.append(res.score_y.mean())
        data.append(res.score_y.sum() / res.score_x.sum())
        data.append(res.score_y.sum())
    return data
            
rows = []
for user in qwerty_users.user_id:
    c = get_smoothed_frequencies(get_user_data(user), remapped_layout=["dvorak", "colemak"])
    rows.append([user] + score(c))
qdata = pd.DataFrame(
    rows,
    columns=["user", "mean_qw", "score_qw", "actual", "mean_dv", "ratio_dv", "score_dv", "mean_cm", "ratio_cm", "score_cm"]
)

rows = []
for user in dvorak_users.user_id:
    c = get_smoothed_frequencies(get_user_data(user), remapped_layout=["qwerty", "colemak"])
    rows.append([user] + score(c))
ddata = pd.DataFrame(
    rows,
    columns=["user", "mean_dv", "score_dv", "actual", "mean_qw", "ratio_qw", "score_qw", "mean_cm", "ratio_cm", "score_cm"]
)

display(qdata)
display(ddata)

