from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from zoneinfo import ZoneInfo


BEIJING_TZ = ZoneInfo("Asia/Shanghai")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def choose_news_date(date_arg: str | None, now_utc: str | None = None) -> str:
    if date_arg:
        if not DATE_RE.match(date_arg):
            raise ValueError("date must use YYYY-MM-DD format")
        return date_arg

    if now_utc:
        value = now_utc.replace("Z", "+00:00")
        now = datetime.fromisoformat(value)
    else:
        now = datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    return now.astimezone(BEIJING_TZ).date().isoformat()


def load_config(path: Path | str) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def read_jsonl(path: Path | str) -> list[dict[str, Any]]:
    result = []
    file_path = Path(path)
    if not file_path.exists():
        return result
    with file_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                result.append(json.loads(line))
    return result


def write_json(path: Path | str, payload: Any) -> None:
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def normalize_candidates(raw_items: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized = []
    for item in raw_items:
        value = _normalize_item(item)
        if value:
            normalized.append(value)
    return normalized


def _normalize_item(item: dict[str, Any]) -> dict[str, Any] | None:
    url = item.get("url") or item.get("html_url")
    if not isinstance(url, str) or not url.startswith("https://github.com/"):
        return None

    repository = item.get("repository")
    if isinstance(repository, dict):
        repository = repository.get("fullName") or repository.get("nameWithOwner")
    repository = repository or item.get("fullName") or _repo_from_url(url)
    if not repository:
        return None

    title = item.get("title") or item.get("name") or repository
    description = item.get("description") or item.get("body") or ""
    published_at = (
        item.get("published_at")
        or item.get("publishedAt")
        or item.get("mergedAt")
        or item.get("closedAt")
        or item.get("updatedAt")
        or item.get("pushedAt")
        or item.get("createdAt")
    )

    return {
        "category": item.get("category", "ai"),
        "source": item.get("source", "repo"),
        "title": str(title).strip(),
        "description": str(description).strip(),
        "repository": str(repository).strip(),
        "url": url,
        "stars": _to_int(item.get("stars", item.get("stargazersCount", 0))),
        "comments": _to_int(item.get("comments", item.get("commentsCount", 0))),
        "published_at": published_at or "",
    }


def select_top_items(
    candidates: Iterable[dict[str, Any]], config: dict[str, Any]
) -> list[dict[str, Any]]:
    normalized = normalize_candidates(candidates)
    filtered = _filter_and_dedupe(normalized, config.get("blocked_terms", []))
    scored = [_with_score(item, config) for item in filtered]
    scored.sort(key=lambda item: item["score"], reverse=True)

    selected: list[dict[str, Any]] = []
    categories = config.get("categories", {})
    for category, category_config in categories.items():
        quota = int(category_config.get("daily_limit", 0))
        pool = [item for item in scored if item["category"] == category]
        selected.extend(pool[:quota])

    return selected[: int(config.get("daily_limit", 10))]


def render_daily_markdown(
    news_date: str, items: list[dict[str, Any]], total_count: int
) -> str:
    lines = [
        f"# GitHub News - {news_date}",
        "",
        f"> 北京时间 {news_date}",
        "> Source: GitHub via gh CLI",
        f"> Count: {len(items)}/{total_count}",
        "",
    ]
    for index, item in enumerate(items, 1):
        headline = item.get("headline") or build_headline(item)
        lines.extend([f"{index}. {headline}", f"   {item['url']}", ""])
    return "\n".join(lines).rstrip() + "\n"


def write_daily_markdown(news_dir: Path | str, news_date: str, markdown: str) -> Path:
    base = Path(news_dir)
    year, month, _ = news_date.split("-")
    target = base / year / month / f"{news_date}.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(markdown, encoding="utf-8")
    return target


def update_index(news_dir: Path | str, news_date: str) -> None:
    base = Path(news_dir)
    index_path = base / "index.md"
    base.mkdir(parents=True, exist_ok=True)
    entries = _read_index_entries(index_path)
    year, month, _ = news_date.split("-")
    entries[news_date] = f"./{year}/{month}/{news_date}.md"

    lines = ["# GitHub News Index", ""]
    for date in sorted(entries.keys(), reverse=True):
        lines.append(f"- [{date}]({entries[date]})")
    index_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_headline(item: dict[str, Any]) -> str:
    repository = item.get("repository", "GitHub 项目")
    source = item.get("source", "repo")
    title = item.get("title") or item.get("description") or "出现新动态"
    if source == "release":
        return f"{repository} 发布新版本，{_trim_sentence(title)}。"
    if source == "pr":
        return f"{repository} 合并高关注变更，{_trim_sentence(title)}。"
    if source == "issue":
        return f"{repository} 出现高互动讨论，{_trim_sentence(title)}。"
    return f"{repository} 值得关注，{_trim_sentence(title)}。"


def _filter_and_dedupe(
    items: list[dict[str, Any]], blocked_terms: list[str]
) -> list[dict[str, Any]]:
    seen_urls: set[str] = set()
    seen_repos: set[str] = set()
    result = []
    for item in items:
        text = f"{item.get('title', '')} {item.get('description', '')}".lower()
        if any(term.lower() in text for term in blocked_terms):
            continue
        url = item["url"]
        repository = item["repository"]
        if url in seen_urls or repository in seen_repos:
            continue
        seen_urls.add(url)
        seen_repos.add(repository)
        result.append(item)
    return result


def _with_score(item: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    source_weights = config.get("source_weights", {})
    keywords = config.get("categories", {}).get(item["category"], {}).get("keywords", [])
    text = f"{item.get('title', '')} {item.get('description', '')}".lower()
    score = int(source_weights.get(item.get("source"), 10))
    score += _popularity_score(item.get("stars", 0))
    score += min(int(item.get("comments", 0)), 30) // 3
    score += sum(5 for keyword in keywords if keyword.lower() in text)
    enriched = dict(item)
    enriched["score"] = score
    enriched["headline"] = build_headline(enriched)
    return enriched


def _popularity_score(stars: int) -> int:
    if stars >= 10000:
        return 20
    if stars >= 2000:
        return 10
    if stars >= 500:
        return 5
    return 0


def _repo_from_url(url: str) -> str | None:
    parts = url.removeprefix("https://github.com/").split("/")
    if len(parts) >= 2:
        return f"{parts[0]}/{parts[1]}"
    return None


def _read_index_entries(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    entries: dict[str, str] = {}
    pattern = re.compile(r"^- \[(\d{4}-\d{2}-\d{2})\]\(([^)]+)\)")
    for line in path.read_text(encoding="utf-8").splitlines():
        match = pattern.match(line)
        if match:
            entries[match.group(1)] = match.group(2)
    return entries


def _trim_sentence(text: str) -> str:
    return text.strip().rstrip("。.!")[:80] or "出现新动态"


def _to_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0
