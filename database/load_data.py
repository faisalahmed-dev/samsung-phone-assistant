"""Load data/phones.json into the MySQL tables defined in schema.sql.

Usage:
    python -m database.load_data
"""

import json
import os
import re
from datetime import date

from database.db import get_connection

SCHEMA_FILE = os.path.join(os.path.dirname(__file__), "schema.sql")
JSON_FILE = os.path.join("data", "phones.json")

CURRENCY_SYMBOLS = {"$": "USD", "€": "EUR", "£": "GBP", "₹": "INR"}


# Parsers: extract numbers from GSMArena text. They return None (NULL) if nothing matches.

def parse_year(text):
    match = re.search(r"(20\d{2})", text or "")
    return int(match.group(1)) if match else None


def parse_display_size(text):
    match = re.search(r"([\d.]+)\s*inches", text or "")
    return float(match.group(1)) if match else None


def parse_battery_mah(text):
    match = re.search(r"(\d+)\s*mAh", text or "")
    return int(match.group(1)) if match else None


def parse_weight(text):
    # "169 g (Sub6), 171 g (mmWave)" -> 169.0 (first value)
    match = re.search(r"([\d.]+)\s*g\b", text or "")
    return float(match.group(1)) if match else None


def parse_max_ram(text):
    # "128GB 6GB RAM, 256GB 8GB RAM" -> 8 (largest option)
    numbers = re.findall(r"(\d+)\s*GB RAM", text or "")
    return max(int(n) for n in numbers) if numbers else None


def parse_main_camera_mp(text):
    # GSMArena lists the main (wide) camera first. The largest value is not always
    # the main camera: on the S21 it is the 64 MP telephoto.
    match = re.search(r"(\d+)\s*MP", text or "")
    return int(match.group(1)) if match else None


def parse_charging_watt(all_specs):
    charging = all_specs.get("Battery", {}).get("Charging", "")
    match = re.search(r"(\d+)\s*W wired", charging)
    return int(match.group(1)) if match else None


def parse_prices(text):
    """Split a price string into (currency, amount) pairs.

    Handles "$ 159.99 / € 192.00" as well as the older "About 800 EUR" format.
    """
    if not text:
        return []

    results = [
        (CURRENCY_SYMBOLS[symbol], float(amount.replace(",", "")))
        for symbol, amount in re.findall(r"([$€£₹])\s*([\d,]+(?:\.\d+)?)", text)
    ]

    if not results:
        match = re.search(r"([\d,.]+)\s*([A-Z]{3})", text)
        if match:
            results.append((match.group(2), float(match.group(1).replace(",", ""))))

    return results


def remove_strange_prices(price_list, phone_name):
    """Drop the USD price when it is more than 2x away from the EUR price.

    GSMArena occasionally lists a wrong USD price (e.g. Galaxy A55: $941 vs €255.99).
    """
    prices = dict(price_list)
    usd, eur = prices.get("USD"), prices.get("EUR")

    if usd and eur and not 0.5 <= usd / eur <= 2:
        print(f"  Warning: {phone_name} USD price {usd} looks wrong (EUR {eur}), skipped")
        return [(currency, amount) for currency, amount in price_list if currency != "USD"]

    return price_list


def run_schema(cursor):
    """Execute schema.sql statement by statement."""
    with open(SCHEMA_FILE, encoding="utf-8") as f:
        lines = [line for line in f if not line.strip().startswith("--")]

    for statement in "".join(lines).split(";"):
        if statement.strip():
            cursor.execute(statement)


def insert_phone(cursor, phone):
    """Insert one phone into the phones table and return its new id."""
    ks = phone["key_specs"]
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
            parse_charging_watt(phone["all_specs"]),
            ks.get("battery_active_use"),
            ks.get("battery_endurance"),
            parse_weight(ks.get("weight")),
            ks.get("dimensions"),
            phone["url"],
            phone.get("image_url"),
        ),
    )
    return cursor.lastrowid


def main():
    with open(JSON_FILE, encoding="utf-8") as f:
        phones = json.load(f)
    print(f"Found {len(phones)} phones in {JSON_FILE}")

    conn = get_connection()
    cursor = conn.cursor()
    today = date.today()

    try:
        run_schema(cursor)
        print("Tables created")

        for phone in phones:
            phone_id = insert_phone(cursor, phone)

            spec_rows = [
                (phone_id, category, spec_name, spec_value)
                for category, specs in phone["all_specs"].items()
                for spec_name, spec_value in specs.items()
            ]
            cursor.executemany(
                "INSERT INTO specifications (phone_id, category, spec_name, spec_value) "
                "VALUES (%s, %s, %s, %s)",
                spec_rows,
            )

            price_text = phone["key_specs"].get("price")
            price_list = remove_strange_prices(parse_prices(price_text), phone["name"])
            for currency, amount in price_list:
                cursor.execute(
                    "INSERT INTO prices (phone_id, currency, amount, price_text, collected_on) "
                    "VALUES (%s, %s, %s, %s, %s)",
                    (phone_id, currency, amount, price_text, today),
                )

            print(f"  {phone['name']}: {len(spec_rows)} specs, {len(price_list)} prices")

        # Commit only if every phone was inserted, so the database is never half-filled.
        conn.commit()
        print("\nAll data saved to MySQL")

    except Exception as error:
        conn.rollback()
        print(f"Error, nothing was saved: {error}")
        raise

    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    main()