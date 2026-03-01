#!/usr/bin/env python3
"""
PR Monitor - Waits for all requested reviewers to complete their reviews.

Exit codes:
  0 - All reviewers completed, new activity detected
  1 - Failed to fetch PR data
  2 - Timeout reached
"""

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime
from typing import Any, Dict, List, Tuple, Union


def run_gh_command(args: List[str]) -> Tuple[int, str, str]:
    """Run a gh command and return (exit_code, stdout, stderr)."""
    result = subprocess.run(
        ["gh"] + args,
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout, result.stderr


def get_pr_info(pr_url: str) -> Union[Dict[str, Any], None]:
    """Fetch PR information including reviews and review requests."""
    # Extract owner/repo/number from URL
    # URL format: https://github.com/owner/repo/pull/number
    parts = pr_url.rstrip("/").split("/")
    if len(parts) < 7:
        return None

    owner = parts[-4]
    repo = parts[-3]
    pr_number = parts[-1]

    # Get PR details
    exit_code, stdout, stderr = run_gh_command(
        [
            "pr",
            "view",
            pr_number,
            "--json",
            "url,number,state,reviewDecision,reviews,reviewRequests,latestReviews",
            "-R",
            f"{owner}/{repo}",
        ]
    )

    if exit_code != 0:
        print(f"Error fetching PR: {stderr}", file=sys.stderr)
        return None

    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        return None


def get_review_comments(pr_url: str) -> list[dict]:
    """Get all review comments on the PR."""
    parts = pr_url.rstrip("/").split("/")
    if len(parts) < 7:
        return []

    owner = parts[-4]
    repo = parts[-3]
    pr_number = parts[-1]

    exit_code, stdout, stderr = run_gh_command(
        ["api", f"repos/{owner}/{repo}/pulls/{pr_number}/comments"]
    )

    if exit_code != 0:
        return []

    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        return []


def check_all_reviewers_done(pr_info: dict) -> Tuple[bool, List[str]]:
    """Check if all requested reviewers have submitted their reviews.

    Returns:
        (all_done, pending_reviewers)
    """
    review_requests_raw = pr_info.get("reviewRequests", [])

    # Handle both list and dict with nodes format
    if isinstance(review_requests_raw, dict):
        review_requests = review_requests_raw.get("nodes", [])
    else:
        review_requests = review_requests_raw

    if not review_requests:
        # No specific reviewers requested - consider done
        return True, []

    requested_reviewers = set()
    for r in review_requests:
        # Handle different response formats
        if isinstance(r, dict):
            reviewer = r.get("requestedReviewer", {})
            if isinstance(reviewer, dict):
                login = reviewer.get("login")
            else:
                login = r.get("login")
            if login:
                requested_reviewers.add(login)

    # Get reviewers who have submitted
    latest_reviews = pr_info.get("latestReviews", [])
    submitted_reviewers = {r.get("author", {}).get("login") for r in latest_reviews}

    # Also check reviews array for any additional submissions
    all_reviews = pr_info.get("reviews", [])
    for r in all_reviews:
        submitted_reviewers.add(r.get("author", {}).get("login"))

    pending = requested_reviewers - submitted_reviewers

    return len(pending) == 0, list(pending)


def main():
    parser = argparse.ArgumentParser(description="Monitor PR for review activity")
    parser.add_argument("pr_url", help="URL of the PR to monitor")
    parser.add_argument(
        "--interval", type=int, default=15, help="Polling interval in seconds"
    )
    parser.add_argument(
        "--timeout", type=int, default=1200, help="Timeout in seconds (default: 20 min)"
    )
    args = parser.parse_args()

    start_time = time.time()
    last_comment_count = 0
    last_review_count = 0

    print(f"Monitoring PR: {args.pr_url}")
    print(f"Interval: {args.interval}s, Timeout: {args.timeout}s")
    print("-" * 50)

    while True:
        elapsed = time.time() - start_time
        if elapsed >= args.timeout:
            pr_info = get_pr_info(args.pr_url)
            all_done, pending = (
                check_all_reviewers_done(pr_info) if pr_info else (False, [])
            )
            result = {
                "status": "timeout",
                "elapsed_seconds": int(elapsed),
                "all_reviewers_done": all_done,
                "pending_reviewers": pending,
                "pr_url": args.pr_url,
            }
            print(json.dumps(result, indent=2))
            return 2

        pr_info = get_pr_info(args.pr_url)
        if not pr_info:
            print(f"[{datetime.now().isoformat()}] Error fetching PR data, retrying...")
            time.sleep(args.interval)
            continue

        comments = get_review_comments(args.pr_url)
        current_comment_count = len(comments)
        current_review_count = len(pr_info.get("reviews", []))

        all_done, pending = check_all_reviewers_done(pr_info)

        timestamp = datetime.now().strftime("%H:%M:%S")
        print(
            f"[{timestamp}] Reviews: {current_review_count}, Comments: {current_comment_count}, "
            f"All done: {all_done}, Pending: {pending if pending else 'none'}"
        )

        # Check for new activity
        has_new_activity = (
            current_comment_count > last_comment_count
            or current_review_count > last_review_count
        )

        if has_new_activity:
            last_comment_count = current_comment_count
            last_review_count = current_review_count

            if all_done:
                result = {
                    "status": "all_reviewers_done",
                    "elapsed_seconds": int(elapsed),
                    "all_reviewers_done": True,
                    "pending_reviewers": [],
                    "review_count": current_review_count,
                    "comment_count": current_comment_count,
                    "pr_url": args.pr_url,
                    "pr_info": pr_info,
                }
                print("-" * 50)
                print("All reviewers have completed their reviews!")
                print(json.dumps(result, indent=2))
                return 0
            else:
                print(
                    f"  -> New activity detected, waiting for pending reviewers: {pending}"
                )

        time.sleep(args.interval)


if __name__ == "__main__":
    main()

