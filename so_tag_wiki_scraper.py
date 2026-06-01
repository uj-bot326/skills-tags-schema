import requests
import json
import csv
import time
import os

API_KEY = "rl_RQqK6YPohTmeW59p8gat5jkH7"
BASE_URL = "https://api.stackexchange.com/2.3"
SITE = "stackoverflow"

SCRIPT_DIR      = os.path.dirname(os.path.abspath(__file__))
OUTPUT_JSON     = os.path.join(SCRIPT_DIR, "so_tag_wikis.json")
OUTPUT_CSV      = os.path.join(SCRIPT_DIR, "so_tag_wikis.csv")
PROGRESS_FILE   = os.path.join(SCRIPT_DIR, "so_tags_progress.json")
WIKIS_FILE      = os.path.join(SCRIPT_DIR, "so_wikis_progress.json")
SYNONYMS_FILE   = os.path.join(SCRIPT_DIR, "so_synonyms_progress.json")


def fetch_with_retry(url, params, retries=6):
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(url, params=params, timeout=30)
            if not resp.text.strip():
                wait = attempt * 10
                print(f"  [Empty response - throttled] Waiting {wait}s...")
                time.sleep(wait)
                continue
            data = resp.json()
            if "backoff" in data:
                backoff = int(data["backoff"])
                print(f"  [Backoff] API asked to wait {backoff}s...")
                time.sleep(backoff + 1)
            return data
        except requests.exceptions.JSONDecodeError:
            wait = attempt * 10
            print(f"  [Bad response] Waiting {wait}s before retry {attempt}/{retries}...")
            time.sleep(wait)
        except Exception as e:
            wait = attempt * 5
            print(f"  [Connection error] {e}")
            print(f"  Retrying in {wait}s... (attempt {attempt}/{retries})")
            time.sleep(wait)
    print("  Failed after all retries. Skipping.")
    return None


def get_all_tags(api_key):
    tags = []
    start_page = 1

    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, "r") as f:
            progress = json.load(f)
            tags = progress.get("tags", [])
            start_page = progress.get("next_page", 1)
        print(f"Resuming tag fetch from page {start_page} ({len(tags)} tags already saved)...")
    else:
        print("Fetching tag list from page 1...")

    page = start_page
    while True:
        params = {
            "page": page, "pagesize": 100,
            "order": "desc", "sort": "popular",
            "site": SITE, "key": api_key,
        }
        data = fetch_with_retry(f"{BASE_URL}/tags", params)
        if data is None:
            page += 1
            continue

        if "error_id" in data:
            print(f"  API error: {data.get('error_message')}")
            time.sleep(10)
            page += 1
            continue

        batch = [item["name"] for item in data.get("items", [])]
        tags.extend(batch)
        quota = data.get("quota_remaining", "?")
        print(f"  Page {page} — {len(batch)} tags — quota remaining: {quota}")

        with open(PROGRESS_FILE, "w") as f:
            json.dump({"tags": tags, "next_page": page + 1}, f)

        if not data.get("has_more", False):
            print("All tag pages fetched!")
            break

        page += 1
        time.sleep(0.5)

        if isinstance(quota, int) and quota < 50:
            print("Quota almost exhausted — stopping.")
            break

    print(f"Total tags: {len(tags)}")
    return tags


def get_tag_wikis(tag_names, api_key):
    wikis = []
    batch_size = 20
    total = len(tag_names)
    start_index = 0

    if os.path.exists(WIKIS_FILE):
        with open(WIKIS_FILE, "r") as f:
            wp = json.load(f)
            wikis = wp.get("wikis", [])
            start_index = wp.get("next_index", 0)
        print(f"Resuming wiki fetch from index {start_index} ({len(wikis)} wikis already saved)...")
    else:
        print(f"\nFetching wikis for {total} tags...")

    for i in range(start_index, total, batch_size):
        batch = tag_names[i:i + batch_size]
        tags_param = ";".join(batch)
        params = {"site": SITE, "key": api_key}

        data = fetch_with_retry(f"{BASE_URL}/tags/{tags_param}/wikis", params)
        if data is None:
            continue

        if "error_id" in data:
            print(f"  API error on batch: {data.get('error_message')}")
            time.sleep(5)
            continue

        for item in data.get("items", []):
            wikis.append({
                "tag_name":               item.get("tag_name", ""),
                "excerpt":                item.get("excerpt", ""),
                "body":                   item.get("body", ""),
                "excerpt_last_edit_date": item.get("excerpt_last_edit_date", ""),
                "body_last_edit_date":    item.get("body_last_edit_date", ""),
            })

        quota = data.get("quota_remaining", "?")
        done = min(i + batch_size, total)
        print(f"  [{done}/{total}] wikis — quota: {quota}")

        with open(WIKIS_FILE, "w") as f:
            json.dump({"wikis": wikis, "next_index": i + batch_size}, f)

        time.sleep(0.5)

        if isinstance(quota, int) and quota < 50:
            print("Quota almost exhausted — stopping.")
            break

    print(f"Total wikis fetched: {len(wikis)}")
    return wikis


