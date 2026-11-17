"""Download GSMArena phone pages, keeping a local copy of each page in html_pages/."""

import os
import random
import time

import requests

BASE_URL = "https://www.gsmarena.com/"
HTML_FOLDER = "html_pages"

# A normal browser User-Agent; many sites block the default one sent by requests.
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}


def get_html(page_name):
    """Return the HTML of a phone page, or None if it could not be fetched.

    A saved copy is used when available, so each page is downloaded only once.
    """
    local_file = os.path.join(HTML_FOLDER, page_name.replace(".php", ".html"))

    if os.path.exists(local_file):
        print(f"  Using saved copy: {local_file}")
        with open(local_file, encoding="utf-8") as f:
            return f.read()

    url = BASE_URL + page_name
    try:
        response = requests.get(url, headers=HEADERS, timeout=20)
    except requests.exceptions.RequestException as error:
        print(f"  Network error: {error}")
        return None

    # Every real phone page contains "specs-list". Without it,
    # GSMArena most likely returned a bot-check page instead.
    if response.status_code == 200 and "specs-list" in response.text:
        os.makedirs(HTML_FOLDER, exist_ok=True)
        with open(local_file, "w", encoding="utf-8") as f:
            f.write(response.text)
        time.sleep(random.uniform(3, 6))  # avoid overloading the server
        return response.text

    print(f"  Blocked (status {response.status_code}). Save the page manually as {local_file}:")
    print(f"  {url}")
    return None