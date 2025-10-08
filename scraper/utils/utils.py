import re

COMMON_EVENT_TITLES = {
  "Extra Training",
  "At Summer Camp (Year 2)",
  "Just an Acupuncturist, No Worries! ☆",
  "Get Well Soon!",
  "Don't Overdo It!",
  "Victory!", 
  "Solid Showing", 
  "Defeat", 
  "Etsuko's Exhaustive Coverage",
}

STAT_KEYS = ["Friendship","Guts","HP","Max Energy","Mood","Power",
             "Skill","Skill Hint","Skill Pts","Speed","Stamina","Wit"]

PREFIX_EVENTS = {
    "Acupuncture",
    "Failed training"
}

RACE_RESULT_EVENTS = {
    "Victory!", 
    "Solid Showing", 
    "Defeat", 
    "Etsuko's Exhaustive Coverage"}

ALIASES = {
    "Energy": "HP",
    "Maximum Energy": "Max Energy",
    "Max Energy": "Max Energy",
    "Wisdom": "Wit",
    "Skill points": "Skill Pts",
    "Skill Points": "Skill Pts",
    "Skill hint": "Skill Hint",
    "Skill Hint": "Skill Hint",
}

ALL_STATS = ["Speed","Stamina","Power","Guts","Wit","Skill"]
DIVIDER_RE = re.compile(r"\n[-─—]{3,}\n", re.U)
RAND_SPLIT_RE = re.compile(r"\n(?:[-─—]{3,}\n|\s*or(?:\s*\([^)]+\))?\s*\n)", re.I)

IGNORE_PATTERNS = (
    "Get ", "status", "Nothing happens", "or (~", "Last trained stat",
    "random stat", "random stats"
)

def clean_event_title(title: str) -> str:
    # remove decorative prefixes like (❯❯), (▶), (★), etc.
    title = re.sub(r"^\s*[\(\[\{❯▶★♦■◆☆]*\s*[\)\]\}❯▶★♦■◆☆]*\s*", "", title)

    # remove decorative suffixes like ☆, ★, ◆, etc.
    title = re.sub(r"[\s❯▶★♦■◆☆]+$", "", title)

    # handle special prefix cases (Acupuncture, Failed training)
    for prefix in PREFIX_EVENTS:
        if title.lower().startswith(prefix.lower()):
            m = re.search(r"\(([^)]+)\)", title)
            if m:
                return m.group(1).strip()

    # handle race result events
    for base in RACE_RESULT_EVENTS:
        if title.startswith(base):
            return base

    return title.strip()