#!/usr/bin/env python3
"""Re-export web/data/*.json from the database. No network.

WHY THIS EXISTS AS ITS OWN STAGE. The export is phase E of build.py, and build.py is a `source`
stage — so `run.py --site` skipped it and every site generator downstream read whatever
capabilities.json happened to be on disk. That is a silent staleness bug, not a theoretical one: on
9 Aug 2026 the task tagger was fixed to stop trusting stuffed npm keywords, `--site` was run, the
hubs regenerated from the OLD export, and /task/audio-production deployed still led by a Solana
transaction tool. Nothing failed; the numbers just did not move.

The export needs no network — it reads the DB and writes JSON — so there is no reason for it to sit
behind the source phase. It runs first in `site`, and the generators after it are now guaranteed to
be reading the database, not a snapshot of whenever build.py last finished.
"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build


def main():
    con = build.db()
    build.export(con)
    con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
