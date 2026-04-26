# tests/test_transformations.py
# Unit tests for Silver layer transformation functions.
# Tests verify that weight, price and vendor normalization
# produce correct results for all known edge cases in the dataset.
#
# Run with: python -m pytest tests/test_transformations.py -v

import pytest
import re

# ── Copy transformation functions here for testing ───────────────────────────
# We duplicate the functions from 02_silver_standardize so tests can run
# without a Spark/Databricks context — pure Python, runs anywhere including CI/CD


def parse_weight_to_kg(raw):
    """
    Parses any weight string and returns a float in kg.
    Handles: kg, g, grams, gr, grs, kilograms, G, Kg, KG etc.
    Returns None if the value cannot be parsed.
    """
    if raw is None or str(raw).strip().lower() in ("none", "nan", ""):
        return None
    
    raw = str(raw).strip().lower()    
    # Remove trailing period — handles "Kg.", "grs.", "g." etc.
    raw = raw.rstrip(".")
    
    # Extract the numeric part (handles: 12.5, 1,8, 12 5 with spaces)
    # Remove currency symbols and text, keep digits, dots, commas
    numeric_str = re.sub(r"[^\d.,]", " ", raw).strip()
    # Handle comma as decimal separator and remove spaces between digits
    numeric_str = numeric_str.replace(",", ".").replace(" ", "")
    
    try:
        value = float(numeric_str)
    except:
        return None
    
    # Detect unit and convert to kg
    if any(unit in raw for unit in ["kilogram", "kilograms"]):
        return round(value, 4)
    elif raw.endswith("kg") or " kg" in raw:
        return round(value, 4)
    elif any(unit in raw for unit in ["gram", "grams", "gr", "grs", "g.", " g"]):
        return round(value / 1000, 4)
    elif raw[-1] == "g" or raw.endswith("kg"):
        # ends with just "g" like "900g" or "370gr"
        if "kg" in raw:
            return round(value, 4)
        else:
            return round(value / 1000, 4)
    else:
        # Default: if unit unclear but value seems reasonable for kg, keep as is
        return round(value, 4)


    """Parses any price string and returns a float in USD."""
    if raw is None or str(raw).strip().lower() in ("none", "nan", ""):
        return None

    raw = str(raw).strip().lower()
    raw = raw.replace("$", "").replace("usd", "").replace("dollars", "").strip()

    if "," in raw and "." in raw:
        raw = raw.replace(",", "")
    elif "," in raw and "." not in raw:
        parts = raw.split(",")
        if len(parts) == 2 and len(parts[1].strip()) <= 2:
            raw = raw.replace(",", ".")
        else:
            raw = raw.replace(",", "")

    space_decimal = re.match(r"^(\d+)\s(\d{2})$", raw.strip())
    if space_decimal:
        raw = f"{space_decimal.group(1)}.{space_decimal.group(2)}"
    else:
        raw = raw.replace(" ", "")

    try:
        return round(float(raw), 2)
    except:
        return None

def parse_price_to_usd(raw):
    
    if raw is None or str(raw).strip().lower() in ("none", "nan", ""):
        return None
    
    raw = str(raw).strip().lower()
    
    # Remove known text
    raw = raw.replace("$", "").replace("usd", "").replace("dollars", "").strip()
    
    # If both comma AND period exist → comma is thousands separator → remove it
    # Example: "1,099.00" → "1099.00"
    if "," in raw and "." in raw:
        raw = raw.replace(",", "")
    
    # If only comma exists and 2 digits follow → decimal separator
    # Example: "349,00" → "349.00"
    elif "," in raw and "." not in raw:
        parts = raw.split(",")
        if len(parts) == 2 and len(parts[1].strip()) <= 2:
            raw = raw.replace(",", ".")
        else:
            raw = raw.replace(",", "")
    
    # Handle space as decimal separator: "59 99" → "59.99"
    space_decimal = re.match(r"^(\d+)\s(\d{2})$", raw.strip())
    
    if space_decimal:
        raw = f"{space_decimal.group(1)}.{space_decimal.group(2)}"
    else:
        raw = raw.replace(" ", "")
    
    try:
        return round(float(raw), 2)
    except:
        return None
    
