"""Character stats for Life RPG: MP, PS, STA, INT, DIS, SOC, WLT.

Every stat is 0-100, built from weighted components that each score 0-1.
A component whose input was never logged is left out and the remaining
weights are rescaled, so missing data never counts as a zero. `confidence`
is the share of the formula that real data covered.

The research behind each curve and weight is listed in README.md under
"Character Stats".
"""
from datetime import datetime, timedelta
from statistics import mean, pstdev

STATS = [
    ('MP', 'Mental Power'),
    ('PS', 'Physical Strength'),
    ('STA', 'Stamina'),
    ('H', 'Health'),
    ('INT', 'Intellect'),
    ('DIS', 'Discipline'),
    ('FOC', 'Focus'),
    ('SOC', 'Social'),
    ('WLT', 'Wealth'),
]

# The six areas of a life the stats are grouped into. Each area is the average of its stats that have
# data, and TOTAL is the average of the areas, so every area counts the same however many stats it has.
CATEGORIES = [
    ('mental', 'Mental', ['MP', 'FOC']),       # mental energy and attention
    ('physical', 'Physical', ['PS', 'STA', 'H']),  # strength, endurance, eating and weight
    ('practical', 'Practical', ['WLT']),       # earning and providing
    ('cultural', 'Cultural', ['INT']),         # learning, reading, skills
    ('discipline', 'Discipline', ['DIS']),     # doing what you said you'd do
    ('social', 'Social', ['SOC']),             # people
]

SLEEP_NEED = 7.5  # hours/night; adult consensus range is 7-9

# --- Mental Power curves (x → 0-1 unless noted) ---------------------------
# Hours slept. Van Dongen 2003: 6h/night for two weeks ≈ the deficit of a full
# night awake. Lim & Dinges 2010: attention and working memory suffer most.
SLEEP_HOURS = [(0, 0), (4, 0.25), (5, 0.5), (6, 0.75), (7, 1), (9, 1), (10, 0.9), (12, 0.7)]
# Short sleep also caps MP outright (value is the cap, not 0-1).
SLEEP_CEILING = [(3, 40), (4, 55), (5, 70), (6, 85), (7, 100)]
# 7-day sleep debt in hours. Van Dongen 2003: deficits accumulate near-linearly.
SLEEP_DEBT = [(0, 1), (3.5, 0.75), (7, 0.5), (14, 0)]
# Std dev of sleep midpoint in minutes. Phillips 2017, Windred 2024.
SLEEP_SPREAD = [(30, 1), (60, 0.6), (90, 0.3), (120, 0)]
# Deep-work hours. Ericsson 1993: ~4h/day of full concentration is the ceiling.
DEEP_WORK = [(0, 0), (1, 0.4), (2, 0.7), (3, 0.9), (4, 1)]
# Short-form video minutes → points lost. Nguyen 2025 meta-analysis:
# r = -.38 with attention, -.41 with inhibitory control.
SHORT_VIDEO = [(0, 0), (30, 4), (60, 8), (120, 14), (180, 20)]

# --- Body curves -----------------------------------------------------------
# Max push-ups in one set. Yang 2019: >40 ≈ 96% fewer CVD events than <10.
PUSHUP_TEST = [(0, 0), (10, 0.3), (20, 0.55), (30, 0.75), (40, 0.9), (50, 1)]
PUSHUP_SESSION = 30  # push-ups in a day that count as a strength session
MIN_DAYS = 3  # logged days a rolling stat needs, so one good day isn't read as a habit
MIN_SPAN = 7  # tracked days before training consistency is judged
# Daily steps (7-day average). Paluch 2022: benefit plateaus at 8-10k under 60.
STEPS = [(0, 0), (4000, 0.35), (6000, 0.6), (8000, 0.85), (10000, 1)]
# Moderate-to-vigorous minutes per week. WHO 2020: 150-300.
CARDIO_WEEK = [(0, 0), (75, 0.5), (150, 0.85), (300, 1)]

