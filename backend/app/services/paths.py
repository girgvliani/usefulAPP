"""Paths: who you want to become (design: usefulAPP-expo/docs/PATHS-DESIGN.md).

A path brings its own sub-classes into the six classes, built on one principle: work hard (volume and
consistency) and be smart (method, strategy, reflection). It has a level and a title from path XP:

- 10 XP each day a daily sub-class is on target, 40 XP each week (Monday to Sunday) a weekly one is;
- each story chapter's XP once reached.

Only days on the path count: from the day it started to the day you leave (XP earned stays).
Switching one of its sub-classes off stops it earning. Targets start from your own last two weeks where the app has
data, and adjust once a week: hit 85%+ of the time → 10% harder, 40% or less → 10% easier.
"""
from dataclasses import dataclass, field as dc_field
from datetime import date, timedelta
from statistics import mean

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import SubClass, User, UserPath
from app.services import character_stats, profiles, sub_classes

MAX_CALLINGS = 3  # family roles don't count: a scientist is also a son
DAY_XP = 10
RATED_DAY_XP = 5  # a self-rating on target (4 or 5 out of 5) earns half: it can't be checked
WEEK_XP = 40
RAISE, LOWER = 1.10, 0.90


@dataclass(frozen=True)
class Sub:
    key: str
    half: str  # work / smart
    class_key: str
    name: str
    icon: str
    kind: str  # number / yesno / rating / field (sub_classes.KINDS)
    target: float
    period: str = "day"
    unit: str | None = None
    field: str | None = None
    better: str = "more"
    why: str = ""
    source: str | None = None


@dataclass(frozen=True)
class Chapter:
    key: str
    name: str
    how: str
    rule: str  # total / best_week / streak / days
    sub: str  # the sub-class it reads
    target: float
    xp: int


@dataclass(frozen=True)
class Path:
    key: str
    name: str
    icon: str
    blurb: str
    subs: tuple[Sub, ...]
    chapters: tuple[Chapter, ...]
    titles: tuple[tuple[int, str], ...] = dc_field(default=())
    group: str = "calling"  # calling (up to three) / parent / child (one of each at a time)


SCIENTIST = Path(
    "scientist", "Scientist", "🔬",
    "Work hard at the bench and the desk; be smart about how you learn and what you ask.",
    subs=(
        Sub("deep_work", "work", "mental", "Deep work", "🧠", "field", 3, field="work.deep", unit="h",
            why="Hours of full concentration are the raw material of expertise; about four a day is what experts sustain.",
            source="Ericsson, Krampe & Tesch-Römer, 1993"),
        Sub("literature", "work", "cultural", "Reading the literature", "📄", "number", 3, period="week", unit="papers",
            why="Knowing what has been done keeps you from reinventing it, and it's where new questions come from."),
        Sub("writing", "work", "discipline", "Daily writing", "✍️", "number", 30, unit="min",
            why="Researchers who wrote a little every day produced several times more than those who waited for big free blocks.",
            source="Boice, 1989"),
        Sub("output", "work", "practical", "Experiments and output", "🧪", "number", 2, period="week", unit="done",
            why="Finished experiments, analyses and write-ups are what moves science forward."),
        Sub("retrieval", "smart", "mental", "Retrieval practice", "🔁", "number", 20, unit="reviews",
            why="Testing yourself beats re-reading for long-term memory, and spacing the reviews out helps even more.",
            source="Roediger & Karpicke, 2006; Cepeda et al., 2006"),
        Sub("questions", "smart", "cultural", "Questions and hypotheses", "❓", "number", 3, period="week", unit="logged",
            why="Good science starts with good questions: write them down, then test them."),
        Sub("teaching", "smart", "social", "Explaining and teaching", "🎓", "number", 2, period="week", unit="times",
            why="Explaining an idea to someone else shows you the gaps in your own understanding (the protégé effect).",
            source="Nestojko et al., 2014"),
    ),
    chapters=(
        Chapter("first_experiment", "First experiment", "Log your first finished experiment, analysis or write-up.", "total", "output", 1, 50),
        Chapter("writing_week", "A week of writing", "Write every day for 7 days in a row.", "streak", "writing", 7, 75),
        Chapter("first_papers", "Ten papers", "Read 10 papers or chapters.", "total", "literature", 10, 100),
        Chapter("first_teaching", "Explain it", "Explain your work to someone outside your field.", "total", "teaching", 1, 50),
        Chapter("deep_week", "A 20-hour deep week", "Put in 20 hours of deep work in one week.", "best_week", "deep_work", 20, 200),
        Chapter("questions_50", "Fifty questions", "Log 50 questions or hypotheses.", "total", "questions", 50, 150),
        Chapter("writing_month", "30 days of writing", "Write every day for 30 days in a row.", "streak", "writing", 30, 300),
        Chapter("reviews_1000", "A thousand reviews", "Do 1,000 self-test reviews.", "total", "retrieval", 1000, 250),
    ),
    titles=((0, "Curious Mind"), (3, "Lab Apprentice"), (6, "Hypothesis Hunter"), (10, "Researcher"),
            (15, "Principal Investigator"), (25, "Luminary")),
)

