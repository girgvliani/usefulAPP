"""Books (Phase 11.4, design: usefulAPP-expo/docs/PATHS-DESIGN.md section 4).

A book is a short guide (a few five-minute chapters, with the research behind them) plus a tracker that
turns its method into something you do. It unlocks at a path level, or a friend who has it gifts it
(one gift a week).

- Reading: 20 XP per chapter, 50 more for finishing the book.
- Practice: 5 XP each day the tracker is used.
- What you log feeds the matching path sub-class for that day (a 50-minute focus session adds to Deep
  work hours, a call home to Calling and visiting), so it counts in the check-in, the stats and the path.
"""
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import BookEntry, SubClass, User, UserBook
from app.services import daily_logs, friends, paths, profiles

CHAPTER_XP = 20
FINISH_XP = 50
PRACTICE_XP = 5
GIFT_DAYS = 7
MAX_ENTRIES = 2000  # per book and person
BOXES = (1, 2, 4, 8, 16)  # spaced repetition: days until the next review, by box


@dataclass(frozen=True)
class BookChapter:
    title: str
    text: str
    source: str | None = None


@dataclass(frozen=True)
class Book:
    key: str
    name: str
    icon: str
    blurb: str
    unlock: tuple[tuple[str, int], ...]  # (path, level): any one of them
    kinds: tuple[str, ...]  # what its tracker logs (ENTRY_FIELDS)
    chapters: tuple[BookChapter, ...]


# ---- What each tracker logs ------------------------------------------------------------------
# field: (type, ...limits, required). text: max length · int: min, max · lines: max items, max length ·
# choice: options

ENTRY_FIELDS: dict[str, dict[str, tuple]] = {
    "palace": {"name": ("text", 40, True), "loci": ("lines", 50, 60, True)},
    "test": {"palace_id": ("int", 1, 2**31, True), "items": ("int", 1, 200, True), "recalled": ("int", 0, 200, True)},
    "card": {"front": ("text", 200, True), "back": ("text", 400, True)},
    "session": {"minutes": ("int", 1, 600, True), "quality": ("int", 1, 5, True), "task": ("text", 80, False)},
    "decision": {"decision": ("text", 200, True), "expected": ("text", 300, True), "confidence": ("int", 50, 100, True)},
    "conversation": {"who": ("text", 60, True), "learned": ("text", 300, True), "change": ("text", 300, False)},
    "block": {"minutes": ("int", 1, 600, True), "with": ("text", 40, False)},
    "person": {"name": ("text", 40, True), "every_days": ("int", 1, 60, True)},
    "contact": {"person_id": ("int", 1, 2**31, True), "how": ("choice", ("call", "visit", "message"), True)},
}
EDITABLE = {"palace", "card", "person", "decision"}  # the rest are things that happened
PRACTICE = {"test", "review", "session", "decision", "conversation", "block", "contact"}  # earn the day's practice XP
REVIEW_AFTER = (30, 90)  # a decision is reviewed after 30 and 90 days

# What a logged entry adds to the day: ("field", "section.key", amount) or ("sub", path sub-class key, amount)
FEEDS = {
    "session": lambda d: [("field", "work.deep", d["minutes"] / 60)],
    "test": lambda d: [("sub", "retrieval", d["recalled"])],
    "review": lambda d: [("sub", "retrieval", 1)],
    "decision": lambda d: [("sub", "decisions", 1)],
    "conversation": lambda d: [("sub", "customers", 1)],
    "block": lambda d: [("sub", "engaged_time", d["minutes"]), ("sub", "connected_time", d["minutes"]), ("sub", "present", True)],
    "contact": lambda d: [("sub", "contact", 1)],
}


