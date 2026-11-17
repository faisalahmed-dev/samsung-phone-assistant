"""
load_data.py

Reads data/phones.json (from Step 1) and saves everything into MySQL.

Steps:
  1. Create the tables (from schema.sql)
  2. For every phone:
       - pull clean numbers out of the text (like 4000 from "Li-Ion 4000 mAh")
       - save the phone in the "phones" table
       - save every spec in the "specifications" table
       - split the price text into currencies, check them, and save them in "prices"

Run it from the project folder:
    python -m database.load_data
"""

import json
import os
import re
from datetime import date

from database.db import get_connection

SCHEMA_FILE = os.path.join(os.path.dirname(__file__), "schema.sql")
JSON_FILE = os.path.join("data", "phones.json")


# ---------------------------------------------------------------
# Cleaning helpers
# GSMArena gives us text. These small functions take out just the number.
# If they can't find it, they return None, which becomes NULL in MySQL.
# ---------------------------------------------------------------

def parse_year(text):
    # "2021, January 14" -> 2021
    match = re.search(r"(20\d{2})", text or "")
    return int(match.group(1)) if match else None


def parse_display_size(text):
    # "6.2 inches, 94.1 cm 2 (...)" -> 6.2
    match = re.search(r"([\d.]+)\s*inches", text or "")
    return float(match.group(1)) if match else None


def parse_battery_mah(text):
    # "Li-Ion 4000 mAh" -> 4000
    match = re.search(r"(\d+)\s*mAh", text or "")
    return int(match.group(1)) if match else None


def parse_weight(text):
    # "169 g (Sub6), 171 g (mmWave) (5.96 oz)" -> 169.0 (we take the first number)
    match = re.search(r"([\d.]+)\s*g\b", text or "")
    return float(match.group(1)) if match else None


def parse_max_ram(text):
    # "128GB 6GB RAM, 128GB 8GB RAM, 256GB 8GB RAM" -> 8 (the biggest option)
    numbers = re.findall(r"(\d+)\s*GB RAM", text or "")
    return max(int(n) for n in numbers) if numbers else None


def parse_main_camera_mp(text):
    # GSMArena always lists the main (wide) camera first, so we take the FIRST number.
    # "12 MP (wide) ... | 64 MP (telephoto) ... | 12 MP (ultrawide)" -> 12
    # We don't take the biggest number: on the S21 the biggest one (64 MP)
    # is the telephoto camera, not the main camera.
    match = re.search(r"(\d+)\s*MP", text or "")
    return int(match.group(1)) if match else None


def parse_charging_watt(all_specs):
    # Battery -> Charging: "25W wired, PD3.0 | 15W wireless ..." -> 25
    charging = all_specs.get("Battery", {}).get("Charging", "")
    match = re.search(r"(\d+)\s*W wired", charging)
    return int(match.group(1)) if match else None


CURRENCY_SYMBOLS = {"$": "USD", "€": "EUR", "£": "GBP", "₹": "INR"}


def parse_prices(text):
    """
    "$ 159.99 / € 192.00 / £ 165.81"  ->  [("USD", 159.99), ("EUR", 192.0), ("GBP", 165.81)]
    Some phones use another style, like "About 800 EUR", so we handle that too.
    """
    results = []
    if not text:
        return results

    for symbol, amount in re.findall(r"([$€£₹])\s*([\d,]+(?:\.\d+)?)", text):
        results.append((CURRENCY_SYMBOLS[symbol], float(amount.replace(",", ""))))

    if not results:
        match = re.search(r"([\d,.]+)\s*([A-Z]{3})", text)
        if match:
            results.append((match.group(2), float(match.group(1).replace(",", ""))))

    return results


