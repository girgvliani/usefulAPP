import httpx
c = httpx.Client(base_url="http://127.0.0.1:8765", timeout=30)
t = c.post("/auth/login", json={"email": "demo@example.com", "password": "demo-password-1"}).json()["access_token"]
c.headers["Authorization"] = f"Bearer {t}"
all_ = c.get("/achievements").json()
earned = [a for a in all_["achievements"] if a["earned_at"]]
locked = [a for a in all_["achievements"] if not a["earned_at"]]
print("badge before:", all_["badge"], c.get("/profile").json()["badge"])
print("locked ->", c.put("/achievements/badge", json={"key": locked[0]["key"]}).status_code, "(400 expected)")
print("bogus ->", c.put("/achievements/badge", json={"key": "nope"}).status_code)
best = sorted(earned, key=lambda a: -a["tier"])[0]
print("pick", best["key"], "->", c.put("/achievements/badge", json={"key": best["key"]}).json())
print("profile:", c.get("/profile").json()["badge"])
print("overview badge:", c.get("/achievements").json()["badge"])
g = c.get("/friends/global").json()
print("global me:", [r["badge"] for r in g["top"] if r["me"]])
# Ben accepts? Ben sent the request; accept it as demo
inc = c.get("/friends").json()["incoming"]
if inc: c.post(f"/friends/requests/{inc[0]['request_id']}/accept")
b = httpx.Client(base_url="http://127.0.0.1:8765", timeout=30)
bt = b.post("/auth/login", json={"email": "ben@example.com", "password": "ben-password-1"}).json()["access_token"]
b.headers["Authorization"] = f"Bearer {bt}"
print("Ben sees demo:", [f["badge"] for f in b.get("/friends").json()["friends"]])
print("Ben's board:", [(r["name"], r.get("badge")) for r in b.get("/friends/leaderboard").json()])
print("clear ->", c.put("/achievements/badge", json={"key": None}).json(), c.get("/profile").json()["badge"])
