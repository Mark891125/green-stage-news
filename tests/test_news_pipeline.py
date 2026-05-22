import json
import tempfile
import unittest
from pathlib import Path

from scripts.github_news.news_pipeline import (
    choose_news_date,
    load_config,
    render_daily_markdown,
    select_top_items,
    update_index,
)


class NewsPipelineTests(unittest.TestCase):
    def test_choose_news_date_uses_beijing_timezone(self):
        self.assertEqual(
            choose_news_date(None, now_utc="2026-05-21T16:30:00Z"),
            "2026-05-22",
        )

    def test_select_top_items_keeps_eight_ai_and_two_fullstack(self):
        config = {
            "daily_limit": 10,
            "categories": {
                "ai": {"daily_limit": 8, "keywords": ["ai", "llm"]},
                "fullstack": {"daily_limit": 2, "keywords": ["react", "postgres"]},
            },
            "blocked_terms": [],
        }
        candidates = []
        for index in range(10):
            candidates.append(
                {
                    "category": "ai",
                    "title": f"AI project {index}",
                    "url": f"https://github.com/example/ai-{index}",
                    "repository": f"example/ai-{index}",
                    "description": "AI developer tooling",
                    "stars": 1000 - index,
                    "source": "repo",
                    "published_at": "2026-05-22T01:00:00Z",
                }
            )
        for index in range(4):
            candidates.append(
                {
                    "category": "fullstack",
                    "title": f"React project {index}",
                    "url": f"https://github.com/example/web-{index}",
                    "repository": f"example/web-{index}",
                    "description": "React and Postgres toolkit",
                    "stars": 500 - index,
                    "source": "repo",
                    "published_at": "2026-05-22T01:00:00Z",
                }
            )

        selected = select_top_items(candidates, config)

        self.assertEqual(len(selected), 10)
        self.assertEqual(
            [item["category"] for item in selected].count("ai"),
            8,
        )
        self.assertEqual(
            [item["category"] for item in selected].count("fullstack"),
            2,
        )

    def test_render_daily_markdown_writes_chinese_summary_and_original_urls(self):
        items = [
            {
                "category": "ai",
                "headline": "example/ai 发布新版本，聚焦 Agent 工具链。",
                "url": "https://github.com/example/ai/releases/tag/v1",
            }
        ]

        markdown = render_daily_markdown("2026-05-22", items, total_count=10)

        self.assertIn("# GitHub News - 2026-05-22", markdown)
        self.assertIn("北京时间 2026-05-22", markdown)
        self.assertIn("Count: 1/10", markdown)
        self.assertIn("1. example/ai 发布新版本，聚焦 Agent 工具链。", markdown)
        self.assertIn("https://github.com/example/ai/releases/tag/v1", markdown)

    def test_update_index_links_newest_daily_file_first(self):
        with tempfile.TemporaryDirectory() as tmp:
            news_dir = Path(tmp)
            update_index(news_dir, "2026-05-21")
            update_index(news_dir, "2026-05-22")

            index = (news_dir / "index.md").read_text(encoding="utf-8")

        self.assertIn("- [2026-05-22](./2026/05/2026-05-22.md)", index)
        self.assertLess(index.index("2026-05-22"), index.index("2026-05-21"))

    def test_load_config_reads_json_without_external_dependencies(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "github-news.json"
            path.write_text(json.dumps({"daily_limit": 10}), encoding="utf-8")

            self.assertEqual(load_config(path)["daily_limit"], 10)


if __name__ == "__main__":
    unittest.main()