BUSINESSMAN = Path(
    "businessman", "Businessman", "💼",
    "Work hard at selling and shipping; be smart about money, decisions and people.",
    subs=(
        Sub("revenue_work", "work", "practical", "Revenue work", "💰", "number", 4, unit="h",
            why="Hours on work that earns money. Everything else is busywork."),
        Sub("outreach", "work", "social", "Sales and outreach", "📞", "number", 10, period="week", unit="contacts",
            why="Results follow pipeline activity: calls, messages, proposals."),
        Sub("shipping", "work", "practical", "Shipping", "🚀", "number", 1, period="week", unit="shipped",
            why="A finished offer, release or deliverable beats a perfect plan."),
        Sub("customers", "work", "social", "Customer conversations", "🗣️", "number", 3, period="week", unit="talks",
            why="Ask about their life, not your idea, to learn what people really need.",
            source="Fitzpatrick, The Mom Test"),
        Sub("decisions", "smart", "mental", "Decision journal", "⚖️", "number", 3, period="week", unit="decisions",
            why="Write down a decision and what you expect; later you can judge the decision itself, not the luck.",
            source="Duke, Thinking in Bets; Kahneman, Thinking, Fast and Slow"),
        Sub("money", "smart", "practical", "Money check", "📊", "yesno", 1, period="week",
            why="Know your cash, costs and runway every week; most businesses die of running out of cash."),
        Sub("experiments", "smart", "cultural", "Experiments", "🧪", "number", 1, period="week", unit="tests",
            why="Test an idea cheaply with a clear yes or no before you build it."),
        Sub("network", "smart", "social", "Network", "🤝", "number", 2, period="week", unit="people",
            why="Opportunities come through people: meet someone new or renew a contact."),
        Sub("craft", "smart", "cultural", "Learning the craft", "📚", "number", 20, unit="min",
            why="Books and case studies: other people's mistakes are the cheapest lessons."),
    ),
    chapters=(
        Chapter("first_ship", "First thing shipped", "Ship an offer, a release or a deliverable.", "total", "shipping", 1, 75),
        Chapter("customers_10", "Ten conversations", "Have 10 customer conversations.", "total", "customers", 10, 100),
        Chapter("money_8", "Eight money checks", "Check your numbers 8 weeks.", "total", "money", 8, 150),
        Chapter("pipeline_week", "A 20-contact week", "Reach out to 20 people in one week.", "best_week", "outreach", 20, 150),
        Chapter("decisions_30", "Thirty decisions", "Journal 30 decisions.", "total", "decisions", 30, 150),
        Chapter("network_25", "Twenty-five people", "Meet or renew 25 contacts.", "total", "network", 25, 200),
        Chapter("revenue_100", "A hundred hours", "Put in 100 hours of revenue work.", "total", "revenue_work", 100, 250),
    ),
    titles=((0, "Side Hustler"), (3, "Deal Seeker"), (6, "Operator"), (10, "Founder"), (15, "Executive"), (25, "Tycoon")),
)

# ---- Family roles: four on purpose. Sons and daughters, fathers and mothers tend to face different gaps
# (see each "why"), so their defaults differ. Everything stays editable.