def remove_strange_prices(price_list, phone_name):
    """
    Sometimes GSMArena has a wrong price.
    Example: Galaxy A55 shows $941, but €255.99 and £279.99.
    USD and EUR are usually close to each other, so if USD is more than
    2x EUR (or less than half of it), we treat the USD price as a mistake and skip it.
    """
    prices = dict(price_list)
    usd = prices.get("USD")
    eur = prices.get("EUR")

    if usd and eur and not (0.5 <= usd / eur <= 2):
        print(f"   ⚠️ {phone_name}: USD price {usd} looks wrong (EUR is {eur}), skipping USD")
        return [(currency, amount) for currency, amount in price_list if currency != "USD"]

    return price_list


def run_schema(cursor):
    """Run schema.sql one statement at a time (statements end with ;)."""
    with open(SCHEMA_FILE, encoding="utf-8") as f:
        # Remove comment lines that start with --
        lines = [line for line in f if not line.strip().startswith("--")]

    for statement in "".join(lines).split(";"):
        if statement.strip():
            cursor.execute(statement)


# ---------------------------------------------------------------
# Main part
# ---------------------------------------------------------------

def main():
    with open(JSON_FILE, encoding="utf-8") as f:
        phones = json.load(f)
    print(f"📂 Found {len(phones)} phones in {JSON_FILE}")

    conn = get_connection()
    cursor = conn.cursor()
    today = date.today()

    try:
        run_schema(cursor)
        print("🧱 Tables created")

        for phone in phones:
            ks = phone["key_specs"]
            all_specs = phone["all_specs"]

            # ---- phones table ----
            cursor.execute(
                """
                INSERT INTO phones (
                    name, release_year, announced, status,
                    display_type, display_size_inches, display_resolution,
                    os, chipset, ram_gb, storage_options,
                    main_camera_mp, main_camera, selfie_camera,
                    battery_mah, charging_watt, battery_active_use, battery_endurance,
                    weight_g, dimensions, gsmarena_url, image_url
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    phone["name"],
                    parse_year(ks.get("announced")),
                    ks.get("announced"),
                    ks.get("status"),
                    ks.get("display_type"),
                    parse_display_size(ks.get("display_size")),
                    ks.get("display_resolution"),
                    ks.get("os"),
                    ks.get("chipset"),
                    parse_max_ram(ks.get("memory")),
                    ks.get("memory"),
                    parse_main_camera_mp(ks.get("main_camera")),
                    ks.get("main_camera"),
                    ks.get("selfie_camera"),
                    parse_battery_mah(ks.get("battery")),
                    parse_charging_watt(all_specs),
                    ks.get("battery_active_use"),
                    ks.get("battery_endurance"),
                    parse_weight(ks.get("weight")),
                    ks.get("dimensions"),
                    phone["url"],
                    phone.get("image_url"),
                ),
            )
            phone_id = cursor.lastrowid   # the id MySQL just gave this phone

            # ---- specifications table (all specs in one go) ----
            spec_rows = []
            for category, specs in all_specs.items():
                for spec_name, spec_value in specs.items():
                    spec_rows.append((phone_id, category, spec_name, spec_value))

            cursor.executemany(
                "INSERT INTO specifications (phone_id, category, spec_name, spec_value) "
                "VALUES (%s, %s, %s, %s)",
                spec_rows,
            )

            # ---- prices table (after checking for wrong prices) ----
            price_list = remove_strange_prices(parse_prices(ks.get("price")), phone["name"])
            for currency, amount in price_list:
                cursor.execute(
                    "INSERT INTO prices (phone_id, currency, amount, price_text, collected_on) "
                    "VALUES (%s, %s, %s, %s, %s)",
                    (phone_id, currency, amount, ks.get("price"), today),
                )

            print(f"   ✔ {phone['name']}: {len(spec_rows)} specs, {len(price_list)} prices")

        # Save everything. If anything failed above, nothing is saved (see except).
        conn.commit()
        print("\n🎉 All data saved to MySQL!")

    except Exception as error:
        conn.rollback()
        print("❌ Something went wrong, nothing was saved:", error)
        raise

    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    main()