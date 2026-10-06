"""What each level unlocks. Everyone starts with the standard stats; customization is earned.

ready: built and usable once unlocked. The later ones are placeholders: unlocking shows them as
coming in an update.
"""

UNLOCKS = [
    (7, "parts_off", "Turn parts off",
     "Leave out parts of a stat you don't track; it's judged on the rest. Drains still count.", True),
    (15, "weights", "Weight the parts", "Decide how much each part of a stat counts.", False),
    (20, "targets", "Personal targets",
     "Set your own target for any part and see your progress. Scores stay on the standard scale.", False),
    (25, "categories", "Move stats between categories", "Put any stat in the category it means to you.", False),
    (30, "questions", "Your own check-in questions", "Track anything: water, guitar, cold showers.", False),
    (40, "own_stats", "Your own stats", "Build a stat from any of your data.", False),
    (50, "mystery_50", "???", "Coming later.", False),
    (75, "mystery_75", "???", "Coming later.", False),
    (100, "mystery_100", "???", "Coming later.", False),
    (250, "mystery_250", "???", "Coming later.", False),
    (500, "mystery_500", "???", "Coming later.", False),
    (1000, "genius", "Genius", "The last unlock. Coming later.", False),
]

LEVELS = {key: level for level, key, *_ in UNLOCKS}


def ladder(level: int) -> list[dict]:
    return [
        {"level": at, "key": key, "title": title, "description": text, "unlocked": level >= at, "ready": ready}
        for at, key, title, text, ready in UNLOCKS
    ]


def require(level: int, key: str) -> None:
    """Raises PermissionError with the level it unlocks at"""
    if level < LEVELS[key]:
        raise PermissionError(f"Unlocks at LV {LEVELS[key]} (you're LV {level})")
