"""
Run this FIRST to find the correct selector.
    python debug_selector.py
"""
import undetected_chromedriver as uc
import time

opts = uc.ChromeOptions()
opts.add_argument("--window-size=1400,900")
driver = uc.Chrome(options=opts, version_main=148, use_subprocess=True)

print("Opening Stack Overflow tags page...")
driver.get("https://stackoverflow.com/tags?page=1&tab=popular")
print("Waiting 8 seconds for page to fully load...")
time.sleep(8)

print("\n" + "="*60)
print("PAGE TITLE:", driver.title)
print("="*60)

# Print ALL anchor tags that have /tags/ in href
all_links = driver.find_elements("tag name", "a")
print(f"\nTotal <a> tags on page: {len(all_links)}")
print("\nAnchor tags containing '/tags/' in href:")
print("-"*60)

count = 0
for a in all_links:
    try:
        href = a.get_attribute("href") or ""
        cls  = a.get_attribute("class") or ""
        text = a.text.strip()
        if "/tags/" in href and text and len(text) < 60:
            print(f"  text='{text}'  |  class='{cls}'  |  href='{href}'")
            count += 1
            if count >= 50:
                print("  ... (showing first 50 only)")
                break
    except Exception:
        pass

if count == 0:
    print("  NO anchor tags with /tags/ found!")
    print("\n  Printing ALL anchor tags instead:")
    for a in all_links[:30]:
        try:
            href = a.get_attribute("href") or ""
            cls  = a.get_attribute("class") or ""
            text = a.text.strip()
            print(f"  text='{text[:40]}'  class='{cls}'  href='{href[:60]}'")
        except Exception:
            pass

# Also print a snippet of page source
print("\n" + "="*60)
print("FIRST 3000 CHARS OF PAGE SOURCE:")
print("="*60)
src = driver.page_source
print(src[:3000])

input("\nPress ENTER to close Chrome...")
driver.quit()