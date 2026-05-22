from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

from scripts.github_news.news_pipeline import choose_news_date, load_config


REPO_FIELDS = "fullName,description,url,stargazersCount,language,createdAt,updatedAt,pushedAt,isArchived,isFork"
ISSUE_FIELDS = "title,url,repository,author,commentsCount,createdAt,updatedAt,state"
PR_FIELDS = "title,url,repository,author,commentsCount,createdAt,updatedAt,closedAt,state"


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect GitHub news candidates with gh.")
    parser.add_argument("date", nargs="?", help="Beijing date, YYYY-MM-DD")
    parser.add_argument("--config", default="config/github-news.json")
    args = parser.parse_args()

    config = load_config(args.config)
    news_date = choose_news_date(args.date)
    raw_path = Path(config["raw_dir"]) / f"{news_date}.jsonl"
    raw_path.parent.mkdir(parents=True, exist_ok=True)

    with raw_path.open("w", encoding="utf-8") as handle:
        for category, category_config in config["categories"].items():
            for source in category_config["sources"]:
                for item in collect_source(source, news_date):
                    item["category"] = category
                    item["source"] = source["type"]
                    handle.write(json.dumps(item, ensure_ascii=False) + "\n")

    print(f"wrote raw candidates to {raw_path}")
    return 0


def collect_source(source: dict[str, Any], news_date: str) -> list[dict[str, Any]]:
    source_type = source["type"]
    if source_type == "repo":
        cmd = [
            "gh",
            "search",
            "repos",
            source["query"],
            "--updated",
            f">={news_date}",
            "--archived=false",
            "--include-forks=false",
            "--sort",
            source.get("sort", "updated"),
            "--order",
            "desc",
            "--limit",
            str(source.get("limit", 50)),
            "--json",
            REPO_FIELDS,
        ]
    elif source_type == "pr":
        cmd = [
            "gh",
            "search",
            "prs",
            source["query"],
            "--merged",
            "--merged-at",
            f">={news_date}",
            "--comments",
            source.get("comments", ">=5"),
            "--sort",
            "interactions",
            "--order",
            "desc",
            "--limit",
            str(source.get("limit", 30)),
            "--json",
            PR_FIELDS,
        ]
    elif source_type == "issue":
        cmd = [
            "gh",
            "search",
            "issues",
            source["query"],
            "--state",
            "open",
            "--updated",
            f">={news_date}",
            "--comments",
            source.get("comments", ">=10"),
            "--sort",
            "interactions",
            "--order",
            "desc",
            "--limit",
            str(source.get("limit", 30)),
            "--json",
            ISSUE_FIELDS,
        ]
    else:
        raise ValueError(f"unsupported source type: {source_type}")

    completed = subprocess.run(cmd, check=True, text=True, capture_output=True)
    return json.loads(completed.stdout)


if __name__ == "__main__":
    raise SystemExit(main())
