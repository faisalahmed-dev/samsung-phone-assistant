from functools import lru_cache

from crewai.tools import tool

from chatbot.documents import SKIP_SPECS, fmt
from database import phone_names
from database.db import get_connection

# Only the spec categories a review needs. Fewer lines keep the small model focused
# and stop it from mixing up unrelated specs (for example "NFC: Yes" and "Radio: No").
REVIEW_CATEGORIES = [
    "Body", "Display", "Platform", "Memory", "Main Camera",
    "Selfie camera", "Sound", "Battery", "Our Tests",
]


@lru_cache(maxsize=1)
def get_aliases():
    return phone_names.load_aliases()


def build_spec_sheet(phone_name):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute(
        "SELECT id, name, release_year FROM phones WHERE name = %s", (phone_name,)
    )
    phone = cursor.fetchone()

    cursor.execute(
        "SELECT category, spec_name, spec_value FROM specifications "
        "WHERE phone_id = %s ORDER BY id",
        (phone["id"],),
    )
    specs = cursor.fetchall()

    cursor.execute(
        "SELECT currency, amount, collected_on FROM prices WHERE phone_id = %s",
        (phone["id"],),
    )
    prices = cursor.fetchall()

    cursor.close()
    connection.close()

    lines = [f"SPEC SHEET: {phone['name']} (released {phone['release_year']})"]

    for category in REVIEW_CATEGORIES:
        rows = [
            spec for spec in specs
            if spec["category"] == category and spec["spec_name"] not in SKIP_SPECS
        ]
        if not rows:
            continue
        lines.append(f"\n[{category}]")
        for row in rows:
            lines.append(f"{row['spec_name']}: {row['spec_value']}")

    # Use the USD price; if a phone has no USD price, use the first available one.
    usd_prices = [p for p in prices if p["currency"] == "USD"]
    price = usd_prices[0] if usd_prices else (prices[0] if prices else None)

    lines.append("\n[Price]")
    if price:
        lines.append(
            f"{fmt(price['amount'])} {price['currency']} "
            f"(current market price, collected {price['collected_on']})"
        )
    else:
        lines.append("No price available.")

    return "\n".join(lines)


@tool("get_phone_specs", result_as_answer=True)
def get_phone_specs(phone_name: str) -> str:
    """Look up the specifications and current price of a Samsung phone
    in the database. Input: the phone name, for example "Galaxy S23" or "S24 Ultra"."""
    phones = phone_names.find_phones(phone_name, get_aliases())
    if not phones:
        return f"No phone matching '{phone_name}' was found in the database."
    return build_spec_sheet(phones[0])


if __name__ == "__main__":
    print(get_phone_specs.run("Galaxy S24 Ultra"))
    print()
    print(get_phone_specs.run("iPhone 15"))