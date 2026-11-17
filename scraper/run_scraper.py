"""
run_scraper.py

Step 1: Collect Samsung phone specs from GSMArena.

This is the main file. It uses the other two:
  - fetcher.py      -> gets the HTML of each page
  - spec_parser.py  -> reads the specs out of the HTML
and saves everything into data/phones.json

Run it from the project folder:
    python -m scraper.run_scraper
"""

import json
import os

from scraper.fetcher import BASE_URL, get_html
from scraper.spec_parser import parse_phone

# The 15 phones we want. These are the last part of each phone's GSMArena link.
PHONE_PAGES = [
    "samsung_galaxy_s21_5g-10626.php",
    "samsung_galaxy_s21_ultra_5g-10596.php",
    "samsung_galaxy_s22_5g-11253.php",
    "samsung_galaxy_s22_ultra_5g-11251.php",
    "samsung_galaxy_s23-12082.php",
    "samsung_galaxy_s23_ultra-12024.php",
    "samsung_galaxy_s23_fe-12520.php",
    "samsung_galaxy_s24-12773.php",
    "samsung_galaxy_s24_ultra-12771.php",
    "samsung_galaxy_s25-13610.php",
    "samsung_galaxy_s25_ultra-13322.php",
    "samsung_galaxy_a54-12070.php",
    "samsung_galaxy_a55-12824.php",
    "samsung_galaxy_z_fold5-12418.php",
    "samsung_galaxy_z_flip5-12252.php",
]

OUTPUT_FILE = os.path.join("data", "phones.json")


def main():
    phones = []
    failed = []

    for number, page_name in enumerate(PHONE_PAGES, start=1):
        print(f"[{number}/{len(PHONE_PAGES)}] {page_name}")

        html = get_html(page_name)
        if html is None:
            failed.append(page_name)
            continue

        phone = parse_phone(html, BASE_URL + page_name)
        phones.append(phone)
        print(f"   ✅ {phone['name']} ({len(phone['all_specs'])} spec categories)")

    # Save everything into one JSON file
    os.makedirs("data", exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(phones, f, indent=2, ensure_ascii=False)

    print(f"\n🎉 Saved {len(phones)} phones to {OUTPUT_FILE}")
    if failed:
        print(f"⚠️ {len(failed)} pages failed. Save them manually and run the script again:")
        for page in failed:
            print("   -", page)


if __name__ == "__main__":
    main()