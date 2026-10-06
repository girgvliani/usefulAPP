"""The questionnaire: what matters to you, how you live now, what gets in your way, and your story.

From the answers the server works out
- your priorities: the six categories in the order you ranked them,
- your focus: the important categories where you're furthest behind (tracked scores when there are
  enough, otherwise an estimate from your answers),
- your plan: the changes that would move those most, each with a first step and the research behind it,
- your peer group (age, sex, build, fitness) for ranking you against people like you. Classes aren't
  public yet, so the peer group is stored but never sent to the apps.

Both apps render the questions from `catalog()`, so a new question only needs a change here.
"""

from datetime import date

from app.services import character_stats

CATEGORY_NAMES = {key: name for key, name, _ in character_stats.CATEGORIES}


def option(value, label):
    return {'value': value, 'label': label}


def choices(*pairs):
    return [option(v, l) for v, l in pairs]


# kind: single / multi (max picks) / scale (1-5) / number (min, max, unit) / rank (order every option) / text
# optional: may be skipped. prefill: filled from what the server already knows about you.
SECTIONS = [
    {
        'key': 'you', 'title': 'About you', 'intro': 'The basics. Used to compare you with people like you, never shown to others.',
        'questions': [
            {'id': 'birth_year', 'text': 'What year were you born?', 'kind': 'number', 'min': 1920, 'max': 2015, 'prefill': True},
            {'id': 'sex', 'text': 'Sex', 'kind': 'single', 'options': choices(('male', 'Male'), ('female', 'Female')), 'prefill': True},
            {'id': 'height_cm', 'text': 'Height', 'kind': 'number', 'unit': 'cm', 'min': 100, 'max': 250, 'prefill': True},
            {'id': 'weight_kg', 'text': 'Weight', 'kind': 'number', 'unit': 'kg', 'min': 30, 'max': 300, 'prefill': True},
            {'id': 'daily_activity', 'text': 'What does a normal day look like?', 'kind': 'single', 'options': choices(
                ('desk', 'Sitting most of the day'), ('mixed', 'Some sitting, some moving'),
                ('feet', 'On my feet most of the day'), ('physical', 'Physical work'))},
            {'id': 'fitness', 'text': 'How fit are you right now?', 'kind': 'single', 'options': choices(
                ('low', "I'd struggle to jog 1 km"), ('some', 'I can jog 1-3 km'), ('fit', 'I can run 5 km'),
                ('trained', 'I train regularly / run 10 km+'), ('athlete', 'I compete in a sport'))},
            {'id': 'pushups_max', 'text': 'How many push-ups can you do in one go?', 'kind': 'number', 'min': 0, 'max': 500, 'optional': True},
        ],
    },
    {
        'key': 'matters', 'title': 'What matters to you', 'intro': 'Your plan puts these first.',
        'questions': [
            {'id': 'priorities', 'text': 'Put these in order: most important to you first', 'kind': 'rank',
             'options': [option(key, name) for key, name, _ in character_stats.CATEGORIES]},
            {'id': 'main_goal', 'text': 'If one thing changed in the next 3 months, what should it be?', 'kind': 'single', 'options': choices(
                ('lose_weight', 'Lose weight'), ('fitter', 'Get stronger and fitter'), ('energy', 'More energy and focus'),
                ('money', 'Earn more'), ('learn', 'Learn a skill'), ('people', 'Better relationships'),
                ('discipline', 'Stop procrastinating, build habits'))},
            {'id': 'why', 'text': 'Why does it matter? (up to 2)', 'kind': 'multi', 'max': 2, 'options': choices(
                ('health', 'Health and a long life'), ('looks', 'Look and feel better'), ('career', 'Career and money'),
                ('family', 'My family'), ('prove', 'To prove it to myself'), ('calm', 'Peace of mind'))},
        ],
    },
    {
        'key': 'now', 'title': 'Your life now', 'intro': 'Be honest; nobody else sees this, and the plan is only as good as the answers.',
        'questions': [
            {'id': 'sleep_hours', 'text': 'How long do you usually sleep?', 'kind': 'single', 'options': choices(
                ('lt5', 'Under 5 h'), ('5_6', '5-6 h'), ('6_7', '6-7 h'), ('7_8', '7-8 h'), ('8_9', '8-9 h'), ('gt9', 'Over 9 h'))},
            {'id': 'bedtime', 'text': 'Your bedtime is…', 'kind': 'single', 'options': choices(
                ('regular', 'The same within half an hour'), ('drifts', 'Within an hour or two'), ('random', 'All over the place'))},
            {'id': 'phone_hours', 'text': 'Phone screen time on a normal day', 'kind': 'single', 'options': choices(
                ('lt2', 'Under 2 h'), ('2_4', '2-4 h'), ('4_6', '4-6 h'), ('gt6', 'Over 6 h'))},
            {'id': 'short_video', 'text': 'Reels, Shorts or TikTok a day', 'kind': 'single', 'options': choices(
                ('none', 'None'), ('lt30', 'Under 30 min'), ('30_60', '30-60 min'), ('1_2h', '1-2 h'), ('gt2h', 'Over 2 h'))},
            {'id': 'exercise_days', 'text': 'Days a week you exercise', 'kind': 'single', 'options': choices(
                ('0', 'None'), ('1_2', '1-2'), ('3_4', '3-4'), ('5', '5 or more'))},
            {'id': 'work_hours', 'text': 'Hours of work or study a day', 'kind': 'single', 'options': choices(
                ('lt4', 'Under 4'), ('4_6', '4-6'), ('6_8', '6-8'), ('8_10', '8-10'), ('gt10', 'Over 10'))},
            {'id': 'deep_work', 'text': 'Of that, truly focused (no phone, one task)', 'kind': 'single', 'options': choices(
                ('none', 'Almost none'), ('lt1', 'Under 1 h'), ('1_2', '1-2 h'), ('2_4', '2-4 h'), ('gt4', 'Over 4 h'))},
            {'id': 'learning', 'text': 'Learning something new (books, courses, practice) a week', 'kind': 'single', 'options': choices(
                ('none', 'None'), ('lt1', 'Under 1 h'), ('1_3', '1-3 h'), ('3_7', '3-7 h'), ('gt7', 'Over 7 h'))},
            {'id': 'social', 'text': 'Real conversations (30+ min, in person or a call) a week', 'kind': 'single', 'options': choices(
                ('0', 'None'), ('1_2', '1-2'), ('3_5', '3-5'), ('6', '6 or more'))},
            {'id': 'eating', 'text': 'How do you mostly eat?', 'kind': 'single', 'options': choices(
                ('home', 'Mostly home-cooked'), ('mixed', 'A mix'), ('fast', 'Mostly fast food or snacks'), ('irregular', 'Irregular, I skip meals'))},
            {'id': 'alcohol', 'text': 'Alcoholic drinks a week', 'kind': 'single', 'options': choices(
                ('0', 'None'), ('1_3', '1-3'), ('4_10', '4-10'), ('gt10', 'More than 10'))},
            {'id': 'money', 'text': 'Your money right now', 'kind': 'single', 'options': choices(
                ('stressed', "Tight; it stresses me"), ('ok', 'Getting by'), ('saving', "I save every month"))},
            {'id': 'stress', 'text': 'How stressed are you most days?', 'kind': 'scale', 'min_label': 'Calm', 'max_label': 'Very stressed'},
            {'id': 'energy', 'text': 'Your energy most days', 'kind': 'scale', 'min_label': 'Drained', 'max_label': 'Full of energy'},
        ],
    },
    {
        'key': 'obstacles', 'title': 'What gets in your way', 'intro': 'So the plan works around it instead of against it.',
        'questions': [
            {'id': 'obstacles', 'text': 'What stops you most? (up to 3)', 'kind': 'multi', 'max': 3, 'options': choices(
                ('phone', 'Phone and social media'), ('time', 'No time'), ('tired', 'Low energy, tired'),
                ('motivation', 'No motivation'), ('stress', 'Stress or anxiety'), ('schedule', 'Irregular schedule'),
                ('no_plan', "Don't know where to start"), ('health', 'Injury or health'), ('money', 'Money'))},
            {'id': 'chronotype', 'text': 'When are you at your best?', 'kind': 'single', 'options': choices(
                ('morning', 'Mornings'), ('evening', 'Evenings and nights'), ('neither', 'No real difference'))},
            {'id': 'what_works', 'text': 'What has kept you going before? (up to 2)', 'kind': 'multi', 'max': 2, 'options': choices(
                ('streaks', 'Streaks and tracking'), ('pushed', 'Someone pushing me hard'), ('rewards', 'Rewards'),
                ('people', 'Doing it with others'), ('small_steps', 'A clear plan, small steps'))},
        ],
    },
    {
        'key': 'story', 'title': 'Your story', 'intro': "What you've already done says a lot about what you can do next.",
        'questions': [
            {'id': 'milestones', 'text': 'Which of these have you done? (any)', 'kind': 'multi', 'options': choices(
                ('degree', 'Finished school or university'), ('sport', 'Played a sport for 2+ years'),
                ('race', 'Ran a race (5 km or more)'), ('language', 'Learned a second language'),
                ('job', 'Held a job for 2+ years'), ('built', 'Built a project or business'),
                ('weight', 'Lost or gained 10+ kg on purpose'), ('recovered', 'Came back from a long illness or injury'),
                ('none', 'None of these yet'))},
            {'id': 'best_shape', 'text': 'When were you in your best shape?', 'kind': 'single', 'options': choices(
                ('now', 'Right now'), ('1_2y', '1-2 years ago'), ('3_5y', '3-5 years ago'), ('gt5y', 'More than 5 years ago'), ('never', 'Not yet'))},
            {'id': 'tried', 'text': 'What have you tried before? (any)', 'kind': 'multi', 'options': choices(
                ('gym', 'A gym membership'), ('diet', 'A diet'), ('apps', 'Habit or tracking apps'), ('journal', 'Journaling'),
                ('meditation', 'Meditation'), ('none', 'Nothing like this'))},
            {'id': 'proudest', 'text': "What's the thing you're proudest of so far?", 'kind': 'text', 'optional': True, 'max': 300},
        ],
    },
]

