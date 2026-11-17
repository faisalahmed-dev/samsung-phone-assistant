"""Parse a GSMArena phone page into a dictionary of specs."""

import re

from bs4 import BeautifulSoup


def clean_text(text):
    """Tidy the " | " separators that replace <br> tags.

    Removes repeated, leading and trailing separators, and keeps benchmark
    versions attached to their scores, e.g. "1696727 | (v10)" -> "1696727 (v10)".
    """
    text = re.sub(r"(\s*\|\s*)+", " | ", text)
    text = text.replace(" | (", " (")
    text = text.replace(": | ", ": ")
    return text.strip(" |")


def get_by_data_spec(soup, spec_name):
    """Return the text of the element with the given data-spec attribute, or None."""
    tag = soup.find(attrs={"data-spec": spec_name})
    return clean_text(tag.get_text(" ", strip=True)) if tag else None


def read_spec_tables(soup):
    """Read all spec tables into {category: {spec_name: value}}."""
    all_specs = {}
    specs_list = soup.find("div", id="specs-list")
    if specs_list is None:
        return all_specs

    for table in specs_list.find_all("table"):
        header = table.find("th")
        if header is None:
            continue

        category = header.get_text(strip=True)
        all_specs[category] = {}
        last_key = None

        for row in table.find_all("tr"):
            title_cell = row.find("td", class_="ttl")
            value_cell = row.find("td", class_="nfo")
            if value_cell is None:
                continue

            key = title_cell.get_text(strip=True) if title_cell else ""
            value = clean_text(value_cell.get_text(" ", strip=True))

            # A row without a title continues the previous row.
            if key == "" and last_key:
                all_specs[category][last_key] += " | " + value
            else:
                key = key or "Info"
                all_specs[category][key] = value
                last_key = key

    return all_specs


def parse_phone(html, url):
    """Return the name, image, key specs and full specs of one phone page."""
    soup = BeautifulSoup(html, "html.parser")

    # Cells with several values (e.g. multiple cameras) separate them with <br>.
    for line_break in soup.find_all("br"):
        line_break.replace_with(" | ")

    name_tag = soup.find("h1", class_="specs-phone-name-title")
    image_tag = soup.select_one("div.specs-photo-main img")
    all_specs = read_spec_tables(soup)

    # GSMArena's two battery tests use different methods and are not comparable,
    # so they are stored separately.
    tests = all_specs.get("Our Tests", {})

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
        "battery_active_use": tests.get("Battery") or tests.get("Battery (new)"),
        "battery_endurance": tests.get("Battery (old)"),
        "price": get_by_data_spec(soup, "price"),
    }

    return {
        "name": name_tag.get_text(strip=True) if name_tag else "Unknown",
        "url": url,
        "image_url": image_tag["src"] if image_tag else None,
        "key_specs": key_specs,
        "all_specs": all_specs,
    }