MEMORY_PALACE = Book(
    "memory_palace", "Memory Palace", "🏛️",
    "Remember long lists in order by placing them along a route you know by heart.",
    unlock=(("scientist", 3),), kinds=("palace", "test"),
    chapters=(
        BookChapter(
            "Why places stick",
            "Your brain is far better at remembering places and routes than lists of words. The method of loci, "
            "the memory palace, uses that: you put what you want to remember along a route you already know.\n\n"
            "It is old. The story goes that the Greek poet Simonides could name every guest at a banquet after "
            "the hall collapsed, because he remembered where each one had sat.\n\n"
            "Memory champions are not born different. Brain scans of the world's best memorisers found ordinary "
            "intelligence and ordinary brain structure. What they shared was the strategy: nine in ten used a "
            "route like this one.",
            "Maguire et al., 2003"),
        BookChapter(
            "Build your first palace",
            "Pick a place you know very well: your home is best. Walk through it in your mind, always in the "
            "same direction, and pick ten spots (loci) along the way: the front door, the shoe rack, the mirror, "
            "the sofa, the window…\n\n"
            "Each spot should be distinct, easy to picture and always in the same order. Avoid two similar ones "
            "next to each other (two chairs).\n\n"
            "Write your ten spots in the tracker as your first palace. Walk it in your head twice, forwards and "
            "backwards, until you don't have to think."),
        BookChapter(
            "Placing and walking",
            "To remember a list, turn each item into a vivid image (big, odd, moving, funny) and put it on a "
            "spot, doing something with it. Milk? A cow is spraying milk all over your front door.\n\n"
            "To recall, walk the route: each spot hands you its image back, in order.\n\n"
            "In a study, people who trained like this for 30 minutes a day for six weeks more than doubled the "
            "number of words they could remember, and their brain connectivity shifted towards that of memory "
            "athletes. The gain was still there four months later.\n\n"
            "Test yourself in the tracker: how many items you placed and how many came back. Every item you "
            "recall counts as retrieval practice.",
            "Dresler et al., 2017"),
    ),
)

SPACED_REPETITION = Book(
    "spaced_repetition", "Spaced Repetition", "🗂️",
    "Review each fact just before you would forget it, and keep it for years with a few minutes a day.",
    unlock=(("scientist", 2),), kinds=("card",),
    chapters=(
        BookChapter(
            "The forgetting curve",
            "In the 1880s Hermann Ebbinghaus learned lists of nonsense syllables and measured how fast he forgot "
            "them. Most of it went within a day or two.\n\n"
            "But every review, especially one just as you are about to forget, slows the forgetting down. After "
            "a few well-timed reviews a fact lasts months.",
            "Ebbinghaus, 1885"),
        BookChapter(
            "Test, don't reread",
            "Pulling an answer out of your memory strengthens it far more than reading it again. Students who "
            "practised recalling a text remembered much more of it a week later than students who reread it, "
            "even though the rereaders felt more confident.\n\n"
            "And spread it out: the same study time split over several days beats one long session.",
            "Roediger & Karpicke, 2006; Cepeda et al., 2006"),
        BookChapter(
            "The box system",
            "The tracker uses Leitner's boxes. A new card starts in box 1 and comes back the next day. Remember "
            "it and it moves up a box: next time in 2 days, then 4, 8 and 16. Miss it and it goes back to box 1.\n\n"
            "Keep cards small: one fact, one question. Write the question on the front in your own words.\n\n"
            "Every card you review counts towards Retrieval practice.",
            "Leitner, 1972"),
    ),
)

DEEP_WORK = Book(
    "deep_work", "Deep Work", "🎯",
    "Focus sessions with no distractions, timed and rated, for the work that matters most.",
    unlock=(("scientist", 1), ("businessman", 1)), kinds=("session",),
    chapters=(
        BookChapter(
            "Why depth wins",
            "Hard, valuable work (writing, analysis, building, learning something difficult) needs long, unbroken "
            "concentration.\n\n"
            "Expert musicians did their most demanding practice in sessions of about an hour, and about four "
            "hours a day at most. Beyond that, quality drops.\n\n"
            "Cal Newport calls this deep work, and argues it is becoming both rarer and more valuable.",
            "Ericsson, Krampe & Tesch-Römer, 1993; Newport, 2016"),
        BookChapter(
            "Attention residue",
            "When you switch from one task to another, part of your attention stays behind on the first one, and "
            "you do worse on the next. A quick look at your messages leaves that residue for a while.\n\n"
            "People who are interrupted often do get the work done, by going faster, but with more stress and "
            "frustration.",
            "Leroy, 2009; Mark, Gudith & Klocke, 2008"),
        BookChapter(
            "A session",
            "Decide the one task before you start. Put the phone in another room and turn notifications off.\n\n"
            "Start the timer: 25 to 90 minutes. When you stop, rate the session 1-5: how deep did you really go? "
            "Watching the quality as well as the minutes keeps you honest.\n\n"
            "The minutes add to your Deep work hours for the day."),
    ),
)