QUESTIONS = {q['id']: q for section in SECTIONS for q in section['questions']}


def catalog() -> dict:
    return {'sections': SECTIONS}


class AnswerError(ValueError):
    """An answer the questionnaire can't use; the message says which question and why."""


def validate(answers: dict) -> dict:
    """The answers, checked and cleaned; raises AnswerError for anything missing or out of range."""
    clean = {}
    for qid, q in QUESTIONS.items():
        value = answers.get(qid)
        if value in (None, '', []):
            if q.get('optional'):
                continue
            raise AnswerError(f"Answer '{q['text']}'")
        values = [o['value'] for o in q.get('options', [])]
        kind = q['kind']
        if kind == 'single':
            if value not in values:
                raise AnswerError(f"'{q['text']}': pick one of the options")
        elif kind == 'multi':
            if not isinstance(value, list) or not value or any(v not in values for v in value) or len(set(value)) != len(value):
                raise AnswerError(f"'{q['text']}': pick from the options")
            if 'max' in q and len(value) > q['max']:
                raise AnswerError(f"'{q['text']}': pick at most {q['max']}")
            if 'none' in value and len(value) > 1:
                value = ['none']
        elif kind == 'rank':
            if not isinstance(value, list) or sorted(value) != sorted(values):
                raise AnswerError(f"'{q['text']}': put every option in order")
        elif kind == 'scale':
            if not isinstance(value, int) or not 1 <= value <= 5:
                raise AnswerError(f"'{q['text']}': pick 1 to 5")
        elif kind == 'number':
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not q['min'] <= value <= q['max']:
                raise AnswerError(f"'{q['text']}': a number from {q['min']} to {q['max']}")
        elif kind == 'text':
            value = str(value).strip()[:q.get('max', 300)]
        clean[qid] = value
    return clean


