# green-stage-news

Generate a daily Markdown digest of GitHub news.

The first version collects candidates with `gh`, selects 10 short Chinese news
items, and writes the result by Beijing date:

- 8 AI / LLM / Agent / developer-tool items
- 2 full-stack items
- original GitHub URLs only
- raw collection data stays under `.local/` and is ignored by git

## Local run

```bash
GH_TOKEN=... bash scripts/github_news/collect.sh 2026-05-22
python3 -m scripts.github_news.select 2026-05-22
python3 -m scripts.github_news.render 2026-05-22
```

Output files:

- `news/YYYY/MM/YYYY-MM-DD.md`
- `news/index.md`

Intermediate files:

- `.local/github-news/raw/YYYY-MM-DD.jsonl`
- `.local/github-news/selected/YYYY-MM-DD.json`