def remove_suffixes(text: str) -> str:
    """
    Removes legal suffixes only when they appear at the END of the string.
    The $ anchor ensures we never remove these patterns from inside words.
    """
    # Order matters — longer suffixes first to avoid partial matches
    suffixes = [
        r"\s+corporation$",   # " corporation" at end
        r"\s+corp\.$",        # " corp." at end
        r"\s+corp$",          # " corp" at end
        r"\s+incorporated$",  # " incorporated" at end
        r"\s+inc\.$",         # " inc." at end
        r"\s+inc$",           # " inc" at end
        r"\s+limited$",       # " limited" at end
        r"\s+ltd\.$",         # " ltd." at end
        r"\s+ltd$",           # " ltd" at end
        r"\s+co\.$",          # " co." at end
        r"\s+co$",            # " co" at end
        r",$",                # trailing comma
    ]

    for suffix in suffixes:
        # re.sub replaces the pattern only if it matches at end of string ($)
        # re.IGNORECASE makes it case-insensitive
        text = re.sub(suffix, "", text, flags=re.IGNORECASE).strip()

    return text

def normalize_vendor(raw):
    if raw is None:
        return None

    cleaned = str(raw).strip()
    if cleaned == "" or cleaned.lower() in ("none", "nan", "null"):
        return None

    # ── STEP 1: Generic cleaning ──────────────────────────────────────────
    normalized = " ".join(cleaned.split()).lower()  # collapse spaces + lowercase

    # Remove legal suffixes safely — only at end of string
    normalized = remove_suffixes(normalized)

    # Remove trailing period and convert to Title Case
    normalized = normalized.rstrip(".").strip()
    normalized = normalized.title()

    # ── STEP 2: Canonical mapping ─────────────────────────────────────────
    canonical_map = {
        "Amazon.Com"             : "Amazon",
        "Asus Tek"               : "Asus",
        "Asus Tek Computer"      : "Asus",
        "Hyperx (Kingston)"      : "HyperX (Kingston)",
        "Hp"                     : "HP",
        "Dji Technology"         : "DJI Technology",
        "Logitech International S.A": "Logitech",
    }

    return canonical_map.get(normalized, normalized)


# ── Weight Tests ──────────────────────────────────────────────────────────────

class TestParseWeightToKg:
    """Tests for weight normalization function."""

    def test_kg_with_space(self):
        # "12.5 kg" is the cleanest format — should parse directly
        assert parse_weight_to_kg("12.5 kg") == 12.5

    def test_kg_without_space(self):
        # "1.8kg" has no space between number and unit
        assert parse_weight_to_kg("1.8kg") == 1.8

    def test_kg_uppercase(self):
        # "0.206 KG" — uppercase unit should still work
        assert parse_weight_to_kg("0.206 KG") == 0.206

    def test_kg_with_trailing_period(self):
        # "0.96 Kg." — trailing period is a common Excel artifact
        assert parse_weight_to_kg("0.96 Kg.") == 0.96

    def test_kilograms_full_word(self):
        # "5.8 Kilograms" — full word spelling
        assert parse_weight_to_kg("5.8 Kilograms") == 5.8

    def test_grams_full_word(self):
        # "250 grams" → should convert to 0.25 kg
        assert parse_weight_to_kg("250 grams") == 0.25

    def test_grams_abbreviated_gr(self):
        # "370gr" → 0.37 kg
        assert parse_weight_to_kg("370gr") == 0.37

    def test_grams_abbreviated_g_uppercase(self):
        # "141 G." — uppercase G with trailing period
        assert parse_weight_to_kg("141 G.") == 0.141

    def test_grams_abbreviated_grs(self):
        # "32.9 grs" — plural abbreviation
        assert parse_weight_to_kg("32.9 grs") == 0.0329

    def test_grams_abbreviated_grs_with_period(self):
        # "205 Grs." — capitalized with trailing period
        assert parse_weight_to_kg("205 Grs.") == 0.205

    def test_small_grams(self):
        # "6.8 g" — very small value in grams
        assert parse_weight_to_kg("6.8 g") == 0.0068

    def test_none_returns_none(self):
        # None input should return None gracefully
        assert parse_weight_to_kg(None) is None

    def test_empty_string_returns_none(self):
        # Empty string should return None
        assert parse_weight_to_kg("") is None

    def test_nan_string_returns_none(self):
        # "nan" is what pandas produces for missing values cast to string
        assert parse_weight_to_kg("nan") is None