# --- Focus: phone habits, 7-day averages ------------------------------------
# Short-form video minutes. Nguyen 2025: heavier use goes with poorer attention and inhibitory control.
FOCUS_SHORT_VIDEO = [(0, 1), (15, 1), (30, 0.75), (60, 0.45), (120, 0.15), (180, 0)]
# Social feed minutes. Hunt 2018: capping social media at ~30 min/day cut loneliness and depression.
FOCUS_SOCIAL = [(0, 1), (30, 1), (60, 0.6), (120, 0.25), (180, 0)]
# Unlocks a day. PNAS 2025: US adult median ~41; ~110 is a common problematic-use flag.
FOCUS_UNLOCKS = [(0, 1), (40, 1), (60, 0.75), (90, 0.45), (110, 0.3), (150, 0)]
# Phone minutes between midnight and 5am. Exelmans 2016: bedtime phone use -> worse sleep, more fatigue.
FOCUS_NIGHT = [(0, 1), (15, 0.75), (30, 0.55), (60, 0.3), (120, 0)]
# Total phone screen time, hours. Weakest evidence of the five, so the lowest weight.
FOCUS_SCREEN_HOURS = [(0, 1), (2, 1), (3, 0.8), (4, 0.6), (5, 0.4), (7, 0.1), (8, 0)]

# --- Health: eating, 7 days -------------------------------------------------
# A day is on target between 75% and 110% of the calorie target: below 75% is a crash diet, above is over.
CALORIE_BAND = (0.75, 1.10)
MEALS_A_DAY = 3
# Weekly weight change as % of body weight. Losing 0.5-1%/week keeps muscle (Helms et al. 2014);
# faster is scored a little lower, gaining while you mean to lose scores low.
WEIGHT_RATE_OK = (0.2, 1.0)

# --- Everything else -------------------------------------------------------
LEARNING_28D = [(0, 0), (14, 0.5), (28, 0.8), (56, 1)]  # study hours in 28 days
SOCIAL_WEEK = [(0, 0), (1, 0.35), (2, 0.6), (4, 0.9), (6, 1)]  # meaningful contacts/week


def grade(score):
    """Same F → SSS ladder the daily score uses"""
    for threshold, letter in ((95, 'SSS'), (90, 'SS'), (85, 'S'), (80, 'A+'), (75, 'A'),
                              (70, 'A-'), (60, 'B'), (50, 'C'), (40, 'D')):
        if score >= threshold:
            return letter
    return 'F'


def interp(x, points):
    """Piecewise-linear lookup through (x, y) points, flat beyond both ends"""
    if x <= points[0][0]:
        return points[0][1]
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        if x <= x1:
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    return points[-1][1]


def parse(day):
    return datetime.strptime(day, '%Y-%m-%d')


