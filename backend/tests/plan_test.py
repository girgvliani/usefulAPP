"""The Plan screens' calls: skills, quests, milestones, projects, end to end on a fresh account."""
from datetime import date, timedelta

from fastapi.testclient import TestClient

from app.main import app

c = TestClient(app)


def ok(r, code=200):
    assert r.status_code == code, (r.request.method, r.request.url.path, r.status_code, r.text)
    return r.json() if r.content else None


login = {'Authorization': f"Bearer {ok(c.post('/auth/register', json={'email': 'plan@example.com', 'password': 'password123'}), 201)['access_token']}"}
h = {'Authorization': f"Bearer {ok(c.post('/devices', json={'name': 'S23'}, headers=login), 201)['token']}"}
# XP without achievement bonuses (finishing things also earns achievements)
xp = lambda: (lambda lv: lv['xp'] - lv['sources']['achievements'])(ok(c.get('/stats/level', headers=h)))

# skills
skills = ok(c.get('/life-areas', headers=h))
work = next(s for s in skills if s['name'] == 'Career - Work Skills')
kotlin = ok(c.post('/life-areas', json={'name': 'Career - Kotlin'}, headers=h), 201)
assert ok(c.patch(f"/life-areas/{kotlin['id']}", json={'name': 'Career - Android'}, headers=h))['name'] == 'Career - Android'
assert c.patch(f"/life-areas/{next(s for s in skills if s['name'] == 'Social Balance')['id']}", json={'name': 'x'}, headers=h).status_code == 409

# quests: on time = 1.5x
start = xp()
due = (date.today() + timedelta(days=3)).isoformat()
q = ok(c.post('/todos', json={'task': 'Read docs', 'area_id': kotlin['id'], 'base_xp': 50, 'deadline': due}, headers=h), 201)
q = ok(c.patch(f"/todos/{q['id']}", json={'task': 'Read the docs', 'base_xp': 40}, headers=h))
assert q['task'] == 'Read the docs' and q['base_xp'] == 40
assert c.delete(f"/life-areas/{kotlin['id']}", headers=h).status_code == 409  # a quest uses it
ok(c.post(f"/todos/{q['id']}/complete", headers=h))
assert xp() - start == 60, xp() - start
print('skills + quests ok')

# milestones: XP shared over every skill
m = ok(c.post('/milestones', json={'description': 'Run a 5K', 'xp_reward': 500}, headers=h), 201)
m = ok(c.patch(f"/milestones/{m['key']}", json={'description': 'Run a 5K without stopping', 'xp_reward': 1000}, headers=h))
before = xp()
ok(c.post(f"/milestones/{m['key']}/complete", headers=h))
n = len(ok(c.get('/life-areas', headers=h)))
assert xp() - before == 1000 // n * n
print('milestones ok')

# projects: income + Work Skills XP (the default "Career - Work Skills" counts)
p = ok(c.post('/projects', json={'name': 'Cafe site', 'value': 800, 'deadline': due}, headers=h), 201)
before = xp()
ok(c.post(f"/projects/{p['id']}/complete", headers=h))
gained = xp() - before
assert gained == int(80 * 1.5), gained
assert ok(c.get('/income', headers=h))['current_month_earnings'] == 800
ok(c.delete(f"/projects/{p['id']}", headers=h), 204)
assert ok(c.get('/income', headers=h))['current_month_earnings'] == 0
print('projects ok, +%d XP to Work Skills' % gained)
