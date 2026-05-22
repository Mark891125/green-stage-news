from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.github_news.news_pipeline import (
    choose_news_date,
    load_config,
    render_daily_markdown,
    update_index,
    write_daily_markdown,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Render selected GitHub news as Markdown.")
    parser.add_argument("date", nargs="?", help="Beijing date, YYYY-MM-DD")
    parser.add_argument("--config", default="config/github-news.json")
    args = parser.parse_args()

    config = load_config(args.config)
    news_date = choose_news_date(args.date)
    selected_path = Path(config["selected_dir"]) / f"{news_date}.json"
    if not selected_path.exists():
        raise FileNotFoundError(f"selected file not found: {selected_path}")

    items = json.loads(selected_path.read_text(encoding="utf-8"))
    markdown = render_daily_markdown(news_date, items, int(config["daily_limit"]))
    target = write_daily_markdown(config["news_dir"], news_date, markdown)
    update_index(config["news_dir"], news_date)
    print(f"rendered {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
