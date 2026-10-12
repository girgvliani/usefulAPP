"""Books (Phase 11.4): unlocking by path level, reading XP, trackers that feed path sub-classes, gifts."""
from datetime import date, datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database import SessionLocal
from app.main import app
from app.models import User, UserBook, UserPath
from app.services import books as book_service

today = date.today()
day = lambda back: (today - timedelta(days=back)).isoformat()


def client(email):
    c = TestClient(app)
    token = c.post("/auth/register", json={"email": email, "password": "book-password-1"}).json()["access_token"]
    c.headers["Authorization"] = f"Bearer {token}"
    return c


def give(email, key):
    """Hands a book over directly, to test its tracker without levelling up first"""
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))
        db.add(UserBook(user_id=user.id, book_key=key, via="level", unlocked_at=datetime.now(timezone.utc), chapters_read={}))
        db.commit()


a = client("reader@example.com")

# Every book starts locked, with what unlocks it; the text stays hidden
view = a.get("/books").json()
assert len(view["books"]) == 7 and not any(b["unlocked"] for b in view["books"]), view
deep = next(b for b in view["books"] if b["key"] == "deep_work")
assert deep["unlock"] == "Scientist LV 1 or Businessman LV 1", deep
locked = a.get("/books/deep_work").json()
assert not locked["unlocked"] and "text" not in locked["chapters"][0] and locked["entries"] == []
r = a.post("/books/deep_work/entries", json={"kind": "session", "data": {"minutes": 30, "quality": 3}})
assert r.status_code == 403 and "Scientist LV 1" in r.json()["detail"], r.text
assert a.get("/books/astronomy").status_code == 404

# Scientist for 12 days with daily writing on target: 120 XP + the 75 XP writing-week chapter → LV 1
a.post("/paths/scientist")
with SessionLocal() as db:
    row = db.scalar(select(UserPath).where(UserPath.path_key == "scientist"))
    row.started_on = today - timedelta(days=11)
    db.commit()
writing = next(s for k in a.get("/sub-classes").json()["classes"] for s in k["sub_classes"] if s.get("template_key") == "writing" or s["name"] == "Daily writing")
a.post("/daily-logs/batch", json={"days": [{"date": day(b), "custom": {str(writing["id"]): 35}} for b in range(12)]})
view = a.get("/books").json()
assert view["new"] == ["Deep Work"], view["new"]
mine = {b["key"]: b for b in view["books"]}
assert mine["deep_work"]["unlocked"] and mine["deep_work"]["via"] == "level"
assert not mine["spaced_repetition"]["unlocked"] and not mine["calling_home"]["unlocked"]
assert a.get("/books").json()["new"] == []  # only once
paths = a.get("/paths").json()["active"]
assert [(b["key"], b["unlocked"]) for b in paths[0]["books"]] == [("deep_work", True), ("spaced_repetition", False), ("memory_palace", False)], paths[0]["books"]

# Reading: 20 XP a chapter, 50 for finishing
before = a.get("/stats/level").json()["sources"].get("books", 0)
assert before == 0
for i in range(3):
    detail = a.post(f"/books/deep_work/chapters/{i}/read").json()
a.post("/books/deep_work/chapters/0/read")  # again: no double XP
assert all(ch["read"] and ch["text"] for ch in detail["chapters"]) and detail["chapters"][0]["source"]
assert a.post("/books/deep_work/chapters/9/read").status_code == 404
assert a.get("/stats/level").json()["sources"]["books"] == 3 * 20 + 50

# A 50-minute focus session adds to today's deep work hours and earns the practice XP; deleting takes it back
a.put(f"/daily-logs/{day(0)}", json={"work": {"deep": 1}})
detail = a.post("/books/deep_work/entries", json={"kind": "session", "data": {"minutes": 50, "quality": 4, "task": "Paper draft"}}).json()
assert a.get(f"/daily-logs/{day(0)}").json()["merged"]["work"]["deep"] == 1.83
level = a.get("/stats/level").json()
assert level["sources"]["books"] == 110 + 5 and any("Deep Work: practice" in t["reason"] for t in level["today"]), level["today"]
a.post("/books/deep_work/entries", json={"kind": "session", "data": {"minutes": 25, "quality": 3}})
assert a.get("/stats/level").json()["sources"]["books"] == 115  # practice counts once a day
session = detail["entries"][0]
assert session["kind"] == "session" and session["data"]["task"] == "Paper draft"
a.delete(f"/books/deep_work/entries/{session['id']}")
assert a.get(f"/daily-logs/{day(0)}").json()["merged"]["work"]["deep"] == 1.42  # 1 h + the 25 minutes left
assert a.post("/books/deep_work/entries", json={"kind": "session", "data": {"minutes": 30, "quality": 6}}).status_code == 400
assert a.post("/books/deep_work/entries", json={"kind": "card", "data": {"front": "x", "back": "y"}}).status_code == 400
assert a.post("/books/deep_work/entries", json={"kind": "session", "day": day(-1), "data": {"minutes": 30, "quality": 3}}).status_code == 400

# Spaced repetition: Leitner boxes; each review counts as retrieval practice
give("reader@example.com", "spaced_repetition")
retrieval = next(s for k in a.get("/sub-classes").json()["classes"] for s in k["sub_classes"] if s["name"] == "Retrieval practice")
card = a.post("/books/spaced_repetition/entries", json={"kind": "card", "data": {"front": "Mitochondria?", "back": "Powerhouse"}}).json()["entries"][0]
assert card["data"]["box"] == 1 and card["data"]["due"] == day(-1), card
card = next(e for e in a.post(f"/books/spaced_repetition/entries/{card['id']}/review", json={"remembered": True}).json()["entries"] if e["kind"] == "card")
assert card["data"]["box"] == 2 and card["data"]["due"] == day(-2), card
detail = a.post(f"/books/spaced_repetition/entries/{card['id']}/review", json={"remembered": False}).json()
card = next(e for e in detail["entries"] if e["kind"] == "card")
review = next(e for e in detail["entries"] if e["kind"] == "review")
assert card["data"]["box"] == 1 and review["data"] == {"cards": 2, "remembered": 1}, (card, review)
assert a.get(f"/daily-logs/{day(0)}").json()["merged"]["custom"][str(retrieval["id"])] == 2
assert a.patch(f"/books/spaced_repetition/entries/{card['id']}", json={"data": {"back": "The powerhouse of the cell"}}).status_code == 200

# Memory palace: a recall test feeds retrieval; deleting the palace takes its tests with it
give("reader@example.com", "memory_palace")
palace = a.post("/books/memory_palace/entries", json={"kind": "palace", "data": {"name": "Home", "loci": ["Door", "Mirror", "Sofa"]}}).json()["entries"][0]
assert a.post("/books/memory_palace/entries", json={"kind": "test", "data": {"palace_id": palace["id"], "items": 5, "recalled": 6}}).status_code == 400
assert a.post("/books/memory_palace/entries", json={"kind": "test", "data": {"palace_id": 999999, "items": 5, "recalled": 4}}).status_code == 400
a.post("/books/memory_palace/entries", json={"kind": "test", "data": {"palace_id": palace["id"], "items": 10, "recalled": 8}})
assert a.get(f"/daily-logs/{day(0)}").json()["merged"]["custom"][str(retrieval["id"])] == 10
assert a.post("/books/memory_palace/entries", json={"kind": "palace", "data": {"name": "Empty", "loci": []}}).status_code == 400
detail = a.delete(f"/books/memory_palace/entries/{palace['id']}").json()
assert detail["entries"] == [] and a.get(f"/daily-logs/{day(0)}").json()["merged"]["custom"][str(retrieval["id"])] == 2

# Decision journal: reviews open after 30 and 90 days
give("reader@example.com", "decision_journal")
decision = a.post("/books/decision_journal/entries", json={"kind": "decision", "day": day(31), "data": {
    "decision": "Hire a designer", "expected": "Launch in 6 weeks", "confidence": 70}}).json()["entries"][0]
r = a.patch(f"/books/decision_journal/entries/{decision['id']}", json={"data": {"review30": {"outcome": "Launched in 7 weeks", "right": True}}})
assert r.status_code == 200 and r.json()["entries"][0]["data"]["review30"]["right"] is True, r.text
r = a.patch(f"/books/decision_journal/entries/{decision['id']}", json={"data": {"review90": {"outcome": "x", "right": False}}})
assert r.status_code == 400 and "opens on" in r.json()["detail"], r.text
session_id = next(e["id"] for e in a.get("/books/deep_work").json()["entries"])
assert a.patch(f"/books/deep_work/entries/{session_id}", json={"data": {"minutes": 90}}).status_code == 400  # what happened stays

# Gifts: only friends, only books you have, one a week, not to someone who has it
b, c = client("gifted@example.com"), client("third@example.com")
code_b, code_c = b.get("/friends").json()["code"], c.get("/friends").json()["code"]
assert a.post("/books/deep_work/gift", json={"friend_id": b.get("/auth/me").json()["id"] if b.get("/auth/me").status_code == 200 else 0}).status_code == 404  # not friends yet
for other, code in ((b, code_b), (c, code_c)):
    a.post("/friends/requests", json={"code": code})
    other.post(f"/friends/requests/{other.get('/friends').json()['incoming'][0]['request_id']}/accept")
friend_ids = {f["code"]: f["id"] for f in a.get("/friends").json()["friends"]}
assert a.post("/books/calling_home/gift", json={"friend_id": friend_ids[code_b]}).status_code == 403  # not mine
r = a.post("/books/deep_work/gift", json={"friend_id": friend_ids[code_b]})
assert r.status_code == 200 and "on its way" in r.json()["message"] and r.json()["next_gift_on"] == day(-7), r.text
got = next(x for x in b.get("/books").json()["books"] if x["key"] == "deep_work")
assert got["unlocked"] and got["via"] == "gift" and got["gifted_by"], got
r = a.post("/books/spaced_repetition/gift", json={"friend_id": friend_ids[code_c]})
assert r.status_code == 400 and "One gift a week" in r.json()["detail"], r.text
r = b.post("/books/deep_work/gift", json={"friend_id": next(f["id"] for f in b.get("/friends").json()["friends"])})
assert r.status_code == 400 and "already has" in r.json()["detail"], r.text
# The gifted book works without the path: logging just doesn't feed a sub-class B doesn't have
assert b.post("/books/deep_work/entries", json={"kind": "session", "data": {"minutes": 30, "quality": 5}}).status_code == 201

# Calling home: a contact must be one of your people
give("reader@example.com", "calling_home")
person = a.post("/books/calling_home/entries", json={"kind": "person", "data": {"name": "Mum", "every_days": 3}}).json()["entries"][0]
assert a.post("/books/calling_home/entries", json={"kind": "contact", "data": {"person_id": person["id"], "how": "fax"}}).status_code == 400
assert a.post("/books/calling_home/entries", json={"kind": "contact", "data": {"person_id": person["id"], "how": "call"}}).status_code == 201

# Every book's unlock names real paths, and every tracker kind has its fields
from app.services import paths as path_service
for bk in book_service.BOOKS.values():
    assert all(p in path_service.PATHS for p, _ in bk.unlock) and all(k in book_service.ENTRY_FIELDS for k in bk.kinds), bk.key
    assert len(bk.chapters) >= 3 and all(ch.text for ch in bk.chapters)
print("books ok")