# ---- What the answers say ---------------------------------------------------------------------

# Rough 0-100 starting points per category from the answers alone, for focus areas before there's
# tracked data. Same direction as the formulas, deliberately coarse.
# Typical daily steps by kind of day, as a goal's starting point until the phone has synced real ones
STEPS_GUESS = {'desk': 4000, 'mixed': 6000, 'feet': 9000, 'physical': 11000}
SLEEP_HOURS_MID = {'lt5': 4.5, '5_6': 5.5, '6_7': 6.5, '7_8': 7.5, '8_9': 8.5, 'gt9': 9.5}
SLEEP_POINTS = {'lt5': 20, '5_6': 45, '6_7': 65, '7_8': 90, '8_9': 90, 'gt9': 70}
REELS_POINTS = {'none': 100, 'lt30': 80, '30_60': 55, '1_2h': 35, 'gt2h': 15}
PHONE_POINTS = {'lt2': 95, '2_4': 75, '4_6': 50, 'gt6': 25}
DEEP_POINTS = {'none': 10, 'lt1': 35, '1_2': 60, '2_4': 85, 'gt4': 95}
EXERCISE_POINTS = {'0': 20, '1_2': 50, '3_4': 80, '5': 95}
FITNESS_POINTS = {'low': 20, 'some': 45, 'fit': 65, 'trained': 85, 'athlete': 95}
EATING_POINTS = {'home': 85, 'mixed': 60, 'fast': 30, 'irregular': 35}
LEARNING_POINTS = {'none': 10, 'lt1': 35, '1_3': 60, '3_7': 85, 'gt7': 95}
SOCIAL_POINTS = {'0': 15, '1_2': 50, '3_5': 85, '6': 95}
MONEY_POINTS = {'stressed': 30, 'ok': 60, 'saving': 85}
BEDTIME_POINTS = {'regular': 90, 'drifts': 60, 'random': 30}


