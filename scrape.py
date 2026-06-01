"""
IIT India Scraper — All 23 IITs
================================
Directly scrapes all IITs from a hardcoded list
(no pagination/URL pattern needed).

Requirements:
    pip install selenium webdriver-manager beautifulsoup4 pandas

Run:
    python iit_scraper.py
"""

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import pandas as pd
import re, time, random

# ── All 23 IITs with their Shiksha URLs ──
IITS = [
    ("IIT Bombay",          "https://www.shiksha.com/university/iit-bombay-mumbai-11085"),
    ("IIT Delhi",           "https://www.shiksha.com/university/iit-delhi-new-delhi-11086"),
    ("IIT Madras",          "https://www.shiksha.com/university/iit-madras-chennai-11088"),
    ("IIT Kanpur",          "https://www.shiksha.com/university/iit-kanpur-kanpur-11087"),
    ("IIT Kharagpur",       "https://www.shiksha.com/university/iit-kharagpur-kharagpur-11089"),
    ("IIT Roorkee",         "https://www.shiksha.com/university/iit-roorkee-roorkee-11090"),
    ("IIT Guwahati",        "https://www.shiksha.com/university/iit-guwahati-guwahati-11091"),
    ("IIT Hyderabad",       "https://www.shiksha.com/university/iit-hyderabad-hyderabad-21742"),
    ("IIT Gandhinagar",     "https://www.shiksha.com/university/iit-gandhinagar-gandhinagar-21740"),
    ("IIT Jodhpur",         "https://www.shiksha.com/university/iit-jodhpur-jodhpur-21743"),
    ("IIT Patna",           "https://www.shiksha.com/university/iit-patna-patna-21744"),
    ("IIT Ropar",           "https://www.shiksha.com/university/iit-ropar-rupnagar-21745"),
    ("IIT Bhubaneswar",     "https://www.shiksha.com/university/iit-bhubaneswar-bhubaneswar-21739"),
    ("IIT Mandi",           "https://www.shiksha.com/university/iit-mandi-mandi-21746"),
    ("IIT Varanasi (BHU)",  "https://www.shiksha.com/university/iit-bhu-varanasi-varanasi-11092"),
    ("IIT Indore",          "https://www.shiksha.com/university/iit-indore-indore-36517"),
    ("IIT Tirupati",        "https://www.shiksha.com/university/iit-tirupati-tirupati-79337"),
    ("IIT Palakkad",        "https://www.shiksha.com/university/iit-palakkad-palakkad-79338"),
    ("IIT Bhilai",          "https://www.shiksha.com/university/iit-bhilai-raipur-118775"),
    ("IIT Goa",             "https://www.shiksha.com/university/iit-goa-ponda-118776"),
    ("IIT Jammu",           "https://www.shiksha.com/university/iit-jammu-jammu-118777"),
    ("IIT Dharwad",         "https://www.shiksha.com/university/iit-dharwad-dharwad-118778"),
    ("IIT Chhattisgarh (ISM Dhanbad)", "https://www.shiksha.com/university/iit-ism-dhanbad-dhanbad-11093"),
]

# Region mapping
REGION = {
    "IIT Bombay":         "West",
    "IIT Delhi":          "North",
    "IIT Madras":         "South",
    "IIT Kanpur":         "North",
    "IIT Kharagpur":      "East",
    "IIT Roorkee":        "North",
    "IIT Guwahati":       "Northeast",
    "IIT Hyderabad":      "South",
    "IIT Gandhinagar":    "West",
    "IIT Jodhpur":        "North",
    "IIT Patna":          "East",
    "IIT Ropar":          "North",
    "IIT Bhubaneswar":    "East",
    "IIT Mandi":          "North",
    "IIT Varanasi (BHU)": "North",
    "IIT Indore":         "Central",
    "IIT Tirupati":       "South",
    "IIT Palakkad":       "South",
    "IIT Bhilai":         "Central",
    "IIT Goa":            "West",
    "IIT Jammu":          "North",
    "IIT Dharwad":        "South",
    "IIT Chhattisgarh (ISM Dhanbad)": "East",
}

