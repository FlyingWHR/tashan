#!/usr/bin/env bash
set -euo pipefail
files=$(find web -type f | wc -l)
if (( files >= 20000 )); then
  echo "::error::The snapshot has $files files and exceeds the Pages deployment threshold."
  exit 1
fi
npx --yes wrangler@3 pages deploy web --project-name tashan --branch main --commit-dirty=true
python3 pipeline/check_publication.py
