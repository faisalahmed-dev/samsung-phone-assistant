"""Build LangChain documents from the MySQL database for the RAG chatbot.

Three kinds of documents are created:
    overview - one short summary per phone (key numbers and price)
    spec     - one document per phone and spec category (Display, Battery, ...)
    ranking  - one document per topic comparing all phones (battery, camera, ...)

Ranking documents exist because retrieval only returns a few similar chunks.
A question like "which phone has the best battery?" needs all phones at once.

Usage (prints a summary and one example of each type):
    python -m chatbot.documents
"""

import re
from collections import Counter, defaultdict

from langchain_core.documents import Document

from database.db import get_connection

# Long, rarely asked specs. They would make the context longer without helping answers.
SKIP_SPECS = {"2G bands", "3G bands", "4G bands", "5G bands", "Speed", "SAR", "SAR EU", "Models"}


def fmt(value):
    """Format a number without trailing zeros, e.g. Decimal('6.20') -> '6.2'."""
    return f"{float(value):g}" if value is not None else "unknown"


def load_data():
    """Read phones, specs and prices from MySQL."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM phones ORDER BY id")
    phones = cursor.fetchall()

    cursor.execute("SELECT phone_id, category, spec_name, spec_value FROM specifications ORDER BY id")
    specs = defaultdict(lambda: defaultdict(dict))
    for row in cursor.fetchall():
        specs[row["phone_id"]][row["category"]][row["spec_name"]] = row["spec_value"]

    cursor.execute("SELECT phone_id, currency, amount, collected_on FROM prices ORDER BY id")
    prices = defaultdict(list)
    for row in cursor.fetchall():
        prices[row["phone_id"]].append(row)

    cursor.close()
    conn.close()
    return phones, specs, prices


def price_summary(phone_prices):
    if not phone_prices:
        return "not available"
    amounts = ", ".join(f"{fmt(p['amount'])} {p['currency']}" for p in phone_prices)
    return f"{amounts} (current market price, collected {phone_prices[0]['collected_on']})"


def build_overview(phone, phone_prices):
    """One short summary of a phone's most important specs."""
    tests = [t for t in (phone["battery_active_use"], phone["battery_endurance"]) if t]
    text = (
        f"{phone['name']} overview. Released in {phone['release_year']}. "
        f"Display: {fmt(phone['display_size_inches'])} inches, {phone['display_type']}. "
        f"Chipset: {phone['chipset']}. RAM: up to {phone['ram_gb']} GB. "
        f"Main camera: {phone['main_camera_mp']} MP. "
        f"Battery: {phone['battery_mah']} mAh, {phone['charging_watt']}W wired charging. "
        f"Battery tests: {'; '.join(tests) or 'not tested'}. "
        f"Weight: {fmt(phone['weight_g'])} g. "
        f"Price: {price_summary(phone_prices)}."
    )
    return Document(page_content=text, metadata={"type": "overview", "phone": phone["name"]})


def build_spec_docs(phone_name, phone_specs):
    """One document per spec category of a phone."""
    docs = []
    for category, items in phone_specs.items():
        lines = [f"{name}: {value}" for name, value in items.items() if name not in SKIP_SPECS]
        if lines:
            docs.append(Document(
                page_content=f"{phone_name} - {category}. " + "; ".join(lines),
                metadata={"type": "spec", "phone": phone_name, "category": category},
            ))
    return docs


def active_use_hours(text):
    """'Active use score 13:09h' -> 13.15"""
    match = re.search(r"(\d+):(\d+)h", text or "")
    return int(match.group(1)) + int(match.group(2)) / 60 if match else 0


def endurance_hours(text):
    """'Endurance rating 93h' -> 93"""
    match = re.search(r"(\d+)h", text or "")
    return int(match.group(1)) if match else 0


