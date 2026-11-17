"""
spec_parser.py

The "reading" part of the scraper.
It takes the HTML of one phone page and pulls out the specs with BeautifulSoup.
It never uses the internet, so it's easy to test on the saved pages.
"""

import re

from bs4 import BeautifulSoup


def clean_text(text):
    """
    Tidy up the " | " separators we add for <br> line breaks.
      "UFS 3.1 |"               -> "UFS 3.1"            (pipe at the end)
      "(v10) | | GeekBench"     -> "(v10) | GeekBench"  (two pipes in a row)
      "1696727 | (v10)"         -> "1696727 (v10)"      (keep the version next to its score)
      "Cover camera: | 10 MP"   -> "Cover camera: 10 MP"
    """
    text = re.sub(r"(\s*\|\s*)+", " | ", text)   # many pipes in a row -> just one
    text = text.replace(" | (", " (")             # "(v10)" stays with its number
    text = text.replace(": | ", ": ")             # nothing between ":" and its value
    return text.strip(" |")                       # remove pipes at the start or end


def get_by_data_spec(soup, spec_name):
    """
    Many values on GSMArena have a 'data-spec' label, for example:
        <td class="nfo" data-spec="displaysize">6.1 inches</td>
    This finds the value by its label. Returns None if it's not on the page.
    """
    tag = soup.find(attrs={"data-spec": spec_name})
    return clean_text(tag.get_text(" ", strip=True)) if tag else None


def read_spec_tables(soup):
    """
    Read every spec table on the page.
    Result looks like: {"Display": {"Type": "...", "Size": "..."}, "Battery": {...}}
    """
    all_specs = {}
    specs_list = soup.find("div", id="specs-list")
    if specs_list is None:
        return all_specs

    for table in specs_list.find_all("table"):
        header = table.find("th")
        if header is None:
            continue

        category = header.get_text(strip=True)   # e.g. "Display"
        all_specs[category] = {}
        last_key = None

        for row in table.find_all("tr"):
            title_cell = row.find("td", class_="ttl")
            value_cell = row.find("td", class_="nfo")
            if value_cell is None:
                continue

            key = title_cell.get_text(strip=True) if title_cell else ""
            value = clean_text(value_cell.get_text(" ", strip=True))

            # Some rows have no title. That means the value belongs
            # to the row above it, so we join them together.
            if key == "" and last_key:
                all_specs[category][last_key] += " | " + value
            else:
                key = key or "Info"
                all_specs[category][key] = value
                last_key = key

    return all_specs


def parse_phone(html, url):
    """Read one phone page and return all its data as a dictionary."""
    soup = BeautifulSoup(html, "html.parser")

    # In GSMArena's HTML, values inside one cell (like 3 cameras) are separated
    # by <br> line breaks. We turn each <br> into " | " so the values don't stick together.
    for line_break in soup.find_all("br"):
        line_break.replace_with(" | ")

    # Phone name, e.g. "Samsung Galaxy S23"
    name_tag = soup.find("h1", class_="specs-phone-name-title")
    name = name_tag.get_text(strip=True) if name_tag else "Unknown"

    # Phone picture
    image_tag = soup.select_one("div.specs-photo-main img")
    image_url = image_tag["src"] if image_tag else None

    all_specs = read_spec_tables(soup)

    # GSMArena runs 2 different battery tests. They can't be compared with each other,
    # so we keep them separately.
    tests = all_specs.get("Our Tests", {})
    battery_active_use = tests.get("Battery") or tests.get("Battery (new)")   # e.g. "Active use score 11:27h"
    battery_endurance = tests.get("Battery (old)")                           # e.g. "Endurance rating 93h"

    # The most important specs, kept separately so they're easy to use later
    key_specs = {
        "announced": get_by_data_spec(soup, "year"),
        "status": get_by_data_spec(soup, "status"),
        "dimensions": get_by_data_spec(soup, "dimensions"),
        "weight": get_by_data_spec(soup, "weight"),
        "display_type": get_by_data_spec(soup, "displaytype"),
        "display_size": get_by_data_spec(soup, "displaysize"),
        "display_resolution": get_by_data_spec(soup, "displayresolution"),
        "os": get_by_data_spec(soup, "os"),
        "chipset": get_by_data_spec(soup, "chipset"),
        "cpu": get_by_data_spec(soup, "cpu"),
        "gpu": get_by_data_spec(soup, "gpu"),
        "memory": get_by_data_spec(soup, "internalmemory"),
        "main_camera": get_by_data_spec(soup, "cam1modules"),
        "selfie_camera": get_by_data_spec(soup, "cam2modules"),
        "battery": get_by_data_spec(soup, "batdescription1"),
        "battery_active_use": battery_active_use,
        "battery_endurance": battery_endurance,
        "price": get_by_data_spec(soup, "price"),
    }

    return {
        "name": name,
        "url": url,
        "image_url": image_url,
        "key_specs": key_specs,
        "all_specs": all_specs,
    }