def estimates(a: dict) -> dict:
    """{category: rough 0-100} from the answers alone"""
    avg = lambda *xs: round(sum(xs) / len(xs))
    return {
        'mental': avg(SLEEP_POINTS[a['sleep_hours']], REELS_POINTS[a['short_video']], PHONE_POINTS[a['phone_hours']],
                      DEEP_POINTS[a['deep_work']], 20 * (6 - a['stress'])),
        'physical': avg(EXERCISE_POINTS[a['exercise_days']], FITNESS_POINTS[a['fitness']], EATING_POINTS[a['eating']]),
        'practical': MONEY_POINTS[a['money']],
        'cultural': LEARNING_POINTS[a['learning']],
        'discipline': avg(BEDTIME_POINTS[a['bedtime']], EXERCISE_POINTS[a['exercise_days']], 100 - 15 * len(
            [o for o in a['obstacles'] if o in ('motivation', 'no_plan', 'phone', 'schedule')])),
        'social': SOCIAL_POINTS[a['social']],
    }


def bmi(a: dict) -> float:
    return a['weight_kg'] / (a['height_cm'] / 100) ** 2


def cohort(a: dict, today: date) -> dict:
    """Your peer group for ranking against people like you. Stored only: classes aren't public yet."""
    age = today.year - a['birth_year']
    age_band = next(label for limit, label in ((18, 'under 18'), (30, '18-29'), (40, '30-39'), (50, '40-49'), (60, '50-59')) if age < limit) \
        if age < 60 else '60+'
    b = bmi(a)
    build = 'light' if b < 18.5 else 'medium' if b < 25 else 'heavy' if b < 30 else 'very heavy'
    level = {'low': 'beginner', 'some': 'beginner', 'fit': 'intermediate', 'trained': 'advanced', 'athlete': 'elite'}[a['fitness']]
    return {'age_band': age_band, 'sex': a['sex'], 'build': build, 'fitness': level,
            'key': f"{a['sex']}|{age_band}|{build}|{level}"}


