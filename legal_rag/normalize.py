"""Conservative Arabic normalization for keyword search, never source display."""

import re
import unicodedata

NORMALIZER_VERSION = "arabic-keywords-v1"
TRANSLATION = str.maketrans("أإآٱ٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "اااا01234567890123456789")


def normalize_search_text(text: str) -> str:
    # Expand Arabic presentation forms only; do not compatibility-normalize
    # arbitrary numbers, fractions, units or mathematical symbols.
    text = "".join(unicodedata.normalize("NFKC", char)
                   if "\ufb50" <= char <= "\ufdff" or "\ufe70" <= char <= "\ufeff"
                   else char for char in text)
    text = unicodedata.normalize("NFC", text).translate(TRANSLATION)
    text = re.sub(r"[\u0610-\u061a\u064b-\u065f\u0670\u06d6-\u06ed\u0640]", "", text)
    text = "".join(char for char in text if unicodedata.category(char) != "Cf")
    return " ".join(text.casefold().split())
