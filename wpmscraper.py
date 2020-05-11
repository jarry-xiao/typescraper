import argparse
from dateutil import parser

import pandas as pd

from utils.db import df_to_postgres
from typescraper import Scraper


class WPMScraper(Scraper):

    def load_next_date(self, user, user_id, date=None, n=100):
        query_list = []
        query_list.append(f"user={user}")
        query_list.append(f"n={n}")
        if date:
            query_list.append(f"startDate={date}")
        query = "&".join(query_list)
        soup = self.bsoup(f'race_history?{query}')
        table = soup.find("table", {"class": "scoresTable"})
        if not table:
            return False, None
        df = pd.read_html(str(table))[0]
        df.Date = pd.to_datetime(df.Date)
        df.Speed = df.Speed.str.split(' ').str[0].astype(int)
        df.Accuracy = df.Accuracy.str.strip('%').astype(float) / 100
        df["user_id"] = user_id
        df = df[["user_id", "Date", "Race #", "Speed", "Accuracy"]]
        df.columns = ["user_id", "race_date", "race_id", "wpm", "accuracy"]
        df.race_id = df.race_id.astype(int)
        df_to_postgres(df, "wpm", self.conn)
        next_date = df.tail(1).race_date.iloc[0]
        return True, next_date.strftime("%Y-%m-%d")

    def scrape(self, user):
        user_id = self.fetch_or_create_user(user)
        has_next, next_date = self.load_next_date(user, user_id)
        while has_next:
            has_next, next_date = self.load_next_date(user, user_id, date=next_date)


if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("username")
    args = arg_parser.parse_args()
    wmps = WPMScraper()
    wmps.scrape(args.username)