DECISION_JOURNAL = Book(
    "decision_journal", "Decision Journal", "⚖️",
    "Write down what you decide and what you expect, then check later how often you were right.",
    unlock=(("businessman", 2),), kinds=("decision",),
    chapters=(
        BookChapter(
            "Hindsight lies",
            "Once we know how something turned out, we believe we saw it coming. People asked to recall their "
            "earlier predictions remember them as closer to what happened than they were.\n\n"
            "Without a written record you can't tell which decisions were good and which were lucky.",
            "Fischhoff, 1975"),
        BookChapter(
            "Decisions are not outcomes",
            "A good decision can turn out badly and a bad one can work out. Judging decisions only by how they "
            "ended, which poker players call 'resulting', teaches the wrong lessons.\n\n"
            "So write it down before you know: what you decided, what you expect to happen, and how sure you are.",
            "Duke, 2018"),
        BookChapter(
            "Keep score",
            "Forecasters who wrote down probabilities and got feedback on them became measurably better "
            "calibrated over time.\n\n"
            "Review each decision after 30 and 90 days: what happened, and were you right? The tracker shows how "
            "often you're right at each level of confidence. If your 90% calls come true 60% of the time, you're "
            "overconfident.\n\n"
            "Each decision counts towards your Decision journal.",
            "Tetlock & Gardner, 2015"),
    ),
)

CUSTOMER_CONVERSATIONS = Book(
    "customer_conversations", "Customer Conversations", "🗣️",
    "Learn what people really need by asking about their lives, not your idea.",
    unlock=(("businessman", 1),), kinds=("conversation",),
    chapters=(
        BookChapter(
            "Talk before you build",
            "Building something nobody needs is among the most common reasons new businesses fail. Talking to "
            "customers early is the cheapest way to find out what they need.\n\n"
            "Steve Blank called it customer development: before scaling, go out and test your guesses with real "
            "people.",
            "Blank, 2005; CB Insights startup post-mortems"),
        BookChapter(
            "Ask about their life",
            "People are polite. Ask 'would you buy this?' and most will say yes, and mean nothing by it.\n\n"
            "Ask about the past instead: the last time they had the problem, what they did about it, what it cost "
            "them, what they already pay for. Facts about what they did beat opinions about what they might do.",
            "Fitzpatrick, 2013 (The Mom Test)"),
        BookChapter(
            "Write it down",
            "Right after each conversation write down who it was, what you learned, and what you'll change. "
            "Memory bends towards what you hoped to hear.\n\n"
            "Patterns show up after five to ten conversations: the same problem in the same words.\n\n"
            "Each one counts towards Customer conversations."),
    ),
)

PRESENT_PARENT = Book(
    "present_parent", "The Present Parent", "📵",
    "Phone-free blocks and one-to-one time with your children, logged so you can see them add up.",
    unlock=(("father", 1), ("mother", 1)), kinds=("block",),
    chapters=(
        BookChapter(
            "Technoference",
            "Phones interrupting family time ('technoference') go together with more acting out from children.\n\n"
            "Parents in another study who used their phones more while with their children felt more distracted "
            "and got less sense of connection from the time together.",
            "McDaniel & Radesky, 2018; Kushlev & Dunn, 2019"),
        BookChapter(
            "Phone-free blocks",
            "Pick a block of the day: dinner, bath time, the first hour after school. Put the phone in a drawer, "
            "not face down on the table: in one study, just having a phone in sight made a conversation feel "
            "less close.\n\n"
            "Tell the people who might need you when you'll be back.",
            "Przybylski & Weinstein, 2013"),
        BookChapter(
            "One-to-one time",
            "A few minutes of undivided time with one child, most days: they choose the activity, you follow "
            "their lead, describe what they do and praise it. No teaching, no correcting, no questions.\n\n"
            "This 'special time' is the core of parent-child interaction therapy, one of the best-tested "
            "parenting programmes.\n\n"
            "Log each block: the minutes count towards One-to-one time and the day counts as present.",
            "Eyberg & Funderburk, 2011"),
    ),
)

