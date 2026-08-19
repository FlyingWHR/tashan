#!/usr/bin/env python3
"""Deploy the site — but only if the suite is green and the working tree is committed.

    python3 pipeline/deploy.py            # test, then deploy
    python3 pipeline/deploy.py --force    # deploy a red tree on purpose, and say so out loud

WHY THIS EXISTS. `.githooks/pre-commit` refuses a commit when the suite is red, and it works. Nothing
guarded the DEPLOY. On 19 Aug the hook correctly refused a commit, the very next line of the same
shell ran `wrangler pages deploy`, and a failing tree went to production anyway. The guard was on the
wrong verb: a commit that never lands is a private mistake, a deploy is the public one.

It also refuses to ship an UNCOMMITTED tree. A deploy nobody can reconstruct from git is a site whose
running state exists only on one laptop — and this project regenerates ~12,000 files per run, so
"just redeploy from main" silently ships something different if the tree was dirty.

The proxy dance is not decoration: wrangler routes through $HTTPS_PROXY when it is set and dies with
a bare `fetch failed` in ~400ms if that local proxy is down, which reads exactly like an auth error
and is not one. See CLAUDE.md.
"""
import os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROXY_VARS = ("HTTPS_PROXY", "HTTP_PROXY", "https_proxy", "http_proxy", "ALL_PROXY", "all_proxy")


def run(cmd, **kw):
    return subprocess.run(cmd, cwd=ROOT, **kw)


def main(argv):
    force = "--force" in argv

    dirty = run(["git", "status", "--porcelain"], capture_output=True, text=True).stdout.strip()
    if dirty and not force:
        print("deploy: REFUSED — the working tree is not committed.\n")
        print(dirty[:800])
        print("\n  Commit first. A deployed state that is not in git cannot be reproduced,")
        print("  and the pipeline rewrites ~12,000 files a run.")
        return 1

    if not force:
        print("deploy: running tests/run.sh first...")
        if run(["bash", "tests/run.sh"], capture_output=True).returncode != 0:
            print("deploy: REFUSED — the suite is red.\n")
            run(["bash", "tests/run.sh"])          # show it, do not make anyone re-run to find out
            print("\n  This is the check that was missing on 19 Aug, when a refused commit was")
            print("  followed by a deploy that went out anyway.")
            return 1
        print("deploy: suite green.\n")
    else:
        print("deploy: --force — skipping the suite and the clean-tree check. On your head.\n")

    env = {k: v for k, v in os.environ.items() if k not in PROXY_VARS}
    return run(["npx", "wrangler@3", "pages", "deploy", "web", "--project-name", "tashan"],
               env=env).returncode


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