FATHER = Path(
    "father", "Father", "👨‍👧",
    "Be there and be engaged: play, teach, share the load at home and stay calm.",
    subs=(
        Sub("engaged_time", "work", "social", "One-to-one time", "🧒", "number", 30, unit="min",
            why="Active, engaged fathering is linked to better social, behavioural and school outcomes for children.",
            source="Sarkadi et al., 2008 (review)"),
        Sub("play", "work", "physical", "Play and adventure", "⚽", "number", 3, period="week", unit="times",
            why="Active, rough-and-tumble and outdoor play builds children's confidence and self-control.",
            source="Paquette, 2004"),
        Sub("fair_share", "work", "practical", "Fair share at home", "🧺", "number", 2, unit="tasks",
            why="Most of the planning and the household 'mental load' still falls on mothers; carrying your share is part of fathering.",
            source="Daminger, 2019"),
        Sub("present", "smart", "discipline", "Present, not on the phone", "📵", "yesno", 1,
            why="Phone use during family time ('technoference') goes with more acting out from children.",
            source="McDaniel & Radesky, 2018"),
        Sub("calm", "smart", "discipline", "Calm under pressure", "🧘", "rating", 0,
            why="Staying calm, and repairing after you lose it, teaches children to handle their own feelings.",
            source="Gottman, emotion coaching"),
        Sub("teaching", "smart", "cultural", "Teaching skills", "🛠️", "number", 2, period="week", unit="times",
            why="Teaching a skill (cooking, fixing, a sport) builds their competence and your bond."),
    ),
    chapters=(
        Chapter("time_week", "A week together", "Have one-to-one time 7 days in a row.", "streak", "engaged_time", 7, 75),
        Chapter("adventures_10", "Ten adventures", "Play or go on 10 adventures together.", "total", "play", 10, 100),
        Chapter("calm_week", "A calm week", "Rate yourself 4 or 5 for calm 7 days in a row.", "streak", "calm", 7, 100),
        Chapter("present_20", "Twenty present days", "Keep family time phone-free on 20 days.", "days", "present", 20, 150),
        Chapter("share_50", "Fifty tasks", "Do 50 tasks at home.", "total", "fair_share", 50, 150),
        Chapter("skills_10", "Ten skills", "Teach 10 skills.", "total", "teaching", 10, 150),
    ),
    titles=((0, "Father"), (3, "Steady Hand"), (6, "Everyday Hero"), (10, "The Rock"), (15, "Legacy Builder"), (25, "Patriarch")),
    group="parent",
)

MOTHER = Path(
    "mother", "Mother", "👩‍👧",
    "Connect, read together, share the load and look after yourself too.",
    subs=(
        Sub("connected_time", "work", "social", "One-to-one time", "🧒", "number", 30, unit="min",
            why="Undivided time with each child builds secure attachment and goes with fewer behaviour problems."),
        Sub("reading", "work", "cultural", "Reading together", "📖", "number", 15, unit="min",
            why="Children read to every day hear about 1.4 million more words by age five than children never read to.",
            source="Logan et al., 2019"),
        Sub("shared_load", "work", "practical", "Shared load", "🤝", "number", 2, period="week", unit="tasks",
            why="Handing tasks over and asking for help keeps the household load from landing on one person.",
            source="Daminger, 2019"),
        Sub("recovery", "smart", "physical", "Time for herself", "🌿", "number", 30, unit="min",
            why="Parental burnout is real and preventable; time to recover protects you and your children.",
            source="Mikolajczak & Roskam, 2018"),
        Sub("support", "smart", "social", "Support network", "📞", "number", 2, period="week", unit="contacts",
            why="People to lean on are one of the strongest protections against burnout."),
        Sub("warmth", "smart", "discipline", "Warm but firm", "💛", "rating", 0,
            why="Warmth together with clear limits (authoritative parenting) predicts the best outcomes for children.",
            source="Baumrind, 1966"),
    ),
    chapters=(
        Chapter("time_week", "A week together", "Have one-to-one time 7 days in a row.", "streak", "connected_time", 7, 75),
        Chapter("reading_2w", "Two weeks of stories", "Read together 14 days in a row.", "streak", "reading", 14, 150),
        Chapter("help_10", "Ten handovers", "Hand over or share 10 tasks.", "total", "shared_load", 10, 100),
        Chapter("recovery_20", "Twenty days for you", "Take time for yourself on 20 days.", "days", "recovery", 20, 150),
        Chapter("support_20", "Twenty contacts", "Reach out to your support network 20 times.", "total", "support", 20, 100),
        Chapter("reading_1000", "A thousand minutes", "Read together for 1,000 minutes.", "total", "reading", 1000, 200),
    ),
    titles=((0, "Mother"), (3, "Steady Heart"), (6, "Everyday Hero"), (10, "The Anchor"), (15, "Legacy Builder"), (25, "Matriarch")),
    group="parent",
)