CALLING_HOME = Book(
    "calling_home", "Calling Home", "📞",
    "Keep in touch with your parents and family on a rhythm, before it slips.",
    unlock=(("son", 1), ("daughter", 1)), kinds=("person", "contact"),
    chapters=(
        BookChapter(
            "Connection is health",
            "Across 148 studies and more than 300,000 people, those with stronger social relationships had about "
            "50% higher odds of being alive at the end of the study, an effect on the scale of quitting smoking.\n\n"
            "That goes for your parents as much as for you.",
            "Holt-Lunstad, Smith & Layton, 2010"),
        BookChapter(
            "They want to hear from you",
            "People underestimate how much others appreciate hearing from them, most of all out of the blue. "
            "They also underestimate how good a thank-you makes the other person feel, and how little awkward it "
            "is.\n\n"
            "The call you keep putting off would be welcome.",
            "Liu et al., 2022; Kumar & Epley, 2018"),
        BookChapter(
            "A rhythm",
            "Add the people you want to stay close to and how often you'd like to be in touch: your mother every "
            "3 days, your grandfather every week.\n\n"
            "The tracker shows who is due. Each call, visit or message you log counts towards Calling and "
            "visiting."),
    ),
)

BOOKS = {b.key: b for b in (DEEP_WORK, SPACED_REPETITION, MEMORY_PALACE, CUSTOMER_CONVERSATIONS, DECISION_JOURNAL,
                             PRESENT_PARENT, CALLING_HOME)}


# ---- Unlocking and gifts -----------------------------------------------------------------------

def owned(db: Session, user: User) -> dict[str, UserBook]:
    return {b.book_key: b for b in db.scalars(select(UserBook).where(UserBook.user_id == user.id))}


def unlock_text(book: Book) -> str:
    return " or ".join(f"{paths.PATHS[p].name} LV {lv}" for p, lv in book.unlock)


def sync_unlocks(db: Session, user: User, logs: dict) -> list[str]:
    """Unlocks every book a path level now reaches. Returns the names of the new ones."""
    mine = owned(db, user)
    levels = paths.path_levels(db, user, logs)
    new = []
    for book in BOOKS.values():
        if book.key in mine:
            continue
        if any(levels.get(p, -1) >= lv for p, lv in book.unlock):
            db.add(UserBook(user_id=user.id, book_key=book.key, via="level", unlocked_at=datetime.now(timezone.utc), chapters_read={}))
            new.append(book.name)
    if new:
        db.commit()
    return new


def next_gift_on(db: Session, user: User) -> date | None:
    """The day you can send your next gift, or None if you can send one now"""
    last = db.scalar(select(UserBook).where(UserBook.gifted_by == user.id).order_by(UserBook.unlocked_at.desc()).limit(1))
    if last is None:
        return None
    when = last.unlocked_at.date() + timedelta(days=GIFT_DAYS)
    return when if when > profiles.today(db, user) else None


def gift(db: Session, me: User, key: str, friend_id: int) -> str:
    book = BOOKS.get(key)
    if book is None:
        raise LookupError("No such book")
    if key not in owned(db, me):
        raise PermissionError("You can only gift a book you have")
    friend = next((f for f in friends.friends_of(db, me) if f.id == friend_id), None)
    if friend is None:
        raise LookupError("You can only gift a book to a friend")
    name = friends.name_of(db, friend)
    if key in owned(db, friend):
        raise ValueError(f"{name} already has {book.name}")
    wait = next_gift_on(db, me)
    if wait:
        raise ValueError(f"One gift a week: your next one on {wait.isoformat()}")
    db.add(UserBook(user_id=friend.id, book_key=key, via="gift", gifted_by=me.id, unlocked_at=datetime.now(timezone.utc), chapters_read={}))
    db.commit()
    return f"{book.icon} {book.name} is on its way to {name}"


