"""
fetch_tag_counts.py
-------------------
Fetches the question count for every tag in so_tags_enriched_final.json
using the Stack Exchange API /2.3/tags/{tags}/info endpoint.

Usage:
    python fetch_tag_counts.py \
        --input  so_tags_enriched_final.json \
        --output tag_counts.json \
        [--key YOUR_API_KEY]        # optional but raises quota from 300 to 10000/day

Requirements:  requests  (pip install requests)

Notes:
  - 100 tags per request (API max)
  - 49,979 tags → ~500 API calls
  - Without a key: 300 requests/day quota  →  run in 2 days, or get a key
  - With a free key from https://stackapps.com/apps/oauth/register : 10,000/day
  - Progress is saved after every batch so you can resume safely
  - Final output: list of {name, count, so_count} objects merged back to original
"""

import argparse
import json
import math
import time
import os
import sys

try:
    import requests
except ImportError:
    sys.exit("Install requests first:  pip install requests")

ENDPOINT = "https://api.stackexchange.com/2.3/tags/{tags}/info"
BATCH    = 100          # API maximum
SITE     = "stackoverflow"
SLEEP    = 0.5          # seconds between calls (be polite)


def chunks(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


def fetch_batch(tag_names, api_key=None):
    tags_str = ";".join(tag_names)
    params = {
        "order":    "desc",
        "sort":     "popular",
        "site":     SITE,
        "filter":   "default",
        "pagesize": BATCH,
    }
    if api_key:
        params["key"] = api_key

    url = ENDPOINT.format(tags=tags_str)
    resp = requests.get(url, params=params, timeout=15)

    if resp.status_code == 400:
        # Some tags may contain invalid chars — skip this batch
        print(f"  [WARN] 400 Bad Request, skipping batch starting with {tag_names[0]!r}")
        return {}, None

    resp.raise_for_status()
    data = resp.json()
    quota = data.get("quota_remaining")
    counts = {item["name"]: item["count"] for item in data.get("items", [])}
    return counts, quota


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input",  default="so_tags_enriched_final.json")
    ap.add_argument("--output", default="tag_counts.json")
    ap.add_argument("--key",    default="rl_X5fv8sDj3yycLGzJgCwvR58y8", help="Stack Exchange API key")
    args = ap.parse_args()

    # ── Load tags ──────────────────────────────────────────────────────────
    print(f"Loading {args.input} …")
    with open(args.input, encoding="utf-8") as f:
        data = json.load(f)
    all_names = [item["name"] for item in data]
    print(f"  {len(all_names):,} tags found")

    # ── Resume support ─────────────────────────────────────────────────────
    progress_file = args.output + ".progress"
    counts_map = {}
    start_batch = 0

    if os.path.exists(progress_file):
        with open(progress_file, encoding="utf-8") as f:
            saved = json.load(f)
        counts_map  = saved["counts_map"]
        start_batch = saved["next_batch"]
        print(f"  Resuming from batch {start_batch}")

    batches    = list(chunks(all_names, BATCH))
    total      = len(batches)
    quota_left = "?"

    # ── Fetch ──────────────────────────────────────────────────────────────
    for i, batch in enumerate(batches):
        if i < start_batch:
            continue

        print(f"  Batch {i+1}/{total}  (quota remaining: {quota_left}) …", end=" ", flush=True)
        try:
            result, quota_left = fetch_batch(batch, args.key)
            counts_map.update(result)
            print(f"{len(result)} returned")
        except requests.HTTPError as e:
            if e.response.status_code == 429:
                print("Rate limited — sleeping 60 s …")
                time.sleep(60)
                result, quota_left = fetch_batch(batch, args.key)
                counts_map.update(result)
            else:
                raise

        # Save progress after every batch
        with open(progress_file, "w", encoding="utf-8") as f:
            json.dump({"counts_map": counts_map, "next_batch": i + 1}, f)

        if quota_left is not None and int(quota_left) < 5:
            print("Quota nearly exhausted — stopping. Re-run tomorrow or add an API key.")
            break

        time.sleep(SLEEP)

    # ── Merge back ─────────────────────────────────────────────────────────
    print(f"\nMerging counts into {args.output} …")
    for item in data:
        item["so_count"] = counts_map.get(item["name"])   # None if tag not found on SO

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    found    = sum(1 for item in data if item["so_count"] is not None)
    not_found = len(data) - found
    print(f"Done. {found:,} tags got a count, {not_found:,} had no match on SO.")
    print(f"Output saved to: {args.output}")

    # Clean up progress file on success
    if os.path.exists(progress_file):
        os.remove(progress_file)


if __name__ == "__main__":
    main()