"""Every value a day can hold: what it's called, how it's entered, where it usually comes from, and
which stats read it. The apps build the "About you" screen from this, so a new field or a formula that
starts reading one only needs a change here (tests check it against the DailyLogIn schema)."""

SECTIONS = [
    ('sleep', 'Sleep'),
    ('work', 'Work'),
    ('mind', 'Mind'),
    ('screen', 'Phone use'),
    ('body', 'Body'),
    ('social', 'Social'),
]

# kind: decimal / whole / yesno / time (HH:MM). source: phone (synced), checkin (typed in), both.
# feeds: stat codes whose formulas read the value (character_stats.py).
FIELDS = [
    ('sleep', 'hours', 'Hours slept', 'h', 'decimal', 'both', ['MP', 'DIS']),
    ('sleep', 'bed', 'Fell asleep', '', 'time', 'phone', ['MP']),
    ('sleep', 'wake', 'Woke up', '', 'time', 'phone', ['MP']),
    ('sleep', 'quality', 'Sleep quality (wearable)', '/100', 'whole', 'phone', ['MP']),
    ('sleep', 'alcohol', 'Alcoholic drinks the evening before', 'drinks', 'whole', 'checkin', ['MP']),
    ('sleep', 'late_caffeine', 'Caffeine within 6h of bedtime', '', 'yesno', 'checkin', ['MP']),
    ('sleep', 'screen_before_bed', 'Phone in the last hour before sleep', '', 'yesno', 'phone', ['MP']),
    ('work', 'total', 'Hours worked', 'h', 'decimal', 'checkin', ['MP']),
    ('work', 'deep', 'Deep-focus hours', 'h', 'decimal', 'checkin', ['MP']),
    ('mind', 'learning_min', 'Learning', 'min', 'whole', 'checkin', ['INT']),
    ('mind', 'meditation_min', 'Meditation', 'min', 'whole', 'checkin', ['MP']),
    ('screen', 'short_video_min', 'Reels / Shorts / TikTok', 'min', 'whole', 'phone', ['MP', 'FOC']),
    ('screen', 'social_min', 'Social feeds', 'min', 'whole', 'phone', ['FOC']),
    ('screen', 'long_video_min', 'Long video (YouTube, Netflix…)', 'min', 'whole', 'phone', ['MP']),
    ('screen', 'gaming_min', 'Gaming', 'min', 'whole', 'phone', ['MP']),
    ('screen', 'total_min', 'Total screen time', 'min', 'whole', 'phone', ['FOC']),
    ('screen', 'night_min', 'Phone use after midnight', 'min', 'whole', 'phone', ['FOC']),
    ('screen', 'unlocks', 'Unlocks', '', 'whole', 'phone', ['FOC']),
    ('body', 'steps', 'Steps', '', 'whole', 'phone', ['MP', 'STA']),
    ('body', 'active_min', 'Active minutes', 'min', 'whole', 'phone', ['MP', 'STA']),
    ('body', 'pushups', 'Push-ups', '', 'whole', 'checkin', ['PS', 'DIS']),
    ('body', 'max_pushups', 'Max push-ups in one set', '', 'whole', 'checkin', ['PS']),
    ('body', 'strength', 'Other strength training', '', 'yesno', 'checkin', ['PS']),
    ('body', 'outdoor_min', 'Outdoors', 'min', 'whole', 'checkin', ['MP']),
    ('body', 'shower', 'Showered', '', 'yesno', 'checkin', ['DIS']),
    ('body', 'weight_kg', 'Weight', 'kg', 'decimal', 'both', ['H']),
    ('body', 'resting_hr', 'Resting heart rate', 'bpm', 'whole', 'phone', []),
    ('social', 'interactions', 'Meaningful contacts (30+ min)', '', 'whole', 'checkin', ['SOC']),
]


def catalog() -> dict:
    return {
        'sections': [{'key': key, 'title': title} for key, title in SECTIONS],
        'fields': [
            {'section': section, 'key': key, 'label': label, 'unit': unit, 'kind': kind, 'source': source, 'feeds': feeds}
            for section, key, label, unit, kind, source, feeds in FIELDS
        ],
    }
