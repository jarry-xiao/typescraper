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


dat_5 = get_transition_data(5)

### Histogram
shifted = dat_5[dat_5.shifted_prev & ~dat_5.shifted_next]
notshifted = dat_5[~dat_5.shifted_prev & ~dat_5.shifted_next]
plt.hist(notshifted.ms, density=True, alpha=0.7, label="no Shift")
plt.hist(shifted.ms, density=True, alpha=0.7, label="Shift")
plt.title("Latency Density Histogram")
plt.legend()
plt.savefig(os.path.join(image_dir, "latency_histograms/shifted_latency_histogram_user_5.png"))

display(dat_5.groupby(["shifted_prev", "shifted_next"]).ms.agg(["mean", "std", "count"]))


### Keyboard Visual

finger = {
    0: "thumb",
    1: "index",
    2: "middle",
    3: "ring",
    4: "pinky",
}

shifted = dat_5[dat_5.shifted_next]
counts = shifted.groupby("ch_next").ms.count().reset_index()
to_keep = counts[counts.ms > 20].ch_next.tolist()
shifted = shifted[shifted.ch_next.isin(to_keep)]
q_kb.make_heatmap(
    shifted.groupby("ch_next").ms.mean().to_dict(), cmap='inferno'
)
q_kb.scale("lshift", 0.)
q_kb.scale("rshift", 0.)
q_kb.show_heatmap(cmap='inferno')
q_kb.save(os.path.join(image_dir, "keyboard_diagrams/shifted_heatmap_user_5.png"))

display(shifted.groupby("row_next").ms.agg(["mean", "std", "count"]))
shifted.hand_next = shifted.hand_next.map({"L": "left", "R": "right"})
shifted.digit_next = shifted.digit_next.map(finger)
display(shifted.groupby(["hand_next", "digit_next"]).ms.agg(["mean", "std", "count"]))

notshifted = dat_5[~dat_5.shifted_next]
counts = notshifted.groupby("ch_next").ms.count().reset_index()
to_keep = counts[counts.ms > 100].ch_next.tolist()
notshifted = notshifted[notshifted.ch_next.isin(to_keep)]
q_kb.make_heatmap(
    notshifted.groupby("ch_next").ms.mean().to_dict(), cmap='inferno'
)
q_kb.save(os.path.join(image_dir, "keyboard_diagrams/noshifted_heatmap_user_5.png"))
display(notshifted.groupby("row_next").ms.agg(["mean", "std", "count"]))
notshifted.hand_next = notshifted.hand_next.map({"L": "left", "R": "right"})
notshifted.digit_next = notshifted.digit_next.map(finger)
display(notshifted.groupby(["hand_next", "digit_next"]).ms.agg(["mean", "std", "count"]))


skw = {}
for user in [5, 6, 8, 12, 19]:
    dat = get_transition_data(user)
    transitions = dat[~dat.shifted_next & ~dat.shifted_prev]
    speeds = (
        transitions
        .groupby(["ch_prev", "ch_next"]).ms
        .agg(["mean", "std", "count"])
        .reset_index()
    )
    speeds = speeds[speeds.ch_prev != speeds.ch_next]
    speeds = speeds[speeds["count"] > 100]
    skw[user] = speeds["mean"].skew()
    plt.hist(speeds["mean"])
    plt.xlabel("Latency (ms)")
    plt.title(f"Transition Speeds for User {user}")
    plt.savefig(os.path.join(image_dir, f"latency_histograms/transition_histogram_{user}.png"))

skw_df = pd.DataFrame.from_dict(skw, orient='index').reset_index()
skw_df["user_id"] = skw_df["index"]
skw_df["skewness"] = skw_df[0]
skw_df = skw_df[skw_df.user_id.isin([5, 6, 12, 19, 8])]
display(skw_df[["user_id", "skewness"]].reset_index(drop=True))


transitions = dat_5[~dat_5.shifted_next & ~dat_5.shifted_prev]
speeds = transitions.groupby(["ch_prev", "ch_next"]).ms.agg(["mean", "std", "count"]).reset_index()
speeds = speeds[speeds.ch_prev != speeds.ch_next]
speeds = speeds[speeds["count"] > 100]
speeds = speeds[speeds["mean"] > 100]
display(speeds.sort_values(by="mean", ascending=False).reset_index(drop=True))

generated = set()

for k, group in speeds.groupby("ch_prev"):
    config = k + "_" + "".join(sorted(group.ch_next.tolist()))
    if config in generated:
        continue
    q_kb.fill_color(k, 'tab:blue')
    for ch in group.ch_next:
        q_kb.fill_color(ch, 'tab:orange')
    q_kb.make_colormap()
    q_kb.save(os.path.join(image_dir, f"transition_vis/vis_{config}.png"))
    
for k, group in speeds.groupby("ch_next"):
    config = "".join(sorted(group.ch_prev.tolist())) + "_" + k
    if config in generated:
        continue
    q_kb.fill_color(k, 'tab:orange')
    for ch in group.ch_prev:
        q_kb.fill_color(ch, 'tab:blue')
    q_kb.make_colormap()
    q_kb.save(os.path.join(image_dir, f"vis_{config}.png"))

dat_5 = dat_5.merge(speeds[["ch_prev", "ch_next"]])
dat_5.digit_prev = dat_5.digit_prev.map(finger)
dat_5.digit_next = dat_5.digit_next.map(finger)
valid_transitions = list(zip(speeds.ch_prev.tolist(), speeds.ch_next.tolist()))

for feats in (["hand", "digit", "row"], ["hand", "digit"]):
    keys = [f"{feat}_{pos}" for feat in feats for pos in ["prev", "next"]]
    unique_chars_next = dat_5.groupby(keys)["ch_next"].unique().reset_index()
    unique_chars_prev = dat_5.groupby(keys)["ch_prev"].unique().reset_index()
    group = dat_5.groupby(keys)["ms"].agg(["mean", "std", "count"]).reset_index()
    group = group.sort_values(by="mean", ascending=False)
    group = group.merge(unique_chars_prev, on=keys).merge(unique_chars_next, on=keys)
    if "row" in feats:
        group["row_span"] = (group.row_next - group.row_prev)
        cols = ["hand_prev", "digit_prev", "hand_next", "digit_next", "transitions", "row_span", "mean", "std", "count"]
    else:
        cols = ["hand_prev", "digit_prev", "hand_next", "digit_next", "transitions", "mean", "std", "count"]
    transitions = []
    for p, n in zip(group.ch_prev.tolist(), group.ch_next.tolist()):
        transitions.append(" | ".join([f"{pr} -> {nx}" for pr in p for nx in n if (pr, nx) in valid_transitions]))
    group["transitions"] = transitions
    display(group[cols].reset_index(drop=True))