# ---- Reading -------------------------------------------------------------------------------

def read_chapter(db: Session, user: User, key: str, index: int) -> None:
    book, row = _mine(db, user, key)
    if not 0 <= index < len(book.chapters):
        raise LookupError("No such chapter")
    if str(index) not in (row.chapters_read or {}):
        row.chapters_read = {**(row.chapters_read or {}), str(index): profiles.today(db, user).isoformat()}
        db.commit()


def _mine(db: Session, user: User, key: str) -> tuple[Book, UserBook]:
    book = BOOKS.get(key)
    if book is None:
        raise LookupError("No such book")
    row = owned(db, user).get(key)
    if row is None:
        raise PermissionError(f"{book.name} unlocks at {unlock_text(book)}, or as a gift from a friend")
    return book, row


# ---- Tracker entries -------------------------------------------------------------------------

def _clean(kind: str, data: dict, partial: bool = False) -> dict:
    """Checks an entry's fields against ENTRY_FIELDS; unknown fields are dropped"""
    out = {}
    for name, spec in ENTRY_FIELDS[kind].items():
        value = data.get(name)
        if value is None or value == "" or value == []:
            if spec[-1] and not partial:
                raise ValueError(f"'{name}' is needed")
            continue
        kind_of = spec[0]
        if kind_of == "text":
            if not isinstance(value, str) or len(value.strip()) > spec[1]:
                raise ValueError(f"'{name}' must be text of up to {spec[1]} characters")
            value = value.strip()
        elif kind_of == "int":
            if isinstance(value, bool) or not isinstance(value, (int, float)) or value != int(value) or not spec[1] <= value <= spec[2]:
                raise ValueError(f"'{name}' must be a whole number from {spec[1]} to {spec[2]}")
            value = int(value)
        elif kind_of == "lines":
            if not isinstance(value, list) or not 1 <= len(value) <= spec[1] or not all(isinstance(v, str) and 0 < len(v.strip()) <= spec[2] for v in value):
                raise ValueError(f"'{name}' must be 1 to {spec[1]} lines of up to {spec[2]} characters")
            value = [v.strip() for v in value]
        elif kind_of == "choice":
            if value not in spec[1]:
                raise ValueError(f"'{name}' must be one of {', '.join(spec[1])}")
        out[name] = value
    return out


def entries(db: Session, user: User, key: str) -> list[BookEntry]:
    return list(db.scalars(select(BookEntry).where(BookEntry.user_id == user.id, BookEntry.book_key == key)
                           .order_by(BookEntry.day.desc(), BookEntry.id.desc())))


def _entry(db: Session, user: User, key: str, entry_id: int) -> BookEntry:
    row = db.get(BookEntry, entry_id)
    if row is None or row.user_id != user.id or row.book_key != key:
        raise LookupError("No such entry")
    return row


def _feed(db: Session, user: User, day: date, feeds: list[tuple], sign: int) -> None:
    """Adds (or, sign -1, takes back) what an entry contributes to the day's check-in values"""
    log = daily_logs.get_log(db, user, day)
    current = daily_logs.merged(log) if log else {}
    updates: dict[str, dict] = {}
    for target, key, amount in feeds:
        if target == "field":
            section, field = key.split(".", 1)
            base = updates.get(section, {}).get(field, current.get(section, {}).get(field)) or 0
            value = max(0.0, min(24.0, round(float(base) + sign * amount, 2)))
            updates.setdefault(section, {})[field] = value
            continue
        sub = db.scalar(select(SubClass).where(SubClass.user_id == user.id, SubClass.template_key == key,
                                               SubClass.path_key.is_not(None), SubClass.active.is_(True)).limit(1))
        if sub is None:
            continue
        if sub.kind == "yesno":
            if sign > 0:
                updates.setdefault("custom", {})[str(sub.id)] = True
            continue
        base = updates.get("custom", {}).get(str(sub.id), current.get("custom", {}).get(str(sub.id))) or 0
        updates.setdefault("custom", {})[str(sub.id)] = max(0, round(float(base) + sign * amount, 2))
    if updates:
        daily_logs.save(db, user, day, "manual", updates)