STATE = {
    "IIT Bombay":         "Maharashtra",
    "IIT Delhi":          "Delhi",
    "IIT Madras":         "Tamil Nadu",
    "IIT Kanpur":         "Uttar Pradesh",
    "IIT Kharagpur":      "West Bengal",
    "IIT Roorkee":        "Uttarakhand",
    "IIT Guwahati":       "Assam",
    "IIT Hyderabad":      "Telangana",
    "IIT Gandhinagar":    "Gujarat",
    "IIT Jodhpur":        "Rajasthan",
    "IIT Patna":          "Bihar",
    "IIT Ropar":          "Punjab",
    "IIT Bhubaneswar":    "Odisha",
    "IIT Mandi":          "Himachal Pradesh",
    "IIT Varanasi (BHU)": "Uttar Pradesh",
    "IIT Indore":         "Madhya Pradesh",
    "IIT Tirupati":       "Andhra Pradesh",
    "IIT Palakkad":       "Kerala",
    "IIT Bhilai":         "Chhattisgarh",
    "IIT Goa":            "Goa",
    "IIT Jammu":          "Jammu and Kashmir",
    "IIT Dharwad":        "Karnataka",
    "IIT Chhattisgarh (ISM Dhanbad)": "Jharkhand",
}

CITY = {
    "IIT Bombay":         "Mumbai",
    "IIT Delhi":          "New Delhi",
    "IIT Madras":         "Chennai",
    "IIT Kanpur":         "Kanpur",
    "IIT Kharagpur":      "Kharagpur",
    "IIT Roorkee":        "Roorkee",
    "IIT Guwahati":       "Guwahati",
    "IIT Hyderabad":      "Hyderabad",
    "IIT Gandhinagar":    "Gandhinagar",
    "IIT Jodhpur":        "Jodhpur",
    "IIT Patna":          "Patna",
    "IIT Ropar":          "Rupnagar",
    "IIT Bhubaneswar":    "Bhubaneswar",
    "IIT Mandi":          "Mandi",
    "IIT Varanasi (BHU)": "Varanasi",
    "IIT Indore":         "Indore",
    "IIT Tirupati":       "Tirupati",
    "IIT Palakkad":       "Palakkad",
    "IIT Bhilai":         "Bhilai",
    "IIT Goa":            "Ponda",
    "IIT Jammu":          "Jammu",
    "IIT Dharwad":        "Dharwad",
    "IIT Chhattisgarh (ISM Dhanbad)": "Dhanbad",
}

DEGREES_LIST = [
    "B.Tech", "M.Tech", "Ph.D", "MBA", "M.Sc",
    "Dual Degree", "Integrated M.Tech", "B.Des", "M.Des",
]

STREAMS_LIST = [
    "Computer Science", "Information Technology",
    "Electronics and Communication", "Electrical Engineering",
    "Mechanical Engineering", "Civil Engineering",
    "Chemical Engineering", "Aerospace Engineering",
    "Biotechnology", "Data Science", "Artificial Intelligence",
    "Machine Learning", "Robotics", "Mathematics and Computing",
    "Engineering Physics", "Materials Science",
    "Naval Architecture", "Ocean Engineering",
    "Metallurgical Engineering", "Mining Engineering",
    "Industrial Engineering", "Environmental Engineering",
]

# ─────────────────────────────────────────────
# BROWSER
# ─────────────────────────────────────────────

def create_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    })
    return driver


def scroll_page(driver):
    for pos in range(0, 5000, 400):
        driver.execute_script(f"window.scrollTo(0, {pos});")
        time.sleep(0.15)
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(2)


def load_page(driver, url):
    driver.get(url)
    WebDriverWait(driver, 40).until(
        lambda d: d.execute_script("return document.readyState") == "complete"
    )
    time.sleep(5)
    scroll_page(driver)
    return driver.page_source


# ─────────────────────────────────────────────
# SCRAPE ONE IIT PAGE
# ─────────────────────────────────────────────

