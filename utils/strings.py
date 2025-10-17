import re
import unicodedata

def clean_event_name(name: str) -> str:
    """Normalize event names safely without reordering words."""
    if not name:
        return ""
    # Normalize Unicode and remove accents
    name = unicodedata.normalize("NFKD", name)
    # Keep word order, remove weird symbols but preserve spacing
    name = re.sub(r"[^A-Za-z0-9\s'\-!?.]", "", name)
    # Remove extra spaces and lowercase
    name = re.sub(r"\s+", " ", name).strip().lower()
    return name