def last_dates(day, n):
    """The n dates ending at `day`, oldest first"""
    end = parse(day)
    return [(end - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(n - 1, -1, -1)]


def window(logs, day, n):
    """(date, entry) for the logged days among the n days ending at `day`"""
    return [(d, logs[d]) for d in last_dates(day, n) if d in logs]


def field(entry, section, key):
    return entry.get(section, {}).get(key)


def values(entries, section, key):
    return [v for _, e in entries if (v := field(e, section, key)) is not None]


def tracked_span(data, day, n):
    """Days of the last n that fall after tracking started, or None if nothing was tracked.
    Check-ins and logged meals mark the start; old push-up history only counts when there are neither."""
    dates = [d for d in [*data.get('daily_logs', {}), *data.get('meals', {})] if d <= day]
    if not dates:
        dates = [p['date'] for p in data['habits']['workout']['pushup_history'] if p['date'] <= day]
    if not dates:
        return None
    return min(n, (parse(day) - parse(min(dates))).days + 1)


def sleep_midpoint(sleep):
    """Minutes after noon of the sleep midpoint, so nights that cross midnight stay continuous"""
    if not sleep.get('bed') or sleep.get('hours') is None:
        return None
    h, m = map(int, sleep['bed'].split(':'))
    return (h * 60 + m + sleep['hours'] * 30 - 720) % 1440


def sleep_hours(bed, wake):
    """Hours between two HH:MM times, crossing midnight if needed"""
    to_min = lambda t: int(t[:2]) * 60 + int(t[3:])
    return round(((to_min(wake) - to_min(bed)) % 1440) / 60, 2)


def component(name, weight, score, note, missing='not logged'):
    return {'name': name, 'weight': weight, 'score': score, 'note': note if score is not None else missing}


def penalty(name, points, note):
    return {'name': name, 'points': round(points, 1), 'note': note}


def combine(components, penalties=(), ceiling=100, ceiling_note=''):
    """Weighted average of the known components, minus penalties, capped by the ceiling"""
    known = [c for c in components if c['score'] is not None]
    known_weight = sum(c['weight'] for c in known)
    total_weight = sum(c['weight'] for c in components)
    penalties = [p for p in penalties if p['points'] > 0]
    result = {
        'score': None,
        'components': components,
        'penalties': penalties,
        'ceiling': ceiling if ceiling < 100 else None,
        'ceiling_note': ceiling_note,
        'confidence': round(100 * known_weight / total_weight),
        'best_move': None,
    }
    if not known_weight:
        return result
    base = 100 * sum(c['weight'] * c['score'] for c in known) / known_weight
    result['score'] = round(max(0, min(ceiling, base - sum(p['points'] for p in penalties))))

    # Where the most points are waiting: an unfinished component or a penalty
    gains = [(100 * c['weight'] * (1 - c['score']) / known_weight, c['name']) for c in known]
    gains += [(p['points'], p['name']) for p in penalties]
    top = max(gains)
    if top[0] >= 1:
        result['best_move'] = {'name': top[1], 'points': round(top[0])}
    return result


def sleep_quality(sleep):
    """0-1 from a watch score or self-rating; otherwise estimated from known sleep disruptors"""
    if sleep.get('quality') is not None:
        return sleep['quality'] / 100, f"score {sleep['quality']:g}"
    if all(sleep.get(k) is None for k in ('alcohol', 'late_caffeine', 'screen_before_bed')):
        return None, ''
    quality, notes = 1.0, []
    drinks = sleep.get('alcohol') or 0
    if drinks >= 3:  # Ebrahim 2013: REM loss is dose-dependent
        quality -= 0.35
    elif drinks >= 1:
        quality -= 0.15
    if drinks:
        notes.append(f'{drinks} drinks')
    if sleep.get('late_caffeine'):  # Drake 2013: 6h before bed still costs >1h of sleep
        quality -= 0.2
        notes.append('late caffeine')
    if sleep.get('screen_before_bed'):  # Chang 2015: later clock, groggier morning
        quality -= 0.15
        notes.append('screen before bed')
    return max(quality, 0), ', '.join(notes) or 'no disruptors'


def mental_power(logs, day, sleep_need=SLEEP_NEED):
    """MP: how much focused mental work you had in you that day, and how well you used it"""
    entry = logs.get(day, {})
    sleep = entry.get('sleep', {})
    hours = sleep.get('hours')
    week = window(logs, day, 7)

    nights = values(week, 'sleep', 'hours')
    debt = sum(max(0, sleep_need - h) for h in nights) if len(nights) >= 3 else None
    mids = [m for _, e in week if (m := sleep_midpoint(e.get('sleep', {}))) is not None]
    spread = pstdev(mids) if len(mids) >= 4 else None
    quality, quality_note = sleep_quality(sleep)

    deep = field(entry, 'work', 'deep')
    total = field(entry, 'work', 'total')
    active_min = field(entry, 'body', 'active_min')
    steps = field(entry, 'body', 'steps')
    moves = []
    if active_min is not None:
        moves.append(min(1, active_min / 30))
    if steps is not None:
        moves.append(min(1, steps / 8000))
    outdoor = field(entry, 'body', 'outdoor_min')
    meditation = field(entry, 'mind', 'meditation_min')

    components = [
        component('Sleep last night', 25, None if hours is None else interp(hours, SLEEP_HOURS), f'{hours}h'),
        component('Sleep debt (7 days)', 10, None if debt is None else interp(debt, SLEEP_DEBT),
                  f'{debt:.1f}h owed over {len(nights)} nights' if debt is not None else ''),
        component('Sleep regularity', 8, None if spread is None else interp(spread, SLEEP_SPREAD),
                  f'bedtime drifts ±{spread:.0f} min' if spread is not None else ''),
        component('Sleep quality', 7, quality, quality_note),
        component('Deep work', 25, None if deep is None else interp(deep, DEEP_WORK), f'{deep}h focused'),
        component('Physical activity', 12, max(moves) if moves else None, f'{active_min or 0} min, {steps or 0} steps'),
        component('Outdoors', 8, None if outdoor is None else min(1, outdoor / 20), f'{outdoor} min'),
        component('Meditation', 5, None if meditation is None else min(1, meditation / 10), f'{meditation} min'),
    ]

    shorts = field(entry, 'screen', 'short_video_min') or 0
    long_video = field(entry, 'screen', 'long_video_min') or 0
    gaming = field(entry, 'screen', 'gaming_min') or 0
    week_work = sum(values(week, 'work', 'total'))
    penalties = [
        penalty('Reels / Shorts / TikTok', interp(shorts, SHORT_VIDEO), f'{shorts} min'),
        penalty('Passive video over 2h', min(6, max(0, (long_video - 120) / 20)), f'{long_video} min'),
        penalty('Gaming over 2h', min(6, max(0, (gaming - 120) / 20)), f'{gaming} min'),
        # Pencavel 2015: output per hour collapses past ~50h/week; Kivimäki 2015: 55h+ raises stroke risk
        penalty('Overwork today', min(12, max(0, 3 * ((total or 0) - 10))), f'{total}h worked'),
        penalty('Overwork this week', 6 if week_work > 55 else 3 if week_work > 50 else 0, f'{week_work:g}h in 7 days'),
    ]

    ceiling = 100 if hours is None else round(interp(hours, SLEEP_CEILING))
    return combine(components, penalties, ceiling, f'capped by {hours}h of sleep')


def pushup_counts(data):
    """date → push-ups, merging the workout habit history with check-ins (highest wins)"""
    counts = {}
    for p in data['habits']['workout']['pushup_history']:
        counts[p['date']] = max(counts.get(p['date'], 0), p['count'])
    for day, entry in data.get('daily_logs', {}).items():
        if (count := field(entry, 'body', 'pushups')) is not None:
            counts[day] = max(counts.get(day, 0), count)
    return counts


def physical_strength(data, day):
    """PS: max push-up test plus how often you train strength (WHO: 2+ days a week)"""
    logs = data.get('daily_logs', {})
    tests = values(window(logs, day, 60), 'body', 'max_pushups')
    span = tracked_span(data, day, 14)
    consistency, note = None, ''
    if span and span >= MIN_SPAN:
        counts = pushup_counts(data)
        sessions = sum(1 for d in last_dates(day, span)
                       if counts.get(d, 0) >= PUSHUP_SESSION or field(logs.get(d, {}), 'body', 'strength'))
        expected = 4 * span / 14
        consistency = interp(sessions / expected, [(0, 0), (1, 0.85), (2, 1)])
        note = f'{sessions} sessions in {span} days'
    return combine([
        component('Max push-up test', 60, interp(tests[-1], PUSHUP_TEST) if tests else None,
                  f'{tests[-1]} reps' if tests else '', 'do a max push-up test'),
        component('Training consistency', 40, consistency, note, f'needs {MIN_SPAN}+ days of tracking'),
    ])


def stamina(data, day):
    """STA: daily steps and weekly cardio minutes over the last 7 days"""
    week = window(data.get('daily_logs', {}), day, 7)
    steps = values(week, 'body', 'steps')
    steps = steps if len(steps) >= MIN_DAYS else None
    active = values(week, 'body', 'active_min')
    cardio = mean(active) * 7 if len(active) >= MIN_DAYS else None
    return combine([
        component('Steps (7-day avg)', 50, interp(mean(steps), STEPS) if steps else None,
                  f'{mean(steps):,.0f}/day' if steps else '', f'needs {MIN_DAYS}+ days'),
        component('Cardio minutes / week', 50, None if cardio is None else interp(cardio, CARDIO_WEEK),
                  f'{cardio:.0f} min' if cardio is not None else '', f'needs {MIN_DAYS}+ days'),
    ])


def intellect(data, day):
    """INT: hours of deliberate learning over the last 28 days"""
    learning = values(window(data.get('daily_logs', {}), day, 28), 'mind', 'learning_min')
    hours = mean(learning) * 28 / 60 if len(learning) >= MIN_DAYS else None
    return combine([
        component('Learning (28 days)', 100, None if hours is None else interp(hours, LEARNING_28D),
                  f'≈{hours:.0f}h' if hours is not None else '', f'needs {MIN_DAYS}+ days'),
    ])


def discipline(data, day, pushup_requirement):
    """DIS: how reliably you did what you said you'd do over the last 14 days"""
    span = tracked_span(data, day, 14)
    if not span or span < MIN_DAYS:
        return combine([component('Daily check-ins', 1, None, '', f'needs {MIN_DAYS}+ days')])
    logs = data.get('daily_logs', {})
    dates = last_dates(day, span)
    entries = window(logs, day, span)
    rate = lambda hits, total: hits / total if total else None

    nights = values(entries, 'sleep', 'hours')
    showers = values(entries, 'body', 'shower')
    counts = pushup_counts(data)
    meals = data.get('meals', {})
    meal_days = finished_meal_days(meals, dates, day)
    calories = data.get('nutrition', {}).get('calories')
    due = [t for t in data['todos'] if dates[0] <= t['deadline'] <= day]
    on_time = [t for t in due if t['completed'] and t.get('completion_date', '9999') <= t['deadline']]

    return combine([
        component('Daily check-ins', 1, rate(len(entries), span), f'{len(entries)}/{span} days'),
        component('Slept 7-9h', 1, rate(sum(7 <= h <= 9 for h in nights), len(nights)), f'{sum(7 <= h <= 9 for h in nights)}/{len(nights)} nights'),
        component(f'{pushup_requirement}+ push-ups', 1, rate(sum(counts.get(d, 0) >= pushup_requirement for d in dates), span),
                  f'{sum(counts.get(d, 0) >= pushup_requirement for d in dates)}/{span} days'),
        component('Showered', 1, rate(sum(showers), len(showers)), f'{sum(showers)}/{len(showers)} days'),
        component('Tasks done on time', 1, rate(len(on_time), len(due)), f'{len(on_time)}/{len(due)} tasks'),
        component('Ate within calories', 1, rate(sum(calorie_ok(m['kcal'], calories) for m in meal_days), len(meal_days)) if calories else None,
                  f"{sum(calorie_ok(m['kcal'], calories) for m in meal_days)}/{len(meal_days)} days"),
    ])


def focus(data, day):
    """FOC: phone habits over the last 7 days (reels, social feeds, unlocks, night use, total screen time)"""
    week = window(data.get('daily_logs', {}), day, 7)

    def average(key):
        found = values(week, 'screen', key)
        return mean(found) if len(found) >= MIN_DAYS else None

    def part(name, weight, key, curve, fmt):
        avg = average(key)
        return component(name, weight, None if avg is None else interp(avg, curve), fmt(avg) if avg is not None else '',
                         f'needs {MIN_DAYS}+ days of phone data')

    screen_min = average('total_min')
    return combine([
        part('Reels / Shorts / TikTok', 25, 'short_video_min', FOCUS_SHORT_VIDEO, lambda m: f'{m:.0f} min/day'),
        part('Social feeds', 20, 'social_min', FOCUS_SOCIAL, lambda m: f'{m:.0f} min/day'),
        part('Unlocks', 20, 'unlocks', FOCUS_UNLOCKS, lambda n: f'{n:.0f}/day'),
        part('Phone after midnight', 20, 'night_min', FOCUS_NIGHT, lambda m: f'{m:.0f} min/night'),
        component('Total screen time', 15, None if screen_min is None else interp(screen_min / 60, FOCUS_SCREEN_HOURS),
                  f'{screen_min / 60:.1f}h/day' if screen_min is not None else '', f'needs {MIN_DAYS}+ days of phone data'),
    ])


def calorie_ok(kcal, target):
    return target is not None and CALORIE_BAND[0] * target <= kcal <= CALORIE_BAND[1] * target


def finished_meal_days(meals, dates, day):
    """Days to judge eating on: today only counts once it's fully logged, so lunchtime isn't a 'failed' day."""
    return [meals[d] for d in dates if d in meals and (d != day or meals[d]['count'] >= MEALS_A_DAY)]


def health(data, day):
    """H: eating well for your goal over the last 7 days (calories on target, protein, logging, weight trend)"""
    meals = data.get('meals', {})
    targets = data.get('nutrition', {})
    calories, protein = targets.get('calories'), targets.get('protein')
    logged = finished_meal_days(meals, last_dates(day, 7), day)
    enough = len(logged) >= MIN_DAYS
    setup = 'add ' + ', '.join(targets.get('missing') or []) + ' in your profile' if targets.get('missing') else ''

    first = min(meals) if meals else None
    tracked = [d for d in last_dates(day, 7) if first and d >= first]
    logging = mean(min(1, meals.get(d, {}).get('count', 0) / MEALS_A_DAY) for d in tracked) if len(tracked) >= MIN_DAYS else None

    return combine([
        component('Calories on target', 40,
                  mean(calorie_ok(m['kcal'], calories) for m in logged) if enough and calories else None,
                  f"{sum(calorie_ok(m['kcal'], calories) for m in logged)}/{len(logged)} days near {calories} kcal" if calories else '',
                  setup or f'needs {MIN_DAYS}+ days of meals'),
        component('Protein', 25,
                  mean(min(1, m['protein'] / protein) for m in logged) if enough and protein else None,
                  f"{mean(m['protein'] for m in logged):.0f} / {protein} g a day" if logged and protein else '',
                  'needs a weight' if not protein else f'needs {MIN_DAYS}+ days of meals'),
        component('Meals logged', 20, logging, f'{MEALS_A_DAY} a day' if logging is not None else '',
                  f'needs {MIN_DAYS}+ days of meals'),
        component('Weight trend', 15, *weight_trend(data, day, targets.get('direction'))),
    ])


def weight_trend(data, day, direction):
    """(score, note, missing note) from this week's average weight against last week's."""
    logs = data.get('daily_logs', {})
    this_week = values(window(logs, day, 7), 'body', 'weight_kg')
    earlier = values([(d, logs[d]) for d in last_dates(day, 14)[:7] if d in logs], 'body', 'weight_kg')
    if not this_week or not earlier:
        return None, '', 'needs weigh-ins 2 weeks running'
    change = (mean(this_week) - mean(earlier)) / mean(earlier) * 100  # % of body weight per week
    toward = -change if direction == 'decrease' else change
    if direction is None:
        score = 1 if abs(change) < 0.5 else 0.5
    elif WEIGHT_RATE_OK[0] <= toward <= WEIGHT_RATE_OK[1]:
        score = 1
    elif toward > WEIGHT_RATE_OK[1]:
        score = 0.7  # faster than is healthy to keep up
    elif toward > 0:
        score = 0.6
    else:
        score = 0.1  # moving away from the goal
    return score, f'{change:+.1f}% this week', ''


def social(data, day):
    """SOC: meaningful contacts (30+ min, in person or call) per week. Holt-Lunstad 2010"""
    contacts = values(window(data.get('daily_logs', {}), day, 7), 'social', 'interactions')
    weekly = mean(contacts) * 7 if len(contacts) >= MIN_DAYS else None
    return combine([
        component('Meaningful contacts / week', 100, None if weekly is None else interp(weekly, SOCIAL_WEEK),
                  f'≈{weekly:.1f}' if weekly is not None else '', f'needs {MIN_DAYS}+ days'),
    ])


def wealth(data):
    """WLT: this month's earnings against the monthly goal"""
    income = data['income']
    goal, earned = income['monthly_goal'], income['current_month_earnings']
    currency = income.get('currency', 'Lari')
    return combine([
        component('Monthly income goal', 100, min(1, earned / goal) if goal else None, f'{earned:,} / {goal:,} {currency}'),
    ])


def customize(sheet, custom):
    """Applies a user's customization to their stats: parts they've turned off leave the average (the
    stat is judged on the rest; drains still count). The standard scores used for comparisons skip this."""
    for code, names in (custom or {}).get('off', {}).items():
        result = sheet.get(code)
        if not result or not names:
            continue
        kept = [c for c in result['components'] if c['name'] not in names]
        if not kept or len(kept) == len(result['components']):
            continue
        new = combine(kept, result['penalties'], result['ceiling'] or 100, result['ceiling_note'])
        new['off'] = [c['name'] for c in result['components'] if c['name'] in names]
        sheet[code] = new
    return sheet


def character_sheet(data, day, pushup_requirement=100, sleep_need=SLEEP_NEED, custom=None):
    """All stats for one day, their six categories, and an overall score averaged over the categories that have data"""
    logs = data.get('daily_logs', {})
    sheet = {
        'MP': mental_power(logs, day, sleep_need),
        'PS': physical_strength(data, day),
        'STA': stamina(data, day),
        'H': health(data, day),
        'INT': intellect(data, day),
        'DIS': discipline(data, day, pushup_requirement),
        'FOC': focus(data, day),
        'SOC': social(data, day),
        'WLT': wealth(data),
    }
    customize(sheet, custom)
    categories = category_scores({code: stat['score'] for code, stat in sheet.items()})
    scores = [score for score in categories.values() if score is not None]
    return {'stats': sheet, 'categories': categories, 'overall': round(mean(scores)) if scores else None}


def category_scores(stat_scores):
    """{category key: average of its stats that have data, or None}"""
    result = {}
    for key, _, codes in CATEGORIES:
        known = [stat_scores[code] for code in codes if stat_scores.get(code) is not None]
        result[key] = round(mean(known)) if known else None
    return result
