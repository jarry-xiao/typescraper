import os
import argparse
import re

import psycopg2
import pandas as pd

from utils.db import df_to_postgres


class KeyboardLoader:

    def __init__(self, filepath):
        self.conn = psycopg2.connect(dbname="typeracer", user="typescraper")
        self.cur = self.conn.cursor()
        self.table_name = os.path.basename(filepath).split('.')[0]
        self.key_map = pd.read_csv(filepath)
        self.key_map.row = self.key_map.row.astype(int)

    def __call__(self):
        df_to_postgres(self.key_map, self.table_name, self.conn)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("filepath")
    args = parser.parse_args()
    kb_loader = KeyboardLoader(args.filepath)
    kb_loader()