def add_entry(db: Session, user: User, key: str, kind: str, day: date | None, data: dict) -> BookEntry:
    book, _ = _mine(db, user, key)
    if kind not in book.kinds:
        raise ValueError(f"{book.name} logs {', '.join(book.kinds)}")
    today = profiles.today(db, user)
    day = day or today
    if day > today or (today - day).days > 365:
        raise ValueError("The day must be within the last year")
    clean = _clean(kind, data)
    if kind == "test":
        if clean["recalled"] > clean["items"]:
            raise ValueError("You can't recall more items than you placed")
        _entry_of(db, user, key, clean["palace_id"], "palace")
    if kind == "contact":
        _entry_of(db, user, key, clean["person_id"], "person")
    if kind == "card":
        clean.update(box=1, due=(day + timedelta(days=BOXES[0])).isoformat())
    if len(entries(db, user, key)) >= MAX_ENTRIES:
        raise ValueError(f"Up to {MAX_ENTRIES} entries per book")
    row = BookEntry(user_id=user.id, book_key=key, kind=kind, day=day, data=clean)
    db.add(row)
    db.commit()
    if kind in FEEDS:
        _feed(db, user, day, FEEDS[kind](clean), +1)
    return row


def _entry_of(db: Session, user: User, key: str, entry_id: int, kind: str) -> BookEntry:
    try:
        row = _entry(db, user, key, entry_id)
    except LookupError:
        row = None
    if row is None or row.kind != kind:
        raise ValueError(f"No such {kind}")
    return row


def edit_entry(db: Session, user: User, key: str, entry_id: int, data: dict) -> BookEntry:
    _mine(db, user, key)
    row = _entry(db, user, key, entry_id)
    if row.kind not in EDITABLE:
        raise ValueError("Delete it and log it again instead")
    updated = {**row.data, **_clean(row.kind, data, partial=True)}
    if row.kind == "decision":
        for after in REVIEW_AFTER:
            review = data.get(f"review{after}")
            if review is None:
                continue
            due = row.day + timedelta(days=after)
            if profiles.today(db, user) < due:
                raise ValueError(f"The {after}-day review opens on {due.isoformat()}")
            if not isinstance(review, dict) or not isinstance(review.get("right"), bool) or not isinstance(review.get("outcome"), str) \
                    or not 0 < len(review["outcome"].strip()) <= 300:
                raise ValueError("A review needs what happened (up to 300 characters) and whether you were right")
            updated[f"review{after}"] = {"outcome": review["outcome"].strip(), "right": review["right"]}
    row.data = updated
    db.commit()
    return row


def delete_entry(db: Session, user: User, key: str, entry_id: int) -> None:
    _mine(db, user, key)
    row = _entry(db, user, key, entry_id)
    if row.kind in FEEDS:
        _feed(db, user, row.day, FEEDS[row.kind](row.data), -1)
    if row.kind in ("palace", "person"):  # its tests and contacts go with it
        child, ref = ("test", "palace_id") if row.kind == "palace" else ("contact", "person_id")
        for other in entries(db, user, key):
            if other.kind == child and other.data.get(ref) == row.id:
                _feed(db, user, other.day, FEEDS[child](other.data), -1)
                db.delete(other)
    db.delete(row)
    db.commit()


def review_card(db: Session, user: User, key: str, entry_id: int, remembered: bool) -> BookEntry:
    """Spaced repetition: remembered → up a box (next review later), missed → back to box 1. The day's
    reviews are counted in one 'review' entry."""
    _mine(db, user, key)
    card = _entry_of(db, user, key, entry_id, "card")
    today = profiles.today(db, user)
    box = min(len(BOXES), card.data.get("box", 1) + 1) if remembered else 1
    card.data = {**card.data, "box": box, "due": (today + timedelta(days=BOXES[box - 1])).isoformat()}
    review = next((e for e in entries(db, user, key) if e.kind == "review" and e.day == today), None)
    if review is None:
        review = BookEntry(user_id=user.id, book_key=key, kind="review", day=today, data={"cards": 0, "remembered": 0})
        db.add(review)
    review.data = {"cards": review.data["cards"] + 1, "remembered": review.data["remembered"] + int(remembered)}
    db.commit()
    _feed(db, user, today, FEEDS["review"]({}), +1)
    return card


