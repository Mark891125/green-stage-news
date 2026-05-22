#!/usr/bin/env bash
set -euo pipefail

python3 -m scripts.github_news.collect "$@"
