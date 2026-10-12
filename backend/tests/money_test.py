"""Baby Steps in order and into Wealth; how others see your name."""
from fastapi.testclient import TestClient

from app.main import app

c = TestClient(app)


def ok(r, code=200):
    assert r.status_code == code, (r.request.method, r.request.url.path, r.status_code, r.text)
    return r.json() if r.content else None


h = {'Authorization': f"Bearer {ok(c.post('/auth/register', json={'email': 'm@example.com', 'password': 'password123'}), 201)['access_token']}"}
wlt = lambda: next(s for s in ok(c.get('/stats/character', headers=h))['stats'] if s['code'] == 'WLT')

# Nothing filled in: Baby Steps don't count yet, Wealth is the income goal alone
v = ok(c.get('/money/baby-steps', headers=h))
assert v['score'] is None and v['current'] == 1 and len(v['steps']) == 7
assert next(p for p in wlt()['components'] if p['name'] == 'Baby Steps')['score'] is None

# Step 1 halfway, with debts listed: on step 1, debts don't count yet
v = ok(c.put('/money/baby-steps', json={'saved': 500, 'debts': [
    {'name': 'Card', 'balance': 800, 'original': 1000}, {'name': 'Car', 'balance': 5000, 'original': 8000}]}, headers=h))
assert v['current'] == 1 and v['steps'][0]['progress'] == 0.5 and v['steps'][1]['note'].startswith('Next in the snowball: Card')
# 5 steps apply (no kids, renting: 1, 2, 3, 4, 7): step 1 at 0.5 of 5
assert v['score'] == round(0.5 / 5, 3), v['score']

# Starter fund done, debts half paid: on step 2
v = ok(c.put('/money/baby-steps', json={'saved': 1000, 'monthly_expenses': 2000, 'months': 3, 'invest_percent': 15}, headers=h))
assert v['current'] == 2
s2 = v['steps'][1]['progress']
# Investing 15% before being debt-free doesn't count (Ramsey's order)
assert v['score'] == round((1 + s2) / 5, 3), (v['score'], s2)

# Debt-free and the full fund: steps 4-6 together; renting means step 6 doesn't apply
v = ok(c.put('/money/baby-steps', json={'debts': [{'name': 'Card', 'balance': 0, 'original': 1000}, {'name': 'Car', 'balance': 0, 'original': 8000}],
                                         'saved': 6000}, headers=h))
assert v['current'] == 7 and v['steps'][5]['progress'] == 'n/a' and v['steps'][4]['progress'] == 'n/a'
assert v['score'] == round(4 / 5, 3), v['score']  # 1, 2, 3, 4 done; 7 not yet (not giving)
v = ok(c.put('/money/baby-steps', json={'giving': True}, headers=h))
assert v['current'] is None and v['score'] == 1.0
part = next(p for p in wlt()['components'] if p['name'] == 'Baby Steps')
assert part['score'] == 1.0 and part['weight'] == 50
ok(c.put('/money/baby-steps', json={'months': 9}, headers=h), 422)
print('baby steps ok; WLT', wlt()['score'])

# Names: nickname by default (or the code until there is one); name only when chosen
friend = {'Authorization': f"Bearer {ok(c.post('/auth/register', json={'email': 'm2@example.com', 'password': 'password123'}), 201)['access_token']}"}
ok(c.patch('/profile', json={'display_name': 'Nikoloz Girgvliani'}, headers=h))
board = lambda: next(r for r in ok(c.get('/friends/global', headers=friend))['top'] if r['id'] == ok(c.get('/friends', headers=h))['friends'] == [] or True)
names = lambda: [r['name'] for r in ok(c.get('/friends/global', headers=friend))['top']]
assert ok(c.get('/profile', headers=h))['public_name'] == 'nickname'
assert not any('Nikoloz' in n for n in names()), names()  # real name stays private by default
ok(c.patch('/profile', json={'nickname': 'NickG'}, headers=h))
assert 'NickG' in names()
ok(c.patch('/profile', json={'public_name': 'name'}, headers=h))
assert 'Nikoloz Girgvliani' in names()
ok(c.patch('/profile', json={'public_name': 'code'}, headers=h))
assert any(n.startswith('Player ') for n in names()) and 'NickG' not in names()
ok(c.patch('/profile', json={'public_name': 'everyone'}, headers=h), 422)
print('names ok:', names())
print('ALL OK')