# ---- XP and views ----------------------------------------------------------------------------

def summary(db: Session, user: User) -> dict:
    """{day: [(reason, xp)]}: chapters read, finished books, days a tracker was used"""
    by_day: dict[str, list[tuple[str, int]]] = {}
    for key, row in owned(db, user).items():
        book = BOOKS.get(key)
        if book is None:
            continue
        read = row.chapters_read or {}
        for index, day in read.items():
            by_day.setdefault(day, []).append((f"{book.icon} {book.name}: chapter {int(index) + 1}", CHAPTER_XP))
        if len(read) >= len(book.chapters):
            by_day.setdefault(max(read.values()), []).append((f"{book.icon} {book.name}: finished", FINISH_XP))
        practice_days = {e.day.isoformat() for e in entries(db, user, key) if e.kind in PRACTICE}
        for day in practice_days:
            by_day.setdefault(day, []).append((f"{book.icon} {book.name}: practice", PRACTICE_XP))
    return {"by_day": by_day}


def _card(db: Session, user: User, book: Book, row: UserBook | None) -> dict:
    read = (row.chapters_read or {}) if row else {}
    used = {e.day for e in entries(db, user, book.key) if e.kind in PRACTICE} if row else set()
    xp = len(read) * CHAPTER_XP + (FINISH_XP if len(read) >= len(book.chapters) else 0) + len(used) * PRACTICE_XP
    gifted_by = db.get(User, row.gifted_by) if row and row.gifted_by else None
    return {
        "key": book.key, "name": book.name, "icon": book.icon, "blurb": book.blurb,
        "paths": [p for p, _ in book.unlock], "unlock": unlock_text(book),
        "unlocked": row is not None, "via": row.via if row else None,
        "gifted_by": friends.name_of(db, gifted_by) if gifted_by else None,
        "chapters_total": len(book.chapters), "chapters_read": len(read),
        "practice_days": len(used), "used_today": profiles.today(db, user) in used, "xp": xp,
    }


def view(db: Session, user: User, new: list[str] | None = None) -> dict:
    mine = owned(db, user)
    wait = next_gift_on(db, user)
    return {
        "books": [_card(db, user, b, mine.get(b.key)) for b in BOOKS.values()],
        "new": new or [], "next_gift_on": wait.isoformat() if wait else None,
    }


def detail(db: Session, user: User, key: str) -> dict:
    book = BOOKS.get(key)
    if book is None:
        raise LookupError("No such book")
    row = owned(db, user).get(key)
    wait = next_gift_on(db, user)
    read = (row.chapters_read or {}) if row else {}
    return {
        **_card(db, user, book, row),
        "kinds": list(book.kinds),
        "chapters": [
            {"index": i, "title": ch.title, "read": str(i) in read,
             **({"text": ch.text, "source": ch.source} if row else {})}
            for i, ch in enumerate(book.chapters)
        ],
        "entries": [{"id": e.id, "kind": e.kind, "day": e.day.isoformat(), "data": e.data} for e in entries(db, user, key)] if row else [],
        "today": profiles.today(db, user).isoformat(),
        "next_gift_on": wait.isoformat() if wait else None,
        "review_after": list(REVIEW_AFTER),
    }


def for_paths(db: Session, user: User) -> dict[str, list[dict]]:
    """{path key: [its books, unlocked or not]} for the path pages"""
    mine = owned(db, user)
    result: dict[str, list[dict]] = {}
    for book in BOOKS.values():
        for path_key, level in book.unlock:
            result.setdefault(path_key, []).append({"key": book.key, "name": book.name, "icon": book.icon,
                                                    "level": level, "unlocked": book.key in mine})
    return result