def scrape_iit(driver, short_name, url):
    print(f"  Scraping: {short_name} ... ", end="", flush=True)

    try:
        html = load_page(driver, url)
    except Exception as e:
        print(f"ERROR: {e}")
        return build_fallback(short_name, url)

    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True)

    c = {
        "name":            short_name,
        "region":          REGION.get(short_name, "N/A"),
        "city":            CITY.get(short_name, "N/A"),
        "state":           STATE.get(short_name, "N/A"),
        "type":            "IIT (Central Govt - Autonomous)",
        "established":     "N/A",
        "rating":          "N/A",
        "nirf_ranking":    "N/A",
        "fees_btech":      "N/A",
        "degrees_offered": "N/A",
        "streams_offered": "N/A",
        "website":         "N/A",
        "shiksha_url":     url,
    }

    # Full name from H1
    h1 = soup.find("h1")
    if h1:
        full = h1.get_text(strip=True)
        full = re.sub(r'\s*[-|]\s*(Overview|Shiksha|Courses|Fees|Ranking|Admission).*$',
                      '', full, flags=re.IGNORECASE)
        if len(full) > 3:
            c["name"] = full

    # Established year
    m = re.search(r'[Ee]stablished\s*(?:in)?\s*(19|20)\d{2}', text)
    if m:
        c["established"] = m.group(0)

    # Rating
    m = re.search(r'(\d\.\d)\s*/\s*(?:10|5)', text)
    if m:
        c["rating"] = m.group(0)

    # NIRF Ranking
    m = re.search(r'NIRF\s*(?:Rank(?:ing|ed)?)?\s*[:#]?\s*(\d+)', text, re.IGNORECASE)
    if m:
        c["nirf_ranking"] = "NIRF #" + m.group(1)
    else:
        m = re.search(r'(?:Rank(?:ed|ing)?|#)\s*(\d+)', text, re.IGNORECASE)
        if m:
            c["nirf_ranking"] = m.group(0)

    # Fees
    m = re.search(r'(?:₹|Rs\.?)\s*([\d,]+(?:\.\d+)?)\s*(Lakh|L\b|Crore|Cr\b|/-)?',
                  text, re.IGNORECASE)
    if m:
        c["fees_btech"] = m.group(0).strip()

    # Official website
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "iit" in href.lower() and "shiksha" not in href.lower() and href.startswith("http"):
            c["website"] = href
            break

    # Degrees
    found_deg = [d for d in DEGREES_LIST
                 if re.search(rf'\b{re.escape(d)}\b', text, re.IGNORECASE)]
    if found_deg:
        c["degrees_offered"] = " | ".join(found_deg)

    # Streams — search in courses section only
    course_area = ""
    for tag in soup.find_all(["table", "section", "div"]):
        chunk = tag.get_text(" ", strip=True)
        if any(k in chunk[:100].lower() for k in ["course", "program", "branch", "specializ"]):
            course_area += " " + chunk[:5000]
    if not course_area:
        course_area = text

    found_str = [s for s in STREAMS_LIST
                 if re.search(rf'\b{re.escape(s)}\b', course_area, re.IGNORECASE)]
    if found_str:
        c["streams_offered"] = " | ".join(found_str)

    print(f"✅  NIRF={c['nirf_ranking']} | {c['city']}, {c['state']}")
    return c


def build_fallback(short_name, url):
    return {
        "name": short_name, "region": REGION.get(short_name, "N/A"),
        "city": CITY.get(short_name, "N/A"), "state": STATE.get(short_name, "N/A"),
        "type": "IIT (Central Govt - Autonomous)", "established": "N/A",
        "rating": "N/A", "nirf_ranking": "N/A", "fees_btech": "N/A",
        "degrees_offered": "N/A", "streams_offered": "N/A",
        "website": "N/A", "shiksha_url": url,
    }


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def scrape_all_iits():
    print("=" * 60)
    print("  All IITs in India — Scraper")
    print(f"  Total IITs: {len(IITS)}")
    print("=" * 60)

    driver = create_driver()
    results = []

    try:
        for i, (name, url) in enumerate(IITS, 1):
            print(f"\n[{i:2d}/{len(IITS)}] ", end="")
            data = scrape_iit(driver, name, url)
            results.append(data)
            time.sleep(random.uniform(2, 3))
    finally:
        driver.quit()

    df = pd.DataFrame(results, columns=[
        "name", "region", "city", "state", "type",
        "established", "nirf_ranking", "rating", "fees_btech",
        "degrees_offered", "streams_offered", "website", "shiksha_url"
    ])

    # Sort by region then name
    region_order = {"North": 1, "South": 2, "East": 3, "West": 4,
                    "Central": 5, "Northeast": 6, "N/A": 7}
    df["_order"] = df["region"].map(region_order)
    df.sort_values(["_order", "name"], inplace=True)
    df.drop(columns=["_order"], inplace=True)
    df.reset_index(drop=True, inplace=True)

    out = "all_iits_india.csv"
    df.to_csv(out, index=False, encoding="utf-8-sig")

    print(f"\n{'='*60}")
    print(f"✅ Saved {len(df)} IITs → '{out}'")
    print(f"\nIITs by Region:")
    print(df.groupby("region")["name"].apply(list).to_string())
    print(f"\nFull Data Preview:")
    print(df[["name", "region", "state", "nirf_ranking", "fees_btech"]].to_string(index=False))


if __name__ == "__main__":
    scrape_all_iits()