
import requests
import json
import csv
import time
import os

API_KEY = "rl_RQqK6YPohTmeW59p8gat5jkH7"
BASE_URL = "https://api.stackexchange.com/2.3"
SITE = "stackoverflow"

# Save all files in the same folder as this script
SCRIPT_DIR    = os.path.dirname(os.path.abspath(__file__))
OUTPUT_JSON   = os.path.join(SCRIPT_DIR, "so_tag_wikis.json")
OUTPUT_CSV    = os.path.join(SCRIPT_DIR, "so_tag_wikis.csv")
PROGRESS_FILE = os.path.join(SCRIPT_DIR, "so_tags_progress.json")


def fetch_with_retry(url, params, retries=5):
    """GET request with automatic retry on connection errors."""
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(url, params=params, timeout=30)
            return resp
        except Exception as e:
            wait = attempt * 5
            print(f"  [Connection error] {e}")
            print(f"  Retrying in {wait}s... (attempt {attempt}/{retries})")
            time.sleep(wait)
    print("  Failed after all retries. Skipping this request.")
    return None


def get_all_tags(api_key):
    """Fetch all tag names, resuming from saved progress if available."""
    tags = []
    start_page = 1

    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, "r") as f:
            progress = json.load(f)
            tags = progress.get("tags", [])
            start_page = progress.get("next_page", 1)
        print(f"Resuming from page {start_page} ({len(tags)} tags already saved)...")
    else:
        print("Fetching tag list from page 1...")

    page = start_page

    while True:
        url = f"{BASE_URL}/tags"
        params = {
            "page": page,
            "pagesize": 100,
            "order": "desc",
            "sort": "popular",
            "site": SITE,
            "key": api_key,
        }

        resp = fetch_with_retry(url, params)
        if resp is None:
            print(f"  Skipping page {page} after failed retries.")
            page += 1
            continue

        data = resp.json()

        if "error_id" in data:
            print(f"API error: {data['error_message']}")
            break

        batch = [item["name"] for item in data.get("items", [])]
        tags.extend(batch)

        quota = data.get("quota_remaining", "?")
        print(f"  Page {page} — {len(batch)} tags — quota remaining: {quota}")

        # Save progress after every page
        with open(PROGRESS_FILE, "w") as f:
            json.dump({"tags": tags, "next_page": page + 1}, f)

        if not data.get("has_more", False):
            print("All tag pages fetched!")
            break

        page += 1
        time.sleep(0.2)

        if isinstance(quota, int) and quota < 50:
            print("Quota almost exhausted — stopping tag fetch.")
            break

    print(f"Total tags fetched: {len(tags)}")
    return tags


def get_tag_wikis(tag_names, api_key):
    """Fetch wiki excerpt + body for tags in batches of 20."""
    wikis = []
    batch_size = 20
    total = len(tag_names)

    print(f"\nFetching wikis for {total} tags...")

    for i in range(0, total, batch_size):
        batch = tag_names[i:i + batch_size]
        tags_param = ";".join(batch)

        url = f"{BASE_URL}/tags/{tags_param}/wikis"
        params = {
            "site": SITE,
            "key": api_key,
        }

        resp = fetch_with_retry(url, params)
        if resp is None:
            print(f"  Skipping batch at index {i} after failed retries.")
            continue

        data = resp.json()

        if "error_id" in data:
            print(f"  API error on batch: {data['error_message']}")
            time.sleep(5)
            continue

        items = data.get("items", [])
        for item in items:
            wikis.append({
                "tag_name":               item.get("tag_name", ""),
                "excerpt":                item.get("excerpt", ""),
                "body":                   item.get("body", ""),
                "excerpt_last_edit_date": item.get("excerpt_last_edit_date", ""),
                "body_last_edit_date":    item.get("body_last_edit_date", ""),
            })

        quota = data.get("quota_remaining", "?")
        done = min(i + batch_size, total)
        print(f"  [{done}/{total}] batch done — quota remaining: {quota}")

        time.sleep(0.2)

        if isinstance(quota, int) and quota < 50:
            print("Quota almost exhausted — stopping wiki fetch.")
            break

    print(f"Total wikis fetched: {len(wikis)}")
    return wikis


def save_json(wikis, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(wikis, f, ensure_ascii=False, indent=2)
    print(f"Saved JSON -> {path}")


def save_csv(wikis, path):
    if not wikis:
        print("No wiki data to save.")
        return
    fieldnames = ["tag_name", "excerpt", "body", "excerpt_last_edit_date", "body_last_edit_date"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(wikis)
    print(f"Saved CSV  -> {path}")


def main():
    print("=" * 50)
    print("  Stack Overflow Tag Wiki Scraper v3")
    print("=" * 50)
    print(f"Files will be saved to: {SCRIPT_DIR}\n")

    tag_names = get_all_tags(API_KEY)

    if not tag_names:
        print("No tags found. Check your API key and internet connection.")
        return

    wikis = get_tag_wikis(tag_names, API_KEY)

    print("\nSaving results...")
    save_json(wikis, OUTPUT_JSON)
    save_csv(wikis, OUTPUT_CSV)

    if os.path.exists(PROGRESS_FILE):
        os.remove(PROGRESS_FILE)
        print("Progress file cleaned up.")

    print("\nDone! Files saved:")
    print(f"  {OUTPUT_JSON}")
    print(f"  {OUTPUT_CSV}")


if __name__ == "__main__":
    main()