def build_ranking_docs(phones, specs, prices):
    """Documents that compare all phones on one topic."""
    docs = []

    def add_ranking(topic, intro, lines):
        text = (f"{topic} ranking of the {len(phones)} Samsung phones in the database. "
                f"{intro}\n" + "\n".join(lines))
        docs.append(Document(page_content=text, metadata={"type": "ranking", "topic": topic}))

    # Battery life: the two GSMArena tests are not comparable, so they are listed separately.
    tested = sorted((p for p in phones if p["battery_active_use"]),
                    key=lambda p: active_use_hours(p["battery_active_use"]), reverse=True)
    old_only = sorted((p for p in phones if not p["battery_active_use"]),
                      key=lambda p: endurance_hours(p["battery_endurance"]), reverse=True)
    lines = [f"{i}. {p['name']}: {p['battery_active_use']} ({p['battery_mah']} mAh)"
             for i, p in enumerate(tested, 1)]
    lines.append("Phones tested only with the older Endurance rating (not comparable with Active use score):")
    lines += [f"- {p['name']}: {p['battery_endurance']} ({p['battery_mah']} mAh)" for p in old_only]
    add_ranking("Battery life",
                "Ranked by GSMArena's Active use score, higher is better. "
                "A bigger battery (mAh) does not always mean longer battery life.", lines)

    # Main camera
    ranked = sorted(phones, key=lambda p: p["main_camera_mp"], reverse=True)
    add_ranking("Main camera",
                "Ranked by main camera resolution. More megapixels does not always mean better photos.",
                [f"{i}. {p['name']}: {p['main_camera_mp']} MP" for i, p in enumerate(ranked, 1)])

    # Display size
    ranked = sorted(phones, key=lambda p: p["display_size_inches"], reverse=True)
    add_ranking("Display size", "Ranked from the largest to the smallest screen.",
                [f"{i}. {p['name']}: {fmt(p['display_size_inches'])} inches, {p['display_type']}"
                 for i, p in enumerate(ranked, 1)])

    # Price (USD)
    def usd(phone):
        return next((x["amount"] for x in prices[phone["id"]] if x["currency"] == "USD"), None)

    with_usd = sorted((p for p in phones if usd(p) is not None), key=usd)
    lines = [f"{i}. {p['name']}: {fmt(usd(p))} USD" for i, p in enumerate(with_usd, 1)]
    for p in phones:
        if usd(p) is None:
            lines.append(f"- {p['name']}: no reliable USD price ({price_summary(prices[p['id']])})")
    add_ranking("Price", "Ranked from the cheapest to the most expensive (current market price).", lines)

    # Performance: chipset and AnTuTu score
    ranked = sorted(phones, key=lambda p: (p["release_year"], p["name"]), reverse=True)
    lines = []
    for p in ranked:
        performance = specs[p["id"]].get("Our Tests", {}).get("Performance", "not tested")
        lines.append(f"- {p['name']} ({p['release_year']}): {p['chipset']}. {performance.split(' | ')[0]}")
    add_ranking("Performance",
                "Chipset and AnTuTu benchmark score, newest phones first. Higher AnTuTu is better, "
                "but only compare scores of the same AnTuTu version (v8, v9, v10).", lines)

    return docs


def build_documents():
    """Build all documents for the chatbot."""
    phones, specs, prices = load_data()
    docs = []
    for phone in phones:
        docs.append(build_overview(phone, prices[phone["id"]]))
        docs.extend(build_spec_docs(phone["name"], specs[phone["id"]]))
    docs.extend(build_ranking_docs(phones, specs, prices))
    return docs


if __name__ == "__main__":
    documents = build_documents()
    counts = Counter(doc.metadata["type"] for doc in documents)
    print(f"Built {len(documents)} documents: {dict(counts)}")

    for doc_type in ("overview", "spec", "ranking"):
        example = next(doc for doc in documents if doc.metadata["type"] == doc_type)
        print(f"\n--- Example {doc_type} document ---")
        print(example.page_content)