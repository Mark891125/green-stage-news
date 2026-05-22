# GitHub News Initialization Plan

## Scope

The project is not a web site. The first version collects GitHub signals with
the `gh` CLI and generates one Markdown digest per Beijing calendar date.

Daily output contains 10 short Chinese news items:

- 8 AI / LLM / Agent / developer-tool items
- 2 full-stack items
- each item is a one-sentence summary plus the original GitHub URL

## Repository Outputs

Files committed to the repository:

- `news/YYYY/MM/YYYY-MM-DD.md`
- `news/index.md`
- collection, selection, and rendering scripts
- configuration and GitHub Actions workflow

Files not committed to the repository:

- raw collection data under `.local/github-news/raw/`
- selected intermediate data under `.local/github-news/selected/`

## Pipeline

1. `collect`: call `gh search repos`, `gh search prs`, and `gh search issues`
   according to configured source pools; by default use the previous Beijing
   date as the search lower bound so the 08:00 run covers a full prior-day
   window; write raw JSONL data locally.
2. `select`: normalize candidates, filter low-value items, dedupe by URL and
   repository, score by source, popularity, comments, and keywords, then select
   8 AI items and 2 full-stack items.
3. `render`: write the daily Markdown file and update `news/index.md`.

All date arguments use `YYYY-MM-DD` and are interpreted as Beijing dates. The
first version intentionally collects repositories, pull requests, and issues
only; release-specific scoring is not enabled until release collection is added.

## Automation

GitHub Actions runs at 08:00 Beijing time and also supports manual
`workflow_dispatch`. The workflow creates a `daily-news/YYYY-MM-DD` branch and
opens a pull request for review instead of pushing directly to `main`.
If selection returns zero items, the workflow exits without rendering Markdown
or opening a pull request.

Required workflow permissions:

- `contents: write`
- `pull-requests: write`

## Validation

Before merging pipeline changes:

- run unit tests with `python3 -m unittest tests/test_news_pipeline.py`
- compile scripts with `python3 -m compileall scripts tests`
- validate JSON config with `python3 -m json.tool config/github-news.json`
- run a fixture dry run to confirm 10 items are selected with an 8/2 split
- verify `.local/` data is ignored by git
