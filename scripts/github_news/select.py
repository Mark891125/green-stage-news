from __future__ import annotations

import argparse
from pathlib import Path

from scripts.github_news.news_pipeline import (
    choose_news_date,
    load_config,
    read_jsonl,
    select_top_items,
    write_json,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Select daily GitHub news items.")
    parser.add_argument("date", nargs="?", help="Beijing date, YYYY-MM-DD")
    parser.add_argument("--config", default="config/github-news.json")
    args = parser.parse_args()

    config = load_config(args.config)
    news_date = choose_news_date(args.date)
    raw_path = Path(config["raw_dir"]) / f"{news_date}.jsonl"
    selected_path = Path(config["selected_dir"]) / f"{news_date}.json"

    candidates = read_jsonl(raw_path)
    selected = select_top_items(candidates, config)
    write_json(selected_path, selected)

    counts = {}
    for item in selected:
        counts[item["category"]] = counts.get(item["category"], 0) + 1
    print(f"selected {len(selected)}/{config['daily_limit']} items for {news_date}: {counts}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
