"""Sub-classes (Phase 11.1): your own stats in the six classes, scoring, hiding built-ins, check-in answers."""
from datetime import date, timedelta

from fastapi.testclient import TestClient

from app.main import app

c = TestClient(app)
token = c.post("/auth/register", json={"email": "sub@example.com", "password": "sub-password-1"}).json()["access_token"]
c.headers["Authorization"] = f"Bearer {token}"
today = date.today()
day = lambda back: (today - timedelta(days=back)).isoformat()

# --- creating, one of each kind --------------------------------------------------------------
def make(**body):
    r = c.post("/sub-classes", json=body)
    assert r.status_code == 201, r.text
    return r.json()

reading = make(class_key="social", name="Reading to the kids", icon="📖", kind="number", unit="min", target=20)
gym = make(class_key="physical", name="Gym", icon="🏋️", kind="yesno", period="week", target=3)
patience = make(class_key="discipline", name="Patience", icon="🧘", kind="rating")
steps = make(class_key="physical", name="Walking", kind="field", field="body.steps", target=8000)
sugar = make(class_key="physical", name="Sugar", kind="number", unit="g", target=30, better="less")
assert patience["self_rated"] and not reading["self_rated"]

# Settings that don't fit together are refused
for bad in [dict(kind="number"), dict(kind="field", field="sleep.bed", target=1), dict(kind="field", field="nope.x", target=1),
            dict(kind="rating", period="week"), dict(kind="yesno", period="week")]:
    r = c.post("/sub-classes", json={"class_key": "mental", "name": "x", **bad})
    assert r.status_code == 400, (bad, r.text)
assert c.post("/sub-classes", json={"class_key": "nowhere", "name": "x", "kind": "rating"}).status_code == 422

# --- answers in the check-in (manual) and phone data (auto) ----------------------------------
answers = {  # back: (reading min, gym, patience, sugar g)
    0: (25, True, 4, 20), 1: (10, False, 2, 50), 2: (20, True, 5, 30), 3: (0, True, 3, 60),
}
for back, (minutes, went, rating, grams) in answers.items():
    r = c.put(f"/daily-logs/{day(back)}", json={"custom": {str(reading["id"]): minutes, str(gym["id"]): went,
                                                           str(patience["id"]): rating, str(sugar["id"]): grams}})
    assert r.status_code == 200, r.text
c.post("/daily-logs/batch?source=auto", json={"days": [{"date": day(b), "body": {"steps": s}} for b, s in [(0, 10000), (1, 4000)]]})
assert c.put(f"/daily-logs/{day(0)}", json={"custom": {"abc": 1}}).status_code == 422
assert c.put(f"/daily-logs/{day(0)}", json={"custom": {"5": -1}}).status_code == 422

# --- scores -----------------------------------------------------------------------------------
sheet = c.get("/stats/character").json()
stats = {s["code"]: s for s in sheet["stats"]}
classes = {k["key"]: k for k in sheet["categories"]}
code = lambda sub: sub["code"]
print({stats[code(s)]["name"]: (stats[code(s)]["score"], stats[code(s)]["components"][0]["note"]) for s in (reading, gym, patience, steps, sugar)})
assert stats[code(reading)]["score"] == round(100 * (1 + 0.5 + 1 + 0) / 4)  # 25,10,20,0 min against 20
assert stats[code(gym)]["score"] == 100  # 3 gym days this week, target 3
assert stats[code(patience)]["score"] == round(100 * ((4 - 1) / 4 + (2 - 1) / 4 + 1 + (3 - 1) / 4) / 4)
assert stats[code(patience)]["self_rated"] and stats[code(patience)]["icon"] == "🧘"
assert stats[code(steps)]["score"] == round(100 * (1 + 0.5) / 2)
assert stats[code(sugar)]["score"] == round(100 * (1 + (1 - 20 / 30) + 1 + 0) / 4)  # 20, 50, 30, 60 g against ≤30
assert code(reading) in classes["social"]["stats"] and code(gym) in classes["physical"]["stats"]
assert classes["social"]["score"] == round((stats["SOC"]["score"] + stats[code(reading)]["score"]) / 2) if stats["SOC"]["score"] is not None \
    else classes["social"]["score"] == stats[code(reading)]["score"]
print("classes:", {k: (v["score"], v["stats"]) for k, v in classes.items()})

# --- hiding a built-in stat ---------------------------------------------------------------------
view = c.put("/sub-classes/builtin/DIS", json={"active": False}).json()
assert not next(s for k in view["classes"] if k["key"] == "discipline" for s in k["sub_classes"] if s.get("code") == "DIS")["active"]
sheet = c.get("/stats/character").json()
discipline = next(k for k in sheet["categories"] if k["key"] == "discipline")
assert "DIS" not in discipline["stats"] and discipline["score"] == stats[code(patience)]["score"], discipline
assert c.put("/sub-classes/builtin/NOPE", json={"active": False}).status_code == 400
c.put("/sub-classes/builtin/DIS", json={"active": True})
assert "DIS" in next(k for k in c.get("/stats/character").json()["categories"] if k["key"] == "discipline")["stats"]

# --- history, the morning tip and friends' standard view still work -------------------------------
history = c.get(f"/stats/character/history?start={day(6)}").json()
assert len(history) == 7 and code(reading) in history[-1]["scores"], history[-1]
tip = c.get("/stats/tip?when=morning")
assert tip.status_code == 200, tip.text
print("tip:", tip.json()["title"])

# --- editing, switching off, deleting --------------------------------------------------------------
r = c.patch(f"/sub-classes/{reading['id']}", json={"target": 10, "name": "Reading together"})
assert r.status_code == 200 and r.json()["target"] == 10, r.text
assert c.patch(f"/sub-classes/{reading['id']}", json={"kind": "field"}).status_code == 400  # a field needs a field
c.patch(f"/sub-classes/{gym['id']}", json={"active": False})
codes = {s["code"] for s in c.get("/stats/character").json()["stats"]}
assert code(gym) not in codes and code(reading) in codes
assert c.delete(f"/daily-logs/{day(0)}?source=manual&section=custom&field={reading['id']}").status_code == 204
assert c.delete(f"/daily-logs/{day(0)}?source=manual&section=custom&field=abc").status_code == 400
assert c.delete(f"/sub-classes/{sugar['id']}").status_code == 204
assert c.delete(f"/sub-classes/{sugar['id']}").status_code == 404
view = c.get("/sub-classes").json()
assert view["custom_count"] == 4 and len(view["classes"]) == 6 and any(f["field"] == "body.steps" for f in view["fields"])

# --- turning parts off is free from the start ---------------------------------------------------------
custom = c.get("/customize").json()
assert next(u for u in custom["ladder"] if u["key"] == "parts_off")["unlocked"]
assert not any(u["key"] in ("questions", "own_stats") for u in custom["ladder"])

# Another user can't touch them
other = TestClient(app)
other.headers["Authorization"] = "Bearer " + other.post("/auth/register", json={"email": "other@example.com", "password": "other-password-1"}).json()["access_token"]
assert other.patch(f"/sub-classes/{reading['id']}", json={"name": "mine"}).status_code == 404
print("sub-classes ok")
