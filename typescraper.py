import argparse
import pdb
from dateutil import parser
from collections import deque
import random
import re

import psycopg2
import pandas as pd
import requests
from bs4 import BeautifulSoup

from utils.db import df_to_postgres


class Scraper:

    def __init__(self, max_races=5000):
        self.base = 'https://data.typeracer.com/pit/'
        self.conn = psycopg2.connect(dbname="typeracer", user="typescraper")
        self.cur = self.conn.cursor()
        self.max_races = max_races

    def fetch_or_create_user(self, user):
        self.cur.execute(
            "select user_id from users where username=%s",
            [user],
        )
        user_id = self.cur.fetchone()
        if not user_id:
            self.cur.execute(
                """
                    insert into users(username)
                    values(%s)
                    returning user_id
                """,
                [user],
            )
            user_id = self.cur.fetchone()
            self.conn.commit()
        return user_id[0]
        
    def bsoup(self, query):
        print(self.base + query)
        r  = requests.get(self.base + query)
        return BeautifulSoup(r.text, 'html.parser')


class TypeScraper(Scraper):

    def load_text(self, text_id, raw_text):
        self.cur.execute(
            "insert into texts(text_id, raw_text) values(%s, %s) on conflict do nothing",
            [text_id, raw_text],
        )
        self.conn.commit()

    def scrape(self, user):
        user_id = self.fetch_or_create_user(user)
        max_race_id = self.get_max_race(user)
        population = range(1, max_race_id + 1)
        if max_race_id > self.max_races:
            population = random.sample(population, self.max_races)
        for i, race_id in enumerate(population):
            print(i, race_id)
            self.fetch_user_data(user, user_id, race_id)

    def get_max_race(self, user):
        soup = self.bsoup(f'profile?user={user}')
        table = soup.find("table", {"class": "scoresTable"})
        return int(table.find(href=True).text)

    def parse_token(self, token):
        if len(token) == 0:
            return []
        delim = re.search('[^\d]', token)
        if delim is None:
            return []
        i = delim.start()
        ch_idx = int(token[:i])
        end = i + 1
        if end == len(token):
            return []
        end = end + 1 if token[end] == '\\' else end 
        ch = token[end]
        if token[i] == '+' or token[i] == '$':
            typed = True 
        elif token[i] == '-':
            typed = False
        else:
            print("Encountered strange character. Please investigate")
            return self.parse_token(token[end + 1:])
        return [[ch, ch_idx, typed]] + self.parse_token(token[end + 1:])

    def fetch_user_data(self, user, user_id, race_id):
        self.cur.execute(
            "select exists(select 1 from keystrokes where user_id = %s and race_id = %s)",
            [user_id, race_id],
        )
        exists = self.cur.fetchone()
        if exists and exists[0]:
            return
        soup = self.bsoup(f'result?id=|tr:{user}|{race_id}')
        var_pattern = re.compile('var typingLog = ')
        data_pattern = re.compile(r'(?<=").*(?=,";)')
        script = soup.find("script", text=var_pattern)
        if not script:
            print(f"failed to fetch data for {user}|{race_id}")
            return 
        raw_text = soup.find_all("div", {"class": "fullTextStr"})[0].text
        print(raw_text)
        text_info = soup.find_all(href=re.compile('text_info'))[-1]
        text_id = int(text_info.get("href").split("=")[-1])
        self.load_text(text_id, raw_text)
        race_date = parser.parse(
            soup
            .find("table", {"class": "raceDetails"})
            .find(text=re.compile("Date"))
            .parent.nextSibling.next_sibling.text
            .strip()
        )
        data = str(re.findall(data_pattern, script.text)[0])
        data = re.split(r'(?<!\d[\+\-\$])\|', data)[-1]
        data = re.split(r'(?<!\d[\+\-\$]),', data)
        print(data)
        queue = deque(data)
        keystrokes = []
        keystrokes.append([text_id, user_id, race_date, race_id, "", 0, True, -1])
        while queue:
            word_idx = int(queue.popleft())
            length = int(queue.popleft())
            for i in range(length):
                ms = int(queue.popleft())
                token = queue.popleft()
                stats = self.parse_token(token)
                ms //= len(stats)
                for ch, ch_idx, typed in stats:
                    keystrokes.append(
                        [text_id, user_id, race_date, race_id, ch, ms, typed, word_idx + ch_idx]
                    )
        action_df = pd.DataFrame(
            keystrokes,
            columns=[
                'text_id',
                'user_id',
                'race_date',
                'race_id',
                'ch',
                'ms',
                'forward',
                'ch_index',
            ],
        ).reset_index()
        action_df = action_df.rename(columns={"index": "seq_index"})
        key = ['text_id', 'user_id', 'race_date', 'race_id']
        action_df = action_df.merge(action_df, on=key, suffixes=["", "_prev"])
        action_df = action_df[action_df.seq_index - action_df.seq_index_prev == 1]
        action_df = action_df[
            [*key, "ch_prev", "ch", "ms", "forward_prev", "forward", "ch_index", "seq_index"]
        ]
        self.cur.execute(
            "select exists(select 1 from keystrokes where user_id = %s and text_id = %s and race_id = %s)",
            [user_id, text_id, race_id],
        )
        exists = self.cur.fetchone()
        if exists and not exists[0]:
            print("Writing to DB", "\n")
            df_to_postgres(action_df, "keystrokes", self.conn)


if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("username")
    args = arg_parser.parse_args()
    ts = TypeScraper()
    ts.scrape(args.username)