_CHILD_WHY_THANKS = "Saying thanks out loud strengthens the relationship for both of you."
_CHILD_WHY_STORY = "Children who know their family's story show more resilience and self-confidence."

SON = Path(
    "son", "Son", "👦",
    "Stay in touch, help out, say it out loud and learn where you come from.",
    subs=(
        Sub("contact", "work", "social", "Calling and visiting", "📞", "number", 3, period="week", unit="times",
            why="Sons tend to keep less contact with their parents than daughters do; regular contact matters to both of you.",
            source="Swartz, 2009 (review)"),
        Sub("help", "work", "practical", "Practical help", "🛠️", "number", 1, period="week", unit="times",
            why="Doing things for your parents (repairs, errands, tech) is a direct way to give back."),
        Sub("say_it", "smart", "social", "Saying it out loud", "💬", "yesno", 2, period="week",
            why=_CHILD_WHY_THANKS, source="Algoe, 2012"),
        Sub("family_story", "smart", "cultural", "Learning the family story", "📜", "number", 1, period="week", unit="questions",
            why=_CHILD_WHY_STORY, source="Duke & Fivush, 2008"),
    ),
    chapters=(
        Chapter("first_call", "First call", "Call or visit your parents.", "total", "contact", 1, 25),
        Chapter("month_in_touch", "A month in touch", "Call or visit 12 times.", "total", "contact", 12, 100),
        Chapter("thanks_5", "Out loud", "Thank them or share your life 5 times.", "total", "say_it", 5, 75),
        Chapter("help_10", "Ten helping hands", "Help your parents 10 times.", "total", "help", 10, 100),
        Chapter("story_10", "Family historian", "Ask 10 questions about your family's story.", "total", "family_story", 10, 150),
    ),
    titles=((0, "Son"), (3, "Good Son"), (6, "Pillar"), (10, "Keeper of the Story"), (15, "Family Rock")),
    group="child",
)

DAUGHTER = Path(
    "daughter", "Daughter", "👧",
    "Stay in touch, help without burning out, say it out loud and learn where you come from.",
    subs=(
        Sub("contact", "work", "social", "Calling and visiting", "📞", "number", 3, period="week", unit="times",
            why="Regular contact keeps you close; how you spend the time matters more than how much."),
        Sub("help", "work", "practical", "Help, with limits", "🤲", "number", 2, period="week", unit="times",
            why="Daughters carry more of the care for ageing parents than sons; help, and keep it sustainable.",
            source="Grigoryeva, 2017"),
        Sub("boundaries", "smart", "discipline", "Time for yourself kept", "🛡️", "yesno", 1,
            why="Protecting your own time keeps caregiving from wearing you down, so you can keep helping.",
            source="Pinquart & Sörensen, 2003"),
        Sub("say_it", "smart", "social", "Saying it out loud", "💬", "yesno", 2, period="week",
            why=_CHILD_WHY_THANKS, source="Algoe, 2012"),
        Sub("family_story", "smart", "cultural", "Learning the family story", "📜", "number", 1, period="week", unit="questions",
            why=_CHILD_WHY_STORY, source="Duke & Fivush, 2008"),
    ),
    chapters=(
        Chapter("first_call", "First call", "Call or visit your parents.", "total", "contact", 1, 25),
        Chapter("month_in_touch", "A month in touch", "Call or visit 12 times.", "total", "contact", 12, 100),
        Chapter("boundaries_20", "Twenty days for you", "Keep time for yourself on 20 days.", "days", "boundaries", 20, 150),
        Chapter("thanks_5", "Out loud", "Thank them or share your life 5 times.", "total", "say_it", 5, 75),
        Chapter("story_10", "Family historian", "Ask 10 questions about your family's story.", "total", "family_story", 10, 150),
    ),
    titles=((0, "Daughter"), (3, "Good Daughter"), (6, "Pillar"), (10, "Keeper of the Story"), (15, "Family Heart")),
    group="child",
)

PATHS = {p.key: p for p in (SCIENTIST, BUSINESSMAN, FATHER, MOTHER, SON, DAUGHTER)}
GROUP_NAMES = {"parent": "a parent role", "child": "a child role"}


def _today(db: Session, user: User) -> date:
    return profiles.today(db, user)