def get_tag_synonyms(tag_names, api_key):
    """Fetch synonyms for all tags in batches of 20."""
    synonyms_map = {}  # tag_name -> comma-separated synonyms
    batch_size = 20
    total = len(tag_names)
    start_index = 0

    if os.path.exists(SYNONYMS_FILE):
        with open(SYNONYMS_FILE, "r") as f:
            sp = json.load(f)
            synonyms_map = sp.get("synonyms_map", {})
            start_index = sp.get("next_index", 0)
        print(f"Resuming synonym fetch from index {start_index} ({len(synonyms_map)} tags with synonyms so far)...")
    else:
        print(f"\nFetching synonyms for {total} tags...")

    for i in range(start_index, total, batch_size):
        batch = tag_names[i:i + batch_size]
        tags_param = ";".join(batch)
        params = {"site": SITE, "key": api_key}

        data = fetch_with_retry(f"{BASE_URL}/tags/{tags_param}/synonyms", params)
        if data is None:
            continue

        if "error_id" in data:
            print(f"  API error on synonyms batch: {data.get('error_message')}")
            time.sleep(5)
            continue

        for item in data.get("items", []):
            to_tag = item.get("to_tag", "")
            from_tag = item.get("from_tag", "")
            if to_tag and from_tag:
                if to_tag not in synonyms_map:
                    synonyms_map[to_tag] = []
                synonyms_map[to_tag].append(from_tag)

        quota = data.get("quota_remaining", "?")
        done = min(i + batch_size, total)
        print(f"  [{done}/{total}] synonyms — quota: {quota}")

        with open(SYNONYMS_FILE, "w") as f:
            json.dump({"synonyms_map": synonyms_map, "next_index": i + batch_size}, f)

        time.sleep(0.5)

        if isinstance(quota, int) and quota < 50:
            print("Quota almost exhausted — stopping.")
            break

    # Convert lists to comma-separated strings
    result = {k: ", ".join(v) for k, v in synonyms_map.items()}
    print(f"Tags with synonyms found: {len(result)}")
    return result


def save_json(data, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Saved JSON -> {path}")


def save_csv(wikis, synonyms_map, path):
    if not wikis:
        print("No wiki data to save.")
        return
    fieldnames = ["tag_name", "synonyms", "excerpt", "body",
                  "excerpt_last_edit_date", "body_last_edit_date"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in wikis:
            row["synonyms"] = synonyms_map.get(row["tag_name"], "")
            writer.writerow(row)
    print(f"Saved CSV  -> {path}")


def main():
    print("=" * 50)
    print("  Stack Overflow Tag Wiki Scraper v5")
    print("  (with Synonyms)")
    print("=" * 50)
    print(f"Files will be saved to: {SCRIPT_DIR}\n")

    # Step 1: Get all tag names
    tag_names = get_all_tags(API_KEY)
    if not tag_names:
        print("No tags found.")
        return

    # Step 2: Fetch wikis
    wikis = get_tag_wikis(tag_names, API_KEY)

    # Step 3: Fetch synonyms
    synonyms_map = get_tag_synonyms(tag_names, API_KEY)

    # Step 4: Save
    print("\nSaving results...")
    combined = []
    for w in wikis:
        w["synonyms"] = synonyms_map.get(w["tag_name"], "")
        combined.append(w)
    save_json(combined, OUTPUT_JSON)
    save_csv(wikis, synonyms_map, OUTPUT_CSV)

    # Clean up progress files
    for fp in [PROGRESS_FILE, WIKIS_FILE, SYNONYMS_FILE]:
        if os.path.exists(fp):
            os.remove(fp)

    print("\nDone! Files saved:")
    print(f"  {OUTPUT_JSON}")
    print(f"  {OUTPUT_CSV}")
    print("\nCSV columns: tag_name | synonyms | excerpt | body | excerpt_last_edit_date | body_last_edit_date")


if __name__ == "__main__":
    main()