# A change worth making: when it applies, which category it moves, how much (1-3), and what to do.
# goal: a goal the apps can create in one tap (types as in /goals). Sources match the stat formulas.
RULES = [
    ('sleep', 'mental', 3, lambda a: a['sleep_hours'] in ('lt5', '5_6', '6_7'),
     'Sleep 7-9 hours',
     'Two weeks of 6-hour nights cost as much focus as a night without sleep, and you stop noticing it (Van Dongen 2003).',
     'Set an alarm for bedtime, 8 hours before you need to get up.', {'type': 'sleep', 'target_value': 8}),
    ('bedtime', 'mental', 2, lambda a: a['bedtime'] != 'regular',
     'Go to bed at the same time every night',
     'Regular sleep predicts health better than how long you sleep (Windred 2024).',
     'Pick a bedtime you can keep on weekends too, and keep it within 30 minutes.', None),
    ('reels', 'mental', 3, lambda a: a['short_video'] in ('30_60', '1_2h', 'gt2h'),
     'Cut reels and shorts to under 15 minutes',
     'Heavy short-video use goes with worse attention and self-control (Nguyen 2025 meta-analysis).',
     'Turn on Goggins mode for your goal at level 8: the phone warns you when you open them.', None),
    ('phone', 'mental', 2, lambda a: a['phone_hours'] in ('4_6', 'gt6'),
     'Get your screen time under 3 hours',
     'Your phone hours come straight out of sleep, focus and people.',
     'Charge the phone outside the bedroom and turn off every notification that is not from a person.', None),
    ('deep_work', 'mental', 2, lambda a: a['deep_work'] in ('none', 'lt1') and a['work_hours'] != 'lt4',
     'One 90-minute focus block a day',
     'About 4 hours of real concentration a day is the most anyone sustains (Ericsson 1993); most people get under one.',
     'Block 90 minutes at your best time of day, phone in another room, one task.', None),
    ('stress', 'mental', 2, lambda a: a['stress'] >= 4,
     'Ten minutes of meditation a day',
     'Mindfulness practice measurably improves attention in healthy adults (meta-analysis of RCTs).',
     'Ten minutes after waking, before the phone.', None),
    ('exercise', 'physical', 3, lambda a: a['exercise_days'] in ('0', '1_2'),
     'Two strength sessions a week',
     'People who can do 40+ push-ups have far fewer heart problems than those who can do under 10 (Yang 2019).',
     'Two 20-minute sessions: push-ups, squats, rows. Test your max push-ups now and again in a month.',
     {'type': 'max_pushups', 'target_value_from': 'pushups_max'}),
    ('steps', 'physical', 2, lambda a: a['daily_activity'] == 'desk',
     'Walk 8,000 steps a day',
     'Benefits rise steeply up to 8,000-10,000 steps a day (Paluch 2022).',
     'A 30-minute walk after lunch or dinner covers half of it.', {'type': 'steps', 'target_value': 8000}),
    ('weight', 'physical', 3, lambda a: a['main_goal'] == 'lose_weight' or bmi(a) >= 30,
     'Lose weight at 0.5-1% a week',
     'Faster than that costs muscle (Helms 2014). A 500 kcal daily deficit gets you there.',
     'Photo-log every meal for two weeks: the app sets your calorie target from your body and steps.',
     {'type': 'weight', 'target_value_from': 'weight_loss'}),
    ('eating', 'physical', 2, lambda a: a['eating'] in ('fast', 'irregular'),
     'Three regular meals with protein',
     'Hitting 1.6 g of protein per kg keeps muscle while you change everything else (Morton 2018).',
     'Same three meal times every day; log them so you see the pattern.', None),
    ('alcohol', 'physical', 2, lambda a: a['alcohol'] in ('4_10', 'gt10'),
     'Keep alcohol to 3 drinks a week or fewer',
     'Even moderate drinking fragments sleep in the second half of the night (Ebrahim 2013).',
     'Pick two days a week that can have a drink; the others are dry.', None),
    ('learning', 'cultural', 2, lambda a: a['learning'] in ('none', 'lt1'),
     'Learn 20 minutes a day',
     'Skills compound: 20 minutes a day is 120 hours a year.',
     'Pick one book or course and do 20 minutes before your phone in the evening.',
     {'type': 'custom', 'title': 'Read 12 books', 'unit': 'books', 'target_value': 12, 'start_value': 0}),
    ('social', 'social', 2, lambda a: a['social'] in ('0', '1_2'),
     'Three real conversations a week',
     'Strong relationships matter for survival about as much as quitting smoking (Holt-Lunstad 2010).',
     'Put one call or meet-up in your calendar for this week, then make it a standing one.', None),
    ('money', 'practical', 2, lambda a: a['money'] == 'stressed' or a['main_goal'] == 'money',
     'Set a monthly income goal and track it',
     "What you don't measure drifts; Wealth tracks your month against your goal.",
     'Add your monthly income goal in your profile and log each paid project.', None),
    ('plan', 'discipline', 2, lambda a: 'no_plan' in a['obstacles'] or a['main_goal'] == 'discipline',
     'One goal, three quests a week',
     'Small, specific next steps beat big intentions.',
     'Make your main goal in the app, then add three quests for this week.', None),
    ('checkin', 'discipline', 2, lambda a: 'motivation' in a['obstacles'] or 'schedule' in a['obstacles'],
     'Do the 30-second check-in every evening',
     'A daily check-in turns intentions into a streak you can see.',
     'Same time every evening; the widget shows your streak so you notice before it breaks.', None),
]