def user_paths(db: Session, user: User) -> list[UserPath]:
    return list(db.scalars(select(UserPath).where(UserPath.user_id == user.id)))


def path_subs(db: Session, user: User, path_key: str) -> list[SubClass]:
    return list(db.scalars(select(SubClass).where(SubClass.user_id == user.id, SubClass.path_key == path_key)
                           .order_by(SubClass.position, SubClass.id)))


def _baseline(sub: Sub, logs: dict, day: date) -> float | None:
    """Your average over the last two weeks for values the app already has"""
    if sub.kind != "field":
        return None
    section, key = sub.field.split(".", 1)
    values = [logs.get((day - timedelta(days=b)).isoformat(), {}).get(section, {}).get(key) for b in range(14)]
    values = [float(v) for v in values if isinstance(v, (int, float)) and not isinstance(v, bool)]
    return mean(values) if len(values) >= 5 else None


def _round(value: float, unit: str | None) -> float:
    return round(value, 1) if unit == "h" else max(1, round(value))


def start(db: Session, user: User, key: str, logs: dict) -> None:
    """Starts (or restarts) a path: its sub-classes join your classes, from your own baseline"""
    path = PATHS.get(key)
    if path is None:
        raise LookupError("No such path")
    mine = user_paths(db, user)
    row = next((p for p in mine if p.path_key == key), None)
    if not (row and row.active):
        active = [PATHS[p.path_key] for p in mine if p.active and p.path_key in PATHS]
        if path.group == "calling" and sum(1 for p in active if p.group == "calling") >= MAX_CALLINGS:
            raise ValueError(f"Up to {MAX_CALLINGS} paths at a time: leave one first")
        clash = next((p for p in active if p.group == path.group and path.group != "calling"), None)
        if clash:
            raise ValueError(f"You're already on {clash.name}, {GROUP_NAMES[path.group]}: leave it first")
    today = _today(db, user)
    if row is None:
        db.add(UserPath(user_id=user.id, path_key=key, started_on=today, active=True))
    else:
        row.active = True
        row.left_on = None
    existing = {s.template_key: s for s in path_subs(db, user, key)}
    for position, sub in enumerate(path.subs):
        if sub.key in existing:
            existing[sub.key].active = True
            continue
        target = None if sub.kind == "rating" else sub.target  # a 1-5 rating has no target
        baseline = _baseline(sub, logs, today)
        if baseline is not None and baseline > 0:
            target = _round(min(sub.target, baseline * RAISE), sub.unit)  # a step above where you are, never above the template
        db.add(SubClass(
            user_id=user.id, class_key=sub.class_key, name=sub.name, icon=sub.icon, kind=sub.kind, field=sub.field,
            unit=sub.unit, target=target, period=sub.period, better=sub.better, active=True, position=100 + position,
            path_key=key, template_key=sub.key, adjusted_at=today,
        ))
    db.commit()


def leave(db: Session, user: User, key: str) -> None:
    """Leaves a path: its sub-classes switch off (their history stays) and it stops counting"""
    row = next((p for p in user_paths(db, user) if p.path_key == key), None)
    if row is None:
        raise LookupError("You're not on that path")
    row.active = False
    row.left_on = _today(db, user)
    for sub in path_subs(db, user, key):
        sub.active = False
    db.commit()


# ---- Progress -------------------------------------------------------------------------------

def _value(entry: dict, sub: SubClass):
    return sub_classes.value_of(entry, sub)


def _week_start(day: date) -> date:
    return day - timedelta(days=day.weekday())


