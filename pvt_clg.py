import asyncio
import pandas as pd
import os
from datetime import datetime
from playwright.async_api import async_playwright


# ── CONFIG ────────────────────────────────────────────────────────────────────
BATCH_SIZE    = 20          # Save every N colleges
OUTPUT_FILE   = "colleges.csv"
BATCH_DIR     = "batches"   # Folder for individual batch files
MAX_SCROLLS   = 20
SCROLL_DELAY  = 2           # seconds between scrolls


# ── HELPERS ───────────────────────────────────────────────────────────────────
async def get_text(locator, selector: str) -> str:
    """Safely extract inner text from a locator."""
    try:
        el = locator.locator(selector).first
        if await el.count() > 0:
            return (await el.inner_text()).strip().replace("\n", " ")
        return "N/A"
    except Exception:
        return "N/A"


def ensure_dirs():
    """Create output directories if they don't exist."""
    os.makedirs(BATCH_DIR, exist_ok=True)


def save_batch(batch: list[dict], batch_number: int) -> str:
    """
    Save a single batch to its own CSV file.
    Returns the file path.
    """
    filename = os.path.join(BATCH_DIR, f"batch_{batch_number:03d}.csv")
    df = pd.DataFrame(batch)
    df.to_csv(filename, index=False, encoding="utf-8-sig")
    print(f"\n  💾 Batch {batch_number} saved → {filename} ({len(batch)} records)")
    return filename


def merge_all_batches(batch_dir: str, output_file: str) -> pd.DataFrame | None:
    """
    Merge all batch CSV files into one final CSV.
    Removes duplicates based on College Name.
    """
    batch_files = sorted([
        os.path.join(batch_dir, f)
        for f in os.listdir(batch_dir)
        if f.endswith(".csv")
    ])

    if not batch_files:
        print("[WARNING] No batch files found to merge.")
        return None

    print(f"\n[INFO] Merging {len(batch_files)} batch file(s)...")
    dfs = [pd.read_csv(f) for f in batch_files]
    merged_df = pd.concat(dfs, ignore_index=True)
    merged_df.drop_duplicates(subset=["College Name"], inplace=True)
    merged_df.reset_index(drop=True, inplace=True)
    merged_df.to_csv(output_file, index=False, encoding="utf-8-sig")

    print(f"  ✅ Final merged file saved → {output_file}")
    print(f"  📊 Total unique colleges   : {len(merged_df)}")
    return merged_df


def save_progress_log(log: list[dict], filename: str = "progress_log.csv"):
    """Save a log of all batch operations with timestamps."""
    df = pd.DataFrame(log)
    df.to_csv(filename, index=False, encoding="utf-8-sig")
    print(f"  📋 Progress log saved      → {filename}")


