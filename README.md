# Typescraper

Typscraper is an open source scraper for fetching precise latency data from Typeracer.

You can read about this project on Medium:

[Part 1: Data Scraping and Cleaning](https://medium.com/@jarryxiao/data-mining-typeracer-part-1-b32817e65b03)

[Part 2: Exploration and Analytics](https://medium.com/@jarryxiao/data-mining-typeracer-part-2-5bfd0726f87e)

[Part 3: Modeling and Estimation] (https://medium.com/@jarryxiao/data-mining-typeracer-part-3-d71581e25341)

## Usage

If you want to reuse the code, you will need to download [PostgresSQL](https://www.postgresql.org/download/). If you use MacOS, the easiest way to install is through [Homebrew](https://brew.sh/)

`brew install postgressql`

Once installed, you can execute `./create_db` in the project root directory to set up all of the tables and permissions in the database.

To populate the database with latency stats, run `python typescraper %USERNAME` where `%USERNAME` is the username of the individual you want to collect latency data from. I would recommend using [conda](https://docs.conda.io/projects/conda/en/latest/user-guide/install/) or [virtualenv](https://virtualenv.pypa.io/en/latest/) to keep the development environment clean.

To add in keyboard layouts, run `python keyboardloader.py %CONFIG` where `%CONFIG` is a csv file found under the `configs` directory. `configs/qwerty/qwerty.csv` and `configs/dvorak/dvorak.csv` are included in the repository.

Lastly, to add WPM and Accuracy data, run `python wpmscraper %USERNAME`