def daily_xp(subs: list[SubClass], started: date, logs: dict, end: date, path: Path, left: bool = False) -> dict[str, list[tuple[str, int]]]:
    """{day: [(reason, xp)]} for one path from its start to `end`: daily targets hit, weekly targets met
    (on the week's last logged day). left: the path was left, so its switched-off sub-classes still count
    up to the day it was left."""
    result: dict[str, list[tuple[str, int]]] = {}
    days = [started + timedelta(days=i) for i in range((end - started).days + 1)]
    for sub in subs:
        if not sub.active and not left:
            continue
        if sub.period == "week":
            weeks: dict[date, list[date]] = {}
            for d in days:
                weeks.setdefault(_week_start(d), []).append(d)
            for week, ds in weeks.items():
                values = [(d, _value(logs.get(d.isoformat(), {}), sub)) for d in ds]
                values = [(d, v) for d, v in values if v is not None]
                if not values:
                    continue
                if sub.kind == "yesno":
                    amount = sum(1 for _, v in values if bool(v) == (sub.better == "more"))
                    met = amount >= (sub.target or 1)
                else:
                    amount = sum(float(v) for _, v in values)
                    met = amount >= (sub.target or 0) if sub.better == "more" else amount <= (sub.target or 0)
                if met:
                    when = values[-1][0].isoformat()
                    result.setdefault(when, []).append((f"{path.icon} {sub.name}: week done", WEEK_XP))
        else:
            for d in days:
                if _hit(sub, _value(logs.get(d.isoformat(), {}), sub)):
                    xp = RATED_DAY_XP if sub.kind == "rating" else DAY_XP
                    result.setdefault(d.isoformat(), []).append((f"{path.icon} {sub.name}", xp))
    return result


def _hit(sub: SubClass, value) -> bool:
    """On target for the day; a 1-5 self-rating counts from 4"""
    if sub.kind == "rating":
        return value is not None and float(value) >= 4
    score = sub_classes.day_score(sub, value)
    return score is not None and score >= 0.999


def chapter_progress(chapter: Chapter, sub: SubClass | None, started: date, logs: dict, today: date) -> float:
    """How far along a chapter is, in its own unit (papers, days in a row, hours in the best week…)"""
    if sub is None:
        return 0
    days = [started + timedelta(days=i) for i in range((today - started).days + 1)]
    values = [(d, _value(logs.get(d.isoformat(), {}), sub)) for d in days]
    number = lambda v: (1.0 if bool(v) == (sub.better == "more") else 0.0) if isinstance(v, bool) else float(v)
    if chapter.rule == "total":
        return sum(number(v) for _, v in values if v is not None)
    if chapter.rule == "best_week":
        weeks: dict[date, float] = {}
        for d, v in values:
            if v is not None:
                weeks[_week_start(d)] = weeks.get(_week_start(d), 0) + number(v)
        return max(weeks.values(), default=0)
    if chapter.rule == "streak":
        best = run = 0
        for _, v in values:
            run = run + 1 if v is not None and _hit(sub, v) else 0
            best = max(best, run)
        return best
    if chapter.rule == "days":
        return sum(1 for _, v in values if v is not None and _hit(sub, v))
    return 0


def summary(db: Session, user: User, logs: dict) -> dict:
    """Every path you're on (and were on): XP by day and from chapters, for the global level"""
    today = _today(db, user)
    by_day: dict[str, list[tuple[str, int]]] = {}
    chapter_xp = 0
    for row in user_paths(db, user):
        path = PATHS.get(row.path_key)
        if path is None:
            continue
        subs = path_subs(db, user, row.path_key)
        end = today if row.active else (row.left_on or today)
        for day, items in daily_xp(subs, row.started_on, logs, end, path, left=not row.active).items():
            by_day.setdefault(day, []).extend(items)
        by_template = {s.template_key: s for s in subs}
        for chapter in path.chapters:
            if chapter_progress(chapter, by_template.get(chapter.sub), row.started_on, logs, end) >= chapter.target:
                chapter_xp += chapter.xp
    return {"by_day": by_day, "chapter_xp": chapter_xp}


def path_levels(db: Session, user: User, logs: dict) -> dict[str, int]:
    """{path key: level} for every path you're on or were on (books unlock by these)"""
    from app.services import levels

    today = _today(db, user)
    result = {}
    for row in user_paths(db, user):
        path = PATHS.get(row.path_key)
        if path is None:
            continue
        subs = path_subs(db, user, row.path_key)
        end = today if row.active else (row.left_on or today)
        xp = sum(x for items in daily_xp(subs, row.started_on, logs, end, path, left=not row.active).values() for _, x in items)
        by_template = {s.template_key: s for s in subs}
        xp += sum(ch.xp for ch in path.chapters if chapter_progress(ch, by_template.get(ch.sub), row.started_on, logs, end) >= ch.target)
        result[row.path_key] = levels.level_for(xp)
    return result


