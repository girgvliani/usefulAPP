"""Fasting: intermittent and extended, timing, the eating window, XP, Discipline/Health, achievements."""
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.main import app

c = TestClient(app)


def ok(r, code=200):
    assert r.status_code == code, (r.request.method, r.request.url.path, r.status_code, r.text)
    return r.json() if r.content else None


h = {'Authorization': f"Bearer {ok(c.post('/auth/register', json={'email': 'fast@example.com', 'password': 'password123'}), 201)['access_token']}"}
now = datetime.now(timezone.utc)
iso = lambda t: t.isoformat()
stat = lambda code: next(s for s in ok(c.get('/stats/character', headers=h))['stats'] if s['code'] == code)
parts = lambda code: {p['name'] for p in stat(code)['components']}

# Discipline needs 3+ days of check-ins before it scores anything
today = ok(c.get('/stats/level', headers=h))['history'][-1]['date']
from datetime import date
for back in range(4):
    ok(c.put(f"/daily-logs/{date.fromisoformat(today) - timedelta(days=back)}?source=manual", json={'body': {'shower': True}}, headers=h))

# Nothing yet: presets and stages, no fasting parts in anyone's stats
v = ok(c.get('/fasts', headers=h))
assert v['active'] is None and v['history'] == [] and [p['name'] for p in v['presets']['intermittent']][:2] == ['14:10', '16:8']
assert v['presets']['extended'][0]['hours'] == 24 and v['stages'][0]['name'] == 'Digesting'
assert 'Fasts kept' not in parts('DIS') and 'Fasting rhythm' not in parts('H')

# A 16:8 started 10 hours ago: running, stage, goal end, eating window after it
f = ok(c.post('/fasts', json={'kind': 'intermittent', 'goal_hours': 16, 'started_at': iso(now - timedelta(hours=10))}, headers=h), 201)
assert f['active'] and f['completed'] is None and 9.9 < f['hours'] < 10.1 and 0.62 < f['progress'] < 0.63
assert f['stage']['name'] == 'Blood sugar settling' and f['stage']['next'] == {'at_hours': 12, 'name': 'Fat burning rising'}
goal_end = datetime.fromisoformat(f['goal_end'])
assert abs((goal_end - (now + timedelta(hours=6))).total_seconds()) < 5
w = f['eating_window']
assert datetime.fromisoformat(w['closes']) - datetime.fromisoformat(w['opens']) == timedelta(hours=8)
# Only one at a time; no future starts
assert c.post('/fasts', json={'kind': 'extended', 'goal_hours': 24}, headers=h).status_code == 409
assert ok(c.get('/fasts', headers=h))['active']['id'] == f['id']

# Moved the start back 7 hours (forgot to start it): now 17h, end it → completed, XP, achievements
f = ok(c.patch(f"/fasts/{f['id']}", json={'started_at': iso(now - timedelta(hours=17))}, headers=h))
assert 16.9 < f['hours'] < 17.1
before = ok(c.get('/stats/level', headers=h))
f = ok(c.post(f"/fasts/{f['id']}/end", headers=h))
assert f['completed'] is True and not f['active'] and f['day']
lv = ok(c.get('/stats/level', headers=h))
assert any(i['reason'] == 'Fasted 17h' and i['xp'] == 17 for i in lv['today']), lv['today']
new = {a['key'] for a in lv['new_achievements']}
assert {'fast_first', 'fast_16'} <= new and 'fast_24' not in new, new
assert c.post(f"/fasts/{f['id']}/end", headers=h).status_code == 400  # already over

# The stats: DIS "Fasts kept", H "Fasting rhythm" now count
dis = next(p for p in stat('DIS')['components'] if p['name'] == 'Fasts kept')
assert dis['score'] == 1 and dis['note'].startswith('1/1'), dis
hr = next(p for p in stat('H')['components'] if p['name'] == 'Fasting rhythm')
assert hr['score'] == 0.2 and hr['weight'] == 10, hr

# An extended fast broken early: not completed, no XP, DIS drops to 1/2
e = ok(c.post('/fasts', json={'kind': 'extended', 'goal_hours': 48, 'started_at': iso(now - timedelta(hours=30))}, headers=h), 201)
assert e['eating_window'] is None and e['stage']['name'] == 'Deep fast'
e = ok(c.post(f"/fasts/{e['id']}/end", headers=h))
assert e['completed'] is False
dis = next(p for p in stat('DIS')['components'] if p['name'] == 'Fasts kept')
assert dis['score'] == 0.5, dis
# ...but 30 hours is still the longest: 24h achievement? No: only completed fasts count
assert 'fast_24' not in {a['key'] for a in ok(c.get('/stats/level', headers=h))['new_achievements']}
ach = {a['key']: a for a in ok(c.get('/achievements', headers=h))['achievements']}
assert ach['fast_24']['value'] == 17 or ach['fast_24']['value'] >= 16.9

# Bad times are refused
assert c.post('/fasts', json={'kind': 'intermittent', 'goal_hours': 16, 'started_at': iso(now + timedelta(hours=2))}, headers=h).status_code == 400
assert c.post('/fasts', json={'kind': 'intermittent', 'goal_hours': 0.5}, headers=h).status_code == 422
r = ok(c.post('/fasts', json={'kind': 'intermittent', 'goal_hours': 16}, headers=h), 201)
assert c.post(f"/fasts/{r['id']}/end", json={'ended_at': iso(now - timedelta(hours=1))}, headers=h).status_code == 400  # before the start
ok(c.delete(f"/fasts/{r['id']}", headers=h), 204)
assert ok(c.get('/fasts', headers=h))['active'] is None

# History and totals
v = ok(c.get('/fasts', headers=h))
assert len(v['history']) == 2 and v['totals'] == {'completed': 1, 'this_week': 1, 'longest_hours': v['totals']['longest_hours']}
assert 29.9 < v['totals']['longest_hours'] < 30.1

# Someone else can't touch your fasts
h2 = {'Authorization': f"Bearer {ok(c.post('/auth/register', json={'email': 'other@example.com', 'password': 'password123'}), 201)['access_token']}"}
assert c.delete(f"/fasts/{e['id']}", headers=h2).status_code == 404
print('fasting ok')
