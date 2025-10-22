import re
def clean_event_name(s):
    s = s.replace("`", "'")
    s = re.sub(r"[^\w\s]", " ", s)   # drop punctuation (e.g., ! ☆ , .)
    s = " ".join(s.split()).lower()  # collapse spaces + lowercase
    return s