# ── Price Tests ───────────────────────────────────────────────────────────────

class TestParsePriceToUsd:
    """Tests for price normalization function."""

    def test_dollar_sign_with_decimal(self):
        # "$499.99" — standard US format
        assert parse_price_to_usd("$499.99") == 499.99

    def test_plain_number(self):
        # "749" — no currency symbol
        assert parse_price_to_usd("749") == 749.0

    def test_usd_suffix(self):
        # "999.00 USD" — text suffix
        assert parse_price_to_usd("999.00 USD") == 999.0

    def test_space_as_decimal_separator(self):
        # "59 99" — space acting as decimal point
        assert parse_price_to_usd("59 99") == 59.99

    def test_space_inside_number(self):
        # "$4 50.00" — rogue space inside number
        assert parse_price_to_usd("$4 50.00") == 450.0

    def test_comma_as_decimal_separator(self):
        # "349,00 usd" — comma as decimal (European format)
        assert parse_price_to_usd("349,00 usd") == 349.0

    def test_comma_as_thousands_separator(self):
        # "1,099.00 USD" — comma as thousands separator
        assert parse_price_to_usd("1,099.00 USD") == 1099.0

    def test_dollars_suffix(self):
        # "$ 249.00 dollars" — full word suffix
        assert parse_price_to_usd("$ 249.00 dollars") == 249.0

    def test_none_returns_none(self):
        assert parse_price_to_usd(None) is None

    def test_empty_string_returns_none(self):
        assert parse_price_to_usd("") is None

    def test_nan_string_returns_none(self):
        assert parse_price_to_usd("nan") is None


# ── Vendor Tests ──────────────────────────────────────────────────────────────
class TestNormalizeVendor:
    """
    Tests for vendor name normalization function.
    Expected behavior (Option B):
    - Legal suffixes are removed (Inc, Ltd, Co, Corp, Corporation)
    - Extra spaces are collapsed
    - Result is Title Case
    - Known abbreviations are mapped to canonical names
    """

    def test_lowercase_to_title_case(self):
        # "sony corporation" → removes "corporation" → "Sony"
        assert normalize_vendor("sony corporation") == "Sony"

    def test_uppercase_to_title_case(self):
        # "LENOVO GROUP LTD" → removes "ltd" → "Lenovo Group"
        assert normalize_vendor("LENOVO GROUP LTD") == "Lenovo Group"

    def test_trailing_period_removed(self):
        # "Redragon Inc." → removes "inc." → "Redragon"
        assert normalize_vendor("Redragon Inc.") == "Redragon"

    def test_extra_spaces_collapsed(self):
        # "Redragon  Inc." → collapses double space → removes "inc." → "Redragon"
        assert normalize_vendor("Redragon  Inc.") == "Redragon"

    def test_sony_corp_abbreviation(self):
        # "Sony Corp." → removes "corp." → "Sony"
        assert normalize_vendor("Sony Corp.") == "Sony"

    def test_samsung_co_abbreviation(self):
        # "Samsung Electronics Co." → removes "co." → "Samsung Electronics"
        assert normalize_vendor("Samsung Electronics Co.") == "Samsung Electronics"

    def test_apple_inc_standardized(self):
        # "Apple Inc" → removes "inc" → "Apple"
        assert normalize_vendor("Apple Inc") == "Apple"

    def test_asus_canonical(self):
        # "Asus Tek Computer Inc." → removes "inc." → canonical map → "Asus"
        assert normalize_vendor("Asus Tek Computer Inc.") == "Asus"

    def test_nintendo_canonical(self):
        # "Nintendo co ltd" → removes "ltd" then "co" → "Nintendo"
        assert normalize_vendor("Nintendo co ltd") == "Nintendo"

    def test_none_returns_none(self):
        # None input should return None gracefully
        assert normalize_vendor(None) is None

    def test_empty_string_returns_none(self):
        # Empty string should return None
        assert normalize_vendor("") is None

    def test_nan_string_returns_none(self):
        # "nan" is what pandas produces for missing values cast to string
        assert normalize_vendor("nan") is None