#: Points by importance rank (1st ... 6th), so a change in your top category outranks a bigger one you don't care about
RANK_WEIGHT = [6, 5, 4, 3, 2, 1]


def results(a: dict, tracked: dict, today: date) -> dict:
    """priorities, focus areas and the plan; `tracked` = {category: score or None} from the character sheet."""
    order = a['priorities']
    weight = {key: RANK_WEIGHT[i] for i, key in enumerate(order)}
    guess = estimates(a)
    level = {key: tracked.get(key) if tracked.get(key) is not None else guess[key] for key in order}

    # Where an important area is furthest behind: importance x room to grow
    need = {key: weight[key] * (100 - level[key]) for key in order}
    focus = sorted(order[:4], key=lambda key: -need[key])[:3]

    plan = []
    for rid, category, impact, applies, title, why, first_step, goal in RULES:
        if not applies(a):
            continue
        g = dict(goal) if goal else None
        source = g.pop('target_value_from', None) if g else None
        if source == 'pushups_max':
            # Starts from your answer; without one the goal waits for a logged max-push-up test
            if a.get('pushups_max') is None:
                g = None
            else:
                g.update(start_value=a['pushups_max'], target_value=max(20, a['pushups_max'] + 10))
        elif source == 'weight_loss':
            g.update(start_value=a['weight_kg'], target_value=round(a['weight_kg'] * 0.95, 1))  # 5% first: a target you can see coming
        elif g and g['type'] == 'sleep':
            g['start_value'] = SLEEP_HOURS_MID[a['sleep_hours']]
        elif g and g['type'] == 'steps':
            g['start_value'] = STEPS_GUESS[a['daily_activity']]
        plan.append({
            'id': rid, 'category': category, 'category_name': CATEGORY_NAMES[category],
            'title': title, 'why': why, 'first_step': first_step, 'goal': g,
            # How much it moves, how much you care, and how far behind you are there (an area you're
            # already strong in still counts a little)
            'score': impact * weight[category] * max(0.25, (100 - level[category]) / 100),
        })
    plan.sort(key=lambda r: -r['score'])
    # Every focus area gets its best step first, then the rest by score
    leads = [next(r for r in plan if r['category'] == key) for key in focus if any(r['category'] == key for r in plan)]
    plan = sorted(leads, key=lambda r: -r['score']) + [r for r in plan if r not in leads]

    # Leaning into what has worked for you before
    tips = []
    works = a['what_works']
    if 'pushed' in works:
        tips.append('You respond to pressure: set your main goal to Goggins level 8 or higher.')
    if 'streaks' in works:
        tips.append('Streaks work for you: add the home-screen widget so a breaking streak is the first thing you see.')
    if 'people' in works:
        tips.append('You do better with others: tell one person your goal and send them your weekly progress.')
    if 'small_steps' in works:
        tips.append('Small steps work for you: start with only the first change below for a week, then add the next.')
    if 'rewards' in works:
        tips.append('Rewards work for you: pick one for every level you reach.')
    if a['chronotype'] == 'evening':
        tips.append("You're an evening person: put your focus block in the afternoon and protect your wind-down instead of forcing early mornings.")
    elif a['chronotype'] == 'morning':
        tips.append("You're a morning person: do the hardest thing before noon.")

    return {
        'priorities': [{'key': key, 'name': CATEGORY_NAMES[key], 'level': level[key], 'tracked': tracked.get(key) is not None}
                       for key in order],
        'focus': focus,
        'plan': plan[:6],
        'tips': tips,
        'cohort': cohort(a, today),  # stored, never sent: classes aren't public yet
    }
