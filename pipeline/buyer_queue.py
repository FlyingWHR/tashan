"""Prioritise paid-kit gaps using the published snapshot and aggregate task-specific requests."""
import json
import os
import subprocess
from pathlib import Path

import funnel

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "data/raw/kit-priority.json"


def priority(axis):
    if not PLAN.exists():
        return {}
    rows = json.loads(PLAN.read_text())[axis]
    return {cid: i for i, cid in enumerate(rows)}


def select(rows, axis, limit):
    """Use four slots for buyer work and one for discovery. Preserve demand order within discovery."""
    ranks = priority(axis)
    focused = sorted((r for r in rows if r[0] in ranks), key=lambda r: ranks[r[0]])
    broad = (r for r in rows if r[0] not in ranks)
    focus = iter(focused)
    result = []
    for i in range(min(len(rows), limit)):
        first, second = (broad, focus) if i % 5 == 4 else (focus, broad)
        row = next(first, None)
        if row is None:
            row = next(second, None)
        if row is None:
            break
        result.append(row)
    return result


def main():
    interest = {}
    measured = False
    if funnel.ACCOUNT and funnel.TOKEN:
        try:
            for r in funnel.kit_interest(30):
                interest.setdefault(r["task"], {})[r["stage"]] = int(r["c"])
            measured = True
        except (RuntimeError, ValueError, OSError):
            print("Task-level sales analytics unavailable. Using measured kit coverage.")
    raw = subprocess.check_output(["node", str(ROOT / "pipeline/kit_queue.mjs")],
                                  input=json.dumps(interest), text=True, cwd=ROOT)
    plan = json.loads(raw)
    PLAN.parent.mkdir(parents=True, exist_ok=True)
    temp = PLAN.with_suffix(".tmp")
    temp.write_text(raw)
    temp.replace(PLAN)
    line = (f"Snapshot {plan['generated_at']}: {plan['available']}/{plan['mapped']} mapped jobs "
            f"can return a pinned kit, {plan['one_pin']} have one verified pick. "
            f"{len(plan['expertise'])} shortlisted pins lack a documentation grade. "
            f"{len(plan['tasks'])} ranked, installable packages have no published task. "
            + (f"{len(interest)} tasks had a recorded buying signal in the last 30 days."
               if measured else "Task-level buying signals were unavailable for this run."))
    print(line)
    if os.getenv("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as f:
            print("\n### Paid kit coverage\n\n" + line, file=f)


if __name__ == "__main__":
    main()
