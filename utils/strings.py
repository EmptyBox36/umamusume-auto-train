import re
import unicodedata

# def clean_event_name(s):
#     s = s.replace("`", "'")
#     s = re.sub(r"[^\w\s]", " ", s)   # drop punctuation (e.g., ! ☆ , .)
#     s = " ".join(s.split()).lower()  # collapse spaces + lowercase
#     return s


# Normalize punctuation variants but KEEP parentheses content for display
def normalize_event_title(s: str) -> str:
    if not s:
        return ""
    # unify unicode quotes/dashes
    s = unicodedata.normalize("NFKC", s)
    # collapse spaces
    s = " ".join(s.split())
    return s.strip()


# Produce a robust lookup key:
# - lowercase
# - keep the text INSIDE parentheses, drop the parens themselves
# - drop other punctuation, collapse spaces
def event_match_key(s: str) -> str:
    if not s:
        return ""
    s = normalize_event_title(s)
    # turn "(Delicious) Burden" -> "Delicious Burden" (keep inside)
    s = re.sub(r"\(([^)]*)\)", r"\1", s)
    # remove remaining punctuation except spaces and word chars
    s = re.sub(r"[^\w\s]", " ", s)
    s = " ".join(s.split()).lower()
    return s


def clean_event_name(s: str) -> str:
    return event_match_key(s)
