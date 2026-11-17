"""
fetcher.py

The "download" part of the scraper.
It gets the HTML of a GSMArena page and keeps a copy in the html_pages folder,
so the same page is never downloaded twice.
"""

import os
import random
import time

import requests

BASE_URL = "https://www.gsmarena.com/"

# Pretend to be a normal browser. Without this, many websites block the request.
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

HTML_FOLDER = "html_pages"


def get_html(page_name):
    """
    Get the HTML of one phone page.
      - If we already saved this page before, read it from html_pages/
      - If not, download it from GSMArena and save a copy
    Returns the HTML text, or None if it didn't work.
    """
    local_file = os.path.join(HTML_FOLDER, page_name.replace(".php", ".html"))

    # 1) Already have a saved copy? Use it.
    if os.path.exists(local_file):
        print(f"   📁 Using saved copy: {local_file}")
        with open(local_file, encoding="utf-8") as f:
            return f.read()

    # 2) Otherwise download it
    url = BASE_URL + page_name
    try:
        response = requests.get(url, headers=HEADERS, timeout=20)
    except requests.exceptions.RequestException as error:
        print(f"   ❌ Network problem: {error}")
        return None

    # A real phone page always has "specs-list" in it.
    # If it's missing, GSMArena probably showed us a check page instead.
    if response.status_code == 200 and "specs-list" in response.text:
        os.makedirs(HTML_FOLDER, exist_ok=True)
        with open(local_file, "w", encoding="utf-8") as f:
            f.write(response.text)

        # Wait 3-6 seconds before the next download, so we don't overload the website
        time.sleep(random.uniform(3, 6))
        return response.text

    print(f"   ⚠️ Blocked (status code {response.status_code}).")
    print(f"      Open this link in your browser and save it as: {local_file}")
    print(f"      {url}")
    return None