# ── SCRAPER ───────────────────────────────────────────────────────────────────
async def scrape_colleges(url: str) -> list[dict]:
    """
    Scrape colleges with batch-wise saving.
    Every BATCH_SIZE records are saved immediately to disk.
    """

    ensure_dirs()
    all_colleges  = []
    current_batch = []
    batch_number  = 1
    progress_log  = []

    async with async_playwright() as p:

        # ── Launch Browser ────────────────────────────────────────────────────
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox"]
        )

        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1920, "height": 1080},
            locale="en-US",
        )

        page = await context.new_page()

        # Block images/fonts/media to speed up
        await page.route(
            "**/*.{png,jpg,jpeg,gif,svg,woff,woff2,ttf,mp4,webp}",
            lambda route: route.abort()
        )

        # ── Navigate ──────────────────────────────────────────────────────────
        print(f"\n🚀 Navigating to: {url}\n{'─'*60}")
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_selector("tr.table-row", timeout=15000)
        print("[INFO] Page loaded. Starting scroll to load all colleges...")

        # ── Auto-Scroll ───────────────────────────────────────────────────────
        previous_count = 0
        no_change_streak = 0

        while no_change_streak < MAX_SCROLLS:
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(SCROLL_DELAY)

            current_count = await page.locator("tr.table-row").count()
            print(f"  ↕  Scrolling... colleges visible: {current_count}")

            if current_count == previous_count:
                no_change_streak += 1
            else:
                no_change_streak = 0
                previous_count = current_count

        print(f"\n[INFO] Scroll complete. Total rows found: {current_count}\n{'─'*60}")

        # ── Parse Each Row ────────────────────────────────────────────────────
        rows  = page.locator("tr.table-row")
        total = await rows.count()

        for i in range(total):
            row  = rows.nth(i)
            data = {}

            try:
                # Basic Info
                data["CD Rank"]      = await get_text(row, "td.font-weight-medium.text-lg.position-relative")
                data["College Name"] = await get_text(row, "h3.font-weight-medium.text-lg.mb-0")
                data["Location"]     = await get_text(row, "span.location")
                data["Approvals"]    = await get_text(row, "span.approvals")
                data["NAAC Grade"]   = await get_text(row, "span.naac-grade")
                data["CD Score"]     = await get_text(row, "span.font-weight-bold.mr-1")

                # Course & Fees
                data["Course"]       = await get_text(row, "span.fee-shorm-form")
                data["Course Fees"]  = await get_text(row, "span.text-lg.text-green.d-block.font-weight-bold.mb-1")

                # Placements
                placement_links = row.locator("a.jsx-914129990.d-block.underline-on-hover")
                count = await placement_links.count()

                if count >= 1:
                    avg = placement_links.nth(0).locator("span.text-green")
                    data["Avg Package"] = (
                        await avg.inner_text() if await avg.count() > 0 else "N/A"
                    )
                else:
                    data["Avg Package"] = "N/A"

                if count >= 2:
                    high = placement_links.nth(1).locator("span.text-green")
                    data["Highest Package"] = (
                        await high.inner_text() if await high.count() > 0 else "N/A"
                    )
                else:
                    data["Highest Package"] = "N/A"

                # Reviews
                data["User Rating"] = await get_text(row, "span.lr-key")
                data["Reviews"]     = await get_text(row, "span.lr-value")

                # Best In
                taglines    = row.locator("span.placement-reviews-back span:not(.icon)")
                tag_count   = await taglines.count()
                texts       = []
                for t in range(tag_count):
                    txt = (await taglines.nth(t).inner_text()).strip()
                    if txt:
                        texts.append(txt)
                data["Best In"] = texts[0] if texts else "N/A"

                # Ranking
                data["National Ranking"] = await get_text(row, "span.rank-span")

                # Timestamp
                data["Scraped At"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                # ── Batch Logic ───────────────────────────────────────────────
                current_batch.append(data)
                all_colleges.append(data)

                print(f"  ✅ [{i+1:>4}/{total}] {data['College Name'][:55]:<55} "
                      f"| Batch {batch_number} ({len(current_batch)}/{BATCH_SIZE})")

                # Save batch when it reaches BATCH_SIZE
                if len(current_batch) >= BATCH_SIZE:
                    batch_file = save_batch(current_batch, batch_number)
                    progress_log.append({
                        "Batch Number"  : batch_number,
                        "Records"       : len(current_batch),
                        "File"          : batch_file,
                        "Saved At"      : datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "Status"        : "saved"
                    })
                    current_batch = []
                    batch_number += 1

            except Exception as e:
                print(f"  ⚠️  [{i+1:>4}/{total}] Error: {e}")
                continue

        # ── Save Remaining Records (last partial batch) ───────────────────────
        if current_batch:
            batch_file = save_batch(current_batch, batch_number)
            progress_log.append({
                "Batch Number"  : batch_number,
                "Records"       : len(current_batch),
                "File"          : batch_file,
                "Saved At"      : datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Status"        : "saved (final partial batch)"
            })

        await browser.close()

    # ── Post Processing ───────────────────────────────────────────────────────
    print(f"\n{'─'*60}")
    print(f"[INFO] Scraping complete. Total colleges scraped: {len(all_colleges)}")
    save_progress_log(progress_log)

    return all_colleges


# ── DISPLAY ───────────────────────────────────────────────────────────────────
def display_results(colleges: list[dict]):
    if not colleges:
        print("[WARNING] No colleges found.")
        return

    print(f"\n{'='*65}")
    print(f"  🎓 Total Colleges Scraped: {len(colleges)}")
    print(f"{'='*65}")

    for c in colleges:
        print(f"\n  {c.get('CD Rank','N/A')}  {c.get('College Name','N/A')}")
        print(f"     📍 Location       : {c.get('Location','N/A')}")
        print(f"     🏛  NAAC Grade     : {c.get('NAAC Grade','N/A')}")
        print(f"     🎓 Course         : {c.get('Course','N/A')}")
        print(f"     💰 Fees           : {c.get('Course Fees','N/A')}")
        print(f"     📦 Avg Package    : {c.get('Avg Package','N/A')}")
        print(f"     🚀 Highest Pkg    : {c.get('Highest Package','N/A')}")
        print(f"     ⭐ Rating         : {c.get('User Rating','N/A')}")
        print(f"     🏆 Ranking        : {c.get('National Ranking','N/A')}")
        print(f"     ✅ Best In        : {c.get('Best In','N/A')}")
        print(f"     📊 CD Score       : {c.get('CD Score','N/A')}")

    print(f"\n{'='*65}")


# ── MAIN ──────────────────────────────────────────────────────────────────────
async def main():
    TARGET_URL = "https://collegedunia.com/btech/private-colleges"

    print("="*65)
    print("   🏫  CollegeDunia Playwright Scraper — Batch Mode")
    print(f"   📦  Batch Size : {BATCH_SIZE} colleges per file")
    print(f"   📁  Batch Dir  : {BATCH_DIR}/")
    print(f"   📄  Final File : {OUTPUT_FILE}")
    print("="*65)

    colleges = await scrape_colleges(TARGET_URL)

    # Merge all batches into final CSV
    final_df = merge_all_batches(BATCH_DIR, OUTPUT_FILE)

    display_results(colleges)

    if final_df is not None:
        print(f"\n📋 Final Data Preview (first 5 rows):\n")
        print(final_df.head().to_string(index=False))


if __name__ == "__main__":
    asyncio.run(main())
    