def adjust_targets(db: Session, user: User, logs: dict) -> list[str]:
    """Once a week per sub-class: 10% harder after a strong week, 10% easier after a weak one"""
    today = _today(db, user)
    notes = []
    active_paths = {p.path_key for p in user_paths(db, user) if p.active}
    for key in active_paths:
        for sub in path_subs(db, user, key):
            if not sub.active or sub.kind not in ("number", "field") or not sub.target:
                continue
            if sub.adjusted_at and (today - sub.adjusted_at).days < 7:
                continue
            week = [today - timedelta(days=b) for b in range(1, 8)]
            values = [_value(logs.get(d.isoformat(), {}), sub) for d in week]
            if sub.period == "week":
                known = [float(v) for v in values if v is not None and not isinstance(v, bool)]
                if not known:
                    sub.adjusted_at = today
                    continue
                rate = min(1.0, sum(known) / sub.target) if sub.better == "more" else (1.0 if sum(known) <= sub.target else 0.0)
            else:
                known = [v for v in values if v is not None]
                if len(known) < 4:  # not enough days to judge
                    sub.adjusted_at = today
                    continue
                rate = sum(1 for v in known if _hit(sub, v)) / len(known)
            old = sub.target
            if rate >= 0.85:
                sub.target = _round(old * (RAISE if sub.better == "more" else LOWER), sub.unit)
            elif rate <= 0.40:
                sub.target = _round(old * (LOWER if sub.better == "more" else RAISE), sub.unit)
            sub.adjusted_at = today
            if sub.target != old:
                unit = f" {sub.unit}" if sub.unit else ""
                notes.append(f"{sub.name}: {old:g} → {sub.target:g}{unit} ({'harder' if (sub.target > old) == (sub.better == 'more') else 'easier'})")
    db.commit()
    return notes


def view(db: Session, user: User, logs: dict, sheet_stats: dict, notes: list[str] | None = None) -> dict:
    """Paths you're on with level, title, both halves and the story; and the ones you could start"""
    from app.services import levels

    today = _today(db, user)
    mine = {p.path_key: p for p in user_paths(db, user)}
    active = []
    for key, row in mine.items():
        path = PATHS.get(key)
        if path is None or not row.active:
            continue
        subs = path_subs(db, user, key)
        by_template = {s.template_key: s for s in subs}
        xp_days = daily_xp(subs, row.started_on, logs, today, path)
        chapters = []
        for chapter in path.chapters:
            value = chapter_progress(chapter, by_template.get(chapter.sub), row.started_on, logs, today)
            chapters.append({"key": chapter.key, "name": chapter.name, "how": chapter.how, "xp": chapter.xp,
                             "value": round(value, 1), "target": chapter.target, "done": value >= chapter.target,
                             "progress": round(min(1.0, value / chapter.target), 3)})
        xp = sum(x for items in xp_days.values() for _, x in items) + sum(c["xp"] for c in chapters if c["done"])
        level = levels.level_for(xp)
        title = [name for at, name in path.titles if level >= at][-1]
        next_title = next((f"{name} at LV {at}" for at, name in path.titles if at > level), None)
        halves = {"work": [], "smart": []}
        for template in path.subs:
            sub = by_template.get(template.key)
            if sub is None:
                continue
            result = sheet_stats.get(sub_classes.code_of(sub)) or {}
            score = result.get("score")
            halves[template.half].append({
                **sub_classes.describe(sub), "why": template.why, "source": template.source,
                "score": score, "grade": character_stats.grade(score) if score is not None else None,
                "note": (result.get("components") or [{}])[0].get("note"),
            })
        active.append({
            "key": key, "name": path.name, "icon": path.icon, "blurb": path.blurb, "group": path.group, "started_on": row.started_on,
            "xp": xp, "level": level, "level_start_xp": levels.xp_for_level(level), "next_level_xp": levels.xp_for_level(level + 1),
            "title": title, "next_title": next_title, "today_xp": sum(x for _, x in xp_days.get(today.isoformat(), [])),
            "halves": halves, "chapters": chapters,
            "next_chapter": next((c["key"] for c in chapters if not c["done"]), None),
        })
    available = [
        {"key": p.key, "name": p.name, "icon": p.icon, "blurb": p.blurb, "group": p.group, "started_before": p.key in mine,
         "work": [s.name for s in p.subs if s.half == "work"], "smart": [s.name for s in p.subs if s.half == "smart"]}
        for p in PATHS.values() if not (p.key in mine and mine[p.key].active)
    ]
    return {"max": MAX_CALLINGS, "active": active, "available": available, "adjusted": notes or []}
