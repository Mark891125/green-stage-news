from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from scripts.github_news.news_pipeline import (
    choose_news_date,
    collection_since_date,
    load_config,
)


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
    since_date = collection_since_date(
        news_date,
        int(config.get("collection_lookback_days", 1)),
    )
    raw_path = Path(config["raw_dir"]) / f"{news_date}.jsonl"
    raw_path.parent.mkdir(parents=True, exist_ok=True)

    with raw_path.open("w", encoding="utf-8") as handle:
        for category, category_config in config["categories"].items():
            for source in category_config["sources"]:
                for item in collect_source(source, since_date):
                    item["category"] = category
                    item["source"] = source["type"]
                    handle.write(json.dumps(item, ensure_ascii=False) + "\n")

    print(f"wrote raw candidates to {raw_path}")
    return 0


def collect_source(source: dict[str, Any], since_date: str) -> list[dict[str, Any]]:
    source_type = source["type"]
    if source_type == "repo":
        cmd = [
            "gh",
            "search",
            "repos",
            source["query"],
            "--updated",
            f">={since_date}",
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
            f">={since_date}",
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
            f">={since_date}",
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

    try:
        completed = subprocess.run(cmd, check=True, text=True, capture_output=True)
        return json.loads(completed.stdout)
    except (FileNotFoundError, subprocess.CalledProcessError, json.JSONDecodeError) as exc:
        _warn_collect_failure(source, exc)
        return []


def _warn_collect_failure(source: dict[str, Any], exc: Exception) -> None:
    detail = str(exc)
    if isinstance(exc, subprocess.CalledProcessError) and exc.stderr:
        detail = exc.stderr.strip()
    print(
        f"warning: skipped {source['type']} source {source.get('query', '')!r}: {detail}",
        file=sys.stderr,
    )


if __name__ == "__main__":
    raise SystemExit(main())
