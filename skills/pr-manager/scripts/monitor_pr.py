#!/usr/bin/env python3
"""Monitor a GitHub PR for review activity.

Polls the PR every --interval seconds (default 15) until new review activity
is detected AND all requested reviewers have submitted, or --timeout is reached.

Exit codes:
  0 - All reviewers done, new activity detected
  1 - Failed to fetch PR data
  2 - Timeout reached
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from typing import Any, List, Optional, Tuple


def run_gh(args):
    # type: (List[str]) -> Optional[Any]
    try:
        result = subprocess.run(
            ["gh"] + args,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            print("gh error: {}".format(result.stderr.strip()), file=sys.stderr)
            return None
        return json.loads(result.stdout) if result.stdout.strip() else None
    except (subprocess.TimeoutExpired, json.JSONDecodeError) as e:
        print("Error running gh: {}".format(e), file=sys.stderr)
        return None


def get_reviews(owner, repo, pr_number):
    # type: (str, str, int) -> Optional[List[Any]]
    return run_gh([
        "api", "repos/{}/{}/pulls/{}/reviews".format(owner, repo, pr_number),
        "--paginate",
    ])


def get_review_comments(owner, repo, pr_number):
    # type: (str, str, int) -> Optional[List[Any]]
    return run_gh([
        "api", "repos/{}/{}/pulls/{}/comments".format(owner, repo, pr_number),
        "--paginate",
    ])


def parse_pr_url(url):
    # type: (str) -> Tuple[str, str, int]
    parts = url.rstrip("/").split("/")
    return parts[-4], parts[-3], int(parts[-1])


def main():
    parser = argparse.ArgumentParser(description="Monitor PR for reviews")
    parser.add_argument("pr_url", help="Full GitHub PR URL")
    parser.add_argument("--interval", type=int, default=15, help="Poll interval in seconds")
    parser.add_argument("--timeout", type=int, default=1200, help="Timeout in seconds")
    args = parser.parse_args()

    owner, repo, pr_number = parse_pr_url(args.pr_url)
    start_time = time.time()

    # Get initial state
    initial_reviews = get_reviews(owner, repo, pr_number) or []
    initial_comments = get_review_comments(owner, repo, pr_number) or []
    initial_review_count = len(initial_reviews)
    initial_comment_count = len(initial_comments)

    print("Monitoring PR #{} ({}/{})".format(pr_number, owner, repo))
    print("Initial state: {} reviews, {} comments".format(initial_review_count, initial_comment_count))
    print("Polling every {}s, timeout {}s".format(args.interval, args.timeout))

    while True:
        elapsed = time.time() - start_time
        if elapsed >= args.timeout:
            output = {
                "status": "timeout",
                "elapsed_seconds": int(elapsed),
                "all_reviewers_done": False,
            }
            print(json.dumps(output))
            sys.exit(2)

        time.sleep(args.interval)

        # Check for new activity
        reviews = get_reviews(owner, repo, pr_number) or []
        comments = get_review_comments(owner, repo, pr_number) or []

        new_reviews = len(reviews) > initial_review_count
        new_comments = len(comments) > initial_comment_count

        if not new_reviews and not new_comments:
            remaining = int(args.timeout - elapsed)
            print("  No new activity ({}s remaining)...".format(remaining), flush=True)
            continue

        # New activity detected - check if all reviewers are done
        pr_data = run_gh([
            "pr", "view", str(pr_number),
            "--repo", "{}/{}".format(owner, repo),
            "--json", "reviewRequests,reviews,url",
        ])

        pending_reviewers = []
        if pr_data and "reviewRequests" in pr_data:
            pending_reviewers = [
                r.get("login", r.get("name", "unknown"))
                for r in pr_data["reviewRequests"]
            ]

        all_done = len(pending_reviewers) == 0

        if not all_done:
            print("  New activity but waiting on: {}".format(", ".join(pending_reviewers)), flush=True)
            continue

        # All reviewers done
        output = {
            "status": "reviews_complete",
            "total_reviews": len(reviews),
            "total_comments": len(comments),
            "new_reviews": len(reviews) - initial_review_count,
            "new_comments": len(comments) - initial_comment_count,
            "all_reviewers_done": True,
            "reviews": [
                {
                    "id": r["id"],
                    "user": r["user"]["login"],
                    "state": r["state"],
                    "body": r.get("body", ""),
                }
                for r in reviews
            ],
            "comments": [
                {
                    "id": c["id"],
                    "user": c["user"]["login"],
                    "path": c.get("path", ""),
                    "body": c.get("body", ""),
                    "line": c.get("line"),
                }
                for c in comments
            ],
        }
        print(json.dumps(output, indent=2))
        sys.exit(0)


if __name__ == "__main__":
    main()
