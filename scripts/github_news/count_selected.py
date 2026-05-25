from __future__ import annotations

import argparse
from pathlib import Path

from scripts.github_news.news_pipeline import (
    choose_news_date,
    load_config,
    selected_item_count,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Print selected GitHub news count.")
    parser.add_argument("date", nargs="?", help="Beijing date, YYYY-MM-DD")
    parser.add_argument("--config", default="config/github-news.json")
    args = parser.parse_args()

    config = load_config(args.config)
    news_date = choose_news_date(args.date)
    selected_path = Path(config["selected_dir"]) / f"{news_date}.json"
    print(selected_item_count(selected_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
