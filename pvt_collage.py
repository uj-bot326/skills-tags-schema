import asyncio
import pandas as pd
from playwright.async_api import async_playwright


async def scrape_colleges(url: str) -> list[dict]:
    """
    Scrape college data from CollegeDunia using Playwright.
    Handles JS-rendered content, lazy loading, and infinite scroll.
    """

    colleges = []

    async with async_playwright() as p:

        # ── Launch Browser ────────────────────────────────────────────────────
        browser = await p.chromium.launch(
            headless=True,  # Set False to see browser in action
            args=["--no-sandbox", "--disable-setuid-sandbox"]
        )

        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
            locale="en-US",
        )

        page = await context.new_page()

        # Block unnecessary resources to speed up scraping
        await page.route("**/*.{png,jpg,jpeg,gif,svg,woff,woff2,ttf,mp4,webp}",
                         lambda route: route.abort())

        # ── Navigate to Page ──────────────────────────────────────────────────
        print(f"[INFO] Navigating to: {url}")
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)

        # Wait for college cards to load
        await page.wait_for_selector("tr.table-row", timeout=15000)
        print("[INFO] Page loaded successfully.")

        # ── Auto Scroll to Load All Colleges ─────────────────────────────────
        print("[INFO] Scrolling to load all content...")
        previous_count = 0
        scroll_attempts = 0

        while scroll_attempts < 10:
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(2)

            current_count = await page.locator("tr.table-row").count()
            print(f"[INFO] Colleges loaded so far: {current_count}")

            if current_count == previous_count:
                scroll_attempts += 1
            else:
                scroll_attempts = 0
                previous_count = current_count

        print(f"[INFO] Total college rows found: {current_count}")

        # ── Extract Data ──────────────────────────────────────────────────────
        rows = page.locator("tr.table-row")
        total = await rows.count()

        for i in range(total):
            row = rows.nth(i)
            data = {}

            try:
                # CD Rank
                data["CD Rank"] = await get_text(row, "td.font-weight-medium.text-lg.position-relative")

                # College Name
                data["College Name"] = await get_text(row, "h3.font-weight-medium.text-lg.mb-0")

                # Location
                data["Location"] = await get_text(row, "span.location")

                # Approvals
                data["Approvals"] = await get_text(row, "span.approvals")

                # NAAC Grade
                data["NAAC Grade"] = await get_text(row, "span.naac-grade")

                # CD Score
                data["CD Score"] = await get_text(row, "span.font-weight-bold.mr-1")

                # Course
                data["Course"] = await get_text(row, "span.fee-shorm-form")

                # Course Fees
                data["Course Fees"] = await get_text(row, "span.text-lg.text-green.d-block.font-weight-bold.mb-1")

                # Placements
                placement_links = row.locator("a.jsx-914129990.d-block.underline-on-hover")
                placement_count = await placement_links.count()

                if placement_count >= 1:
                    avg_tag = placement_links.nth(0).locator("span.text-green")
                    data["Avg Package"] = await avg_tag.inner_text() if await avg_tag.count() > 0 else "N/A"
                else:
                    data["Avg Package"] = "N/A"

                if placement_count >= 2:
                    high_tag = placement_links.nth(1).locator("span.text-green")
                    data["Highest Package"] = await high_tag.inner_text() if await high_tag.count() > 0 else "N/A"
                else:
                    data["Highest Package"] = "N/A"

                # User Rating
                data["User Rating"] = await get_text(row, "span.lr-key")

                # Reviews
                data["Reviews"] = await get_text(row, "span.lr-value")

                # Best In
                taglines = row.locator("span.placement-reviews-back span:not(.icon)")
                tag_count = await taglines.count()
                texts = []
                for t in range(tag_count):
                    txt = (await taglines.nth(t).inner_text()).strip()
                    if txt:
                        texts.append(txt)
                data["Best In"] = texts[0] if texts else "N/A"

                # National Ranking
                data["National Ranking"] = await get_text(row, "span.rank-span")

                colleges.append(data)
                print(f"  ✅ [{i+1}/{total}] {data['College Name']}")

            except Exception as e:
                print(f"  ⚠️  [{i+1}/{total}] Error parsing row: {e}")
                continue

        await browser.close()

    return colleges


async def get_text(locator, selector: str) -> str:
    """Helper to safely get inner text from a selector."""
    try:
        el = locator.locator(selector).first
        if await el.count() > 0:
            return (await el.inner_text()).strip().replace("\n", " ")
        return "N/A"
    except Exception:
        return "N/A"


def save_to_csv(colleges: list[dict], filename: str = "colleges.csv"):
    """Save scraped data to CSV."""
    if not colleges:
        print("[WARNING] No data to save.")
        return None

    df = pd.DataFrame(colleges)
    df.to_csv(filename, index=False, encoding="utf-8-sig")
    print(f"\n✅ Data saved to '{filename}'")
    return df


def display_results(colleges: list[dict]):
    """Pretty print results to console."""
    if not colleges:
        print("[WARNING] No colleges found.")
        return

    print(f"\n{'='*65}")
    print(f"  🎓 Found {len(colleges)} College(s)")
    print(f"{'='*65}")

    for c in colleges:
        print(f"\n  {c.get('CD Rank', 'N/A')}  {c.get('College Name', 'N/A')}")
        print(f"     📍 Location       : {c.get('Location', 'N/A')}")
        print(f"     🏛  NAAC Grade     : {c.get('NAAC Grade', 'N/A')}")
        print(f"     🎓 Course         : {c.get('Course', 'N/A')}")
        print(f"     💰 Fees           : {c.get('Course Fees', 'N/A')}")
        print(f"     📦 Avg Package    : {c.get('Avg Package', 'N/A')}")
        print(f"     🚀 Highest Pkg    : {c.get('Highest Package', 'N/A')}")
        print(f"     ⭐ Rating         : {c.get('User Rating', 'N/A')}")
        print(f"     🏆 Ranking        : {c.get('National Ranking', 'N/A')}")
        print(f"     ✅ Best In        : {c.get('Best In', 'N/A')}")
        print(f"     📊 CD Score       : {c.get('CD Score', 'N/A')}")

    print(f"\n{'='*65}")


# ── MAIN ──────────────────────────────────────────────────────────────────────
async def main():
    TARGET_URL = "https://collegedunia.com/btech/private-colleges"

    print("🚀 Starting Playwright College Scraper...")
    colleges = await scrape_colleges(TARGET_URL)

    display_results(colleges)
    df = save_to_csv(colleges, "colleges.csv")

    if df is not None:
        print(f"\n📋 Preview (first 5 rows):\n")
        print(df.head().to_string(index=False))


if __name__ == "__main__":
    asyncio.run(main())