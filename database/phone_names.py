"""Find Samsung phone names in free text, e.g. "s23 vs galaxy s22" -> two phones."""

import re

from database.db import get_connection


def simplify(text):
    """Normalize a phone name so it can be matched in any format.

    'Samsung Galaxy S23 Ultra' -> 's23ultra', 'galaxy z fold 5' -> 'zfold5'
    """
    text = text.lower()
    for word in ("samsung", "galaxy", "5g"):
        text = text.replace(word, "")
    return re.sub(r"[^a-z0-9]", "", text)


def load_aliases():
    """Map short names to full names, e.g. {'s23': 'Samsung Galaxy S23', 'fold5': ...}."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM phones")
    names = [row[0] for row in cursor.fetchall()]
    cursor.close()
    conn.close()

    aliases = {}
    for name in names:
        short = simplify(name)
        aliases[short] = name
        if short.startswith("z"):  # people often write "Fold5" without the Z
            aliases[short[1:]] = name
    return aliases


def find_phones(text, aliases):
    """Return the full names of the phones mentioned in text.

    Longer names are checked first and removed after a match,
    so "S23 Ultra" is not also counted as "S23".
    """
    simple = simplify(text)
    found = []
    for alias in sorted(aliases, key=len, reverse=True):
        if alias in simple:
            if aliases[alias] not in found:
                found.append(aliases[alias])
            simple = simple.replace(alias, "#")
    return found