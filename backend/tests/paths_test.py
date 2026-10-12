"""Paths (Phase 11.2): start a path, baseline targets, path XP and chapters, weekly adjustment, leaving."""
from datetime import date, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database import SessionLocal
from app.main import app
from app.models import SubClass, UserPath

c = TestClient(app)
token = c.post("/auth/register", json={"email": "path@example.com", "password": "path-password-1"}).json()["access_token"]
c.headers["Authorization"] = f"Bearer {token}"
today = date.today()
day = lambda back: (today - timedelta(days=back)).isoformat()

view = c.get("/paths").json()
assert view["active"] == [] and {p["key"] for p in view["available"]} == {"scientist", "businessman", "father", "mother", "son", "daughter"}, view
assert c.post("/paths/astronaut").status_code == 404

# Two weeks of deep work at 2 h a day before starting: the target starts a step above that, not at 3 h
c.post("/daily-logs/batch", json={"days": [{"date": day(b), "work": {"deep": 2}} for b in range(1, 11)]})
view = c.post("/paths/scientist").json()
sci = view["active"][0]
assert sci["key"] == "scientist" and sci["level"] == 0 and sci["title"] == "Curious Mind", sci
deep = next(s for s in sci["halves"]["work"] if s["name"] == "Deep work")
assert deep["target"] == 2.2, deep
assert len(sci["halves"]["work"]) == 4 and len(sci["halves"]["smart"]) == 3
assert all(s["why"] for s in sci["halves"]["work"] + sci["halves"]["smart"])
assert any(s["source"] == "Boice, 1989" for s in sci["halves"]["work"])
mine = {s["name"]: s for k in c.get("/sub-classes").json()["classes"] for s in k["sub_classes"] if not s["builtin"]}
assert mine["Daily writing"]["path_key"] == "scientist" and mine["Daily writing"]["class_key"] == "discipline"

# Pretend the path started 10 days ago, then log 8 days of writing in a row and 3 papers this week
with SessionLocal() as db:
    row = db.scalar(select(UserPath).where(UserPath.path_key == "scientist"))
    row.started_on = today - timedelta(days=10)
    db.commit()
writing, papers = mine["Daily writing"]["id"], mine["Reading the literature"]["id"]
for b in range(8):
    assert c.put(f"/daily-logs/{day(b)}", json={"custom": {str(writing): 35}}).status_code == 200
c.put(f"/daily-logs/{day(0)}", json={"custom": {str(writing): 35, str(papers): 3}})

sci = c.get("/paths").json()["active"][0]
chapters = {ch["key"]: ch for ch in sci["chapters"]}
assert chapters["writing_week"]["done"] and not chapters["writing_month"]["done"], chapters["writing_week"]
assert chapters["writing_month"]["value"] == 8
print("Scientist:", sci["xp"], "XP, LV", sci["level"], sci["title"], "| chapters done:", [k for k, ch in chapters.items() if ch["done"]])
# 8 writing days × 10 + papers week 40 (only if this week already has 3) + writing week chapter 75
expected = 8 * 10 + 40 + 75
assert sci["xp"] == expected, (sci["xp"], expected)

level = c.get("/stats/level").json()
assert level["sources"]["paths"] == expected, level["sources"]
assert any("Daily writing" in t["reason"] for t in level["today"]), level["today"]

# The weekly check: 7 of 7 days on target last week → 10% harder
with SessionLocal() as db:
    sub = db.get(SubClass, writing)
    sub.adjusted_at = today - timedelta(days=8)
    db.commit()
view = c.get("/paths").json()
assert any(n.startswith("Daily writing: 30 → 33") for n in view["adjusted"]), view["adjusted"]
assert next(s for s in view["active"][0]["halves"]["work"] if s["name"] == "Daily writing")["target"] == 33
assert c.get("/paths").json()["adjusted"] == []  # not again within the week

# A path's sub-class can be switched off but not deleted on its own
assert c.delete(f"/sub-classes/{writing}").status_code == 400

# Up to three paths; leaving keeps the XP, restarting brings the same sub-classes back
c.post("/paths/businessman")
assert {p["key"] for p in c.get("/paths").json()["active"]} == {"scientist", "businessman"}
view = c.delete("/paths/scientist").json()
assert [p["key"] for p in view["active"]] == ["businessman"] and any(p["key"] == "scientist" and p["started_before"] for p in view["available"])
assert c.get("/stats/level").json()["sources"]["paths"] == expected  # earned XP stays
assert not any(s["path_key"] == "scientist" and s["active"] for k in c.get("/sub-classes").json()["classes"] for s in k["sub_classes"] if not s["builtin"])
view = c.post("/paths/scientist").json()
again = {s["name"]: s for k in c.get("/sub-classes").json()["classes"] for s in k["sub_classes"] if not s["builtin"]}
assert again["Daily writing"]["id"] == writing and again["Daily writing"]["active"]
assert c.delete("/paths/astronaut").status_code == 404
# ---- Family roles (11.3): outside the three, one parent and one child role at a time ----
from app.services import paths as path_service
for p in path_service.PATHS.values():  # every chapter reads a sub-class of its own path; every sub-class says why
    keys = {sub.key for sub in p.subs}
    assert all(ch.sub in keys for ch in p.chapters), p.key
    assert all(sub.why for sub in p.subs), p.key
assert c.post("/paths/father").status_code == 200  # next to Scientist and Businessman
assert c.post("/paths/son").status_code == 200
r = c.post("/paths/mother")
assert r.status_code == 400 and "Father" in r.json()["detail"], r.text
assert c.post("/paths/daughter").status_code == 400
view = c.get("/paths").json()
groups = {p["key"]: p["group"] for p in view["active"]}
assert groups == {"scientist": "calling", "businessman": "calling", "father": "parent", "son": "child"}, groups
father = next(p for p in view["active"] if p["key"] == "father")
assert father["title"] == "Father" and len(father["halves"]["work"]) == 3 and len(father["halves"]["smart"]) == 3
calm = next(s for s in father["halves"]["smart"] if s["name"] == "Calm under pressure")
assert calm["kind"] == "rating" and calm["target"] is None and calm["self_rated"]
# A self-rating counts from 4 and earns half (5 XP); a 3 earns nothing
c.put(f"/daily-logs/{day(0)}", json={"custom": {str(calm['id']): 4}})
assert next(p for p in c.get("/paths").json()["active"] if p["key"] == "father")["today_xp"] == 5
c.put(f"/daily-logs/{day(0)}", json={"custom": {str(calm['id']): 3}})
assert next(p for p in c.get("/paths").json()["active"] if p["key"] == "father")["today_xp"] == 0
c.delete("/paths/father")
assert c.post("/paths/mother").status_code == 200  # free once Father is left
print("paths ok")
