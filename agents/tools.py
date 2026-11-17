"""Tools for the CrewAI agents.

Tool test (prints the spec sheet the agent would receive):
    python -m agents.tools
"""

from functools import lru_cache

from crewai.tools import tool

from chatbot.documents import SKIP_SPECS, fmt
from database.db import get_connection
from database.phone_names import find_phones, load_aliases


@lru_cache(maxsize=1)
def get_aliases():
    """Load the phone name aliases once and reuse them."""
    return load_aliases()


def build_spec_sheet(phone_name):
    """Return a text spec sheet for one phone, read from MySQL."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT id, name, release_year FROM phones WHERE name = %s", (phone_name,))
    phone = cursor.fetchone()

    cursor.execute(
        "SELECT category, spec_name, spec_value FROM specifications WHERE phone_id = %s ORDER BY id",
        (phone["id"],),
    )
    specs = cursor.fetchall()

    cursor.execute(
        "SELECT currency, amount, collected_on FROM prices WHERE phone_id = %s ORDER BY id",
        (phone["id"],),
    )
    prices = cursor.fetchall()

    cursor.close()
    conn.close()

    lines = [f"SPEC SHEET: {phone['name']} (released {phone['release_year']})"]
    current_category = None
    for row in specs:
        if row["spec_name"] in SKIP_SPECS:
            continue
        if row["category"] != current_category:
            current_category = row["category"]
            lines.append(f"\n[{current_category}]")
        lines.append(f"{row['spec_name']}: {row['spec_value']}")

    if prices:
        amounts = ", ".join(f"{fmt(p['amount'])} {p['currency']}" for p in prices)
        lines.append(f"\n[Price]\n{amounts} (current market price, collected {prices[0]['collected_on']})")

    return "\n".join(lines)


@tool("get_phone_specs")
def get_phone_specs(phone_name: str) -> str:
    """Look up the full specifications and current price of a Samsung phone
    in the database. Input: the phone name, for example "Galaxy S23" or "S24 Ultra"."""
    phones = find_phones(phone_name, get_aliases())
    if not phones:
        return f"No phone matching '{phone_name}' was found in the database."
    return build_spec_sheet(phones[0])


if __name__ == "__main__":
    print(get_phone_specs.run("Galaxy S23"))
    print("\n" + "-" * 60 + "\n")
    print(get_phone_specs.run("iPhone 15"))