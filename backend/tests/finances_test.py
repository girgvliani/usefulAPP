"""Manage finances: subscriptions, due dates (month ends), autopay rolling, manual bills, totals."""
from datetime import date, timedelta

from fastapi.testclient import TestClient

from app.main import app
from app.services import finances

c = TestClient(app)


def ok(r, code=200):
    assert r.status_code == code, (r.request.method, r.request.url.path, r.status_code, r.text)
    return r.json() if r.content else None


# Month ends keep their day: 31 Jan → 28 Feb → 31 Mar; yearly 29 Feb → 28 Feb → 29 Feb
assert finances.after(date(2027, 1, 31), "monthly", 31) == date(2027, 2, 28)
assert finances.after(date(2027, 2, 28), "monthly", 31) == date(2027, 3, 31)
assert finances.after(date(2027, 11, 30), "quarterly", 30) == date(2028, 2, 29)
assert finances.after(date(2028, 2, 29), "yearly", 29) == date(2029, 2, 28)
assert finances.after(date(2027, 1, 1), "weekly", 1) == date(2027, 1, 8)

h = {'Authorization': f"Bearer {ok(c.post('/auth/register', json={'email': 'fin@example.com', 'password': 'password123'}), 201)['access_token']}"}
ok(c.patch('/profile', json={'currency': 'GEL'}, headers=h))  # amounts in your own currency by default
today = date.fromisoformat(ok(c.get('/stats/level', headers=h))['history'][-1]['date'])
v = ok(c.get('/finances', headers=h))
assert v['subscriptions'] == [] and v['totals']['monthly'] == {} and 'Streaming' in v['categories'] and v['cycles']['yearly'] == 'Yearly'
cur = v['currency']
assert cur == 'GEL'

# Netflix monthly in USD due in 3 days, gym in the profile currency yearly, Spotify weekly-ish test
v = ok(c.post('/finances/subscriptions', json={'name': 'Netflix', 'amount': 15.99, 'currency': 'USD', 'cycle': 'monthly',
                                             'next_due': str(today + timedelta(days=3)), 'category': 'Streaming'}, headers=h), 201)
v = ok(c.post('/finances/subscriptions', json={'name': 'Gym', 'amount': 600, 'cycle': 'yearly',
                                             'next_due': str(today + timedelta(days=40)), 'category': 'Gym & health'}, headers=h), 201)
v = ok(c.post('/finances/subscriptions', json={'name': 'Coffee club', 'amount': 10, 'cycle': 'weekly',
                                             'next_due': str(today + timedelta(days=1))}, headers=h), 201)
names = [s['name'] for s in v['subscriptions']]
assert names == ['Coffee club', 'Netflix', 'Gym'], names  # soonest first
netflix = next(s for s in v['subscriptions'] if s['name'] == 'Netflix')
assert netflix['status'] == 'soon' and netflix['days_until'] == 3 and netflix['monthly'] == 15.99 and netflix['yearly'] == 191.88
gym = next(s for s in v['subscriptions'] if s['name'] == 'Gym')
assert gym['currency'] == cur and gym['monthly'] == 50 and gym['status'] == 'later'
t = v['totals']
assert t['monthly']['USD'] == 15.99 and t['monthly'][cur] == round(50 + 10 * 52 / 12, 2), t
assert list(t['monthly'])[0] == cur  # your own currency first
# Next 30 days: Netflix once, coffee 5 times (days 1, 8, 15, 22, 29), gym not yet
assert t['next_30_days']['USD'] == 15.99 and t['next_30_days'][cur] == 50, t
assert [u['name'] for u in v['upcoming']].count('Coffee club') == 5
assert t['by_category'][0]['category'] == 'Gym & health'

# Autopay: a date in the past rolls forward by itself (and remembers the last charge)
sid = netflix['id']
v = ok(c.patch(f'/finances/subscriptions/{sid}', json={'next_due': str(today - timedelta(days=1))}, headers=h))
netflix = next(s for s in v['subscriptions'] if s['id'] == sid)
assert netflix['days_until'] > 20 and netflix['last_paid'] == str(today - timedelta(days=1)) and netflix['status'] != 'overdue'

# A manual bill stays overdue until paid; paid moves it one cycle on
v = ok(c.post('/finances/subscriptions', json={'name': 'Rent', 'amount': 1200, 'cycle': 'monthly', 'autopay': False,
                                             'next_due': str(today - timedelta(days=2)), 'category': 'Rent & utilities'}, headers=h), 201)
rent = next(s for s in v['subscriptions'] if s['name'] == 'Rent')
assert rent['status'] == 'overdue' and rent['days_until'] == -2
assert any(u['name'] == 'Rent' and u['days_until'] == -2 for u in v['upcoming'])
v = ok(c.post(f"/finances/subscriptions/{rent['id']}/paid", headers=h))
rent = next(s for s in v['subscriptions'] if s['name'] == 'Rent')
assert rent['status'] != 'overdue' and rent['last_paid'] == str(today - timedelta(days=2))

# Paused ones drop out of the totals and sort last
v = ok(c.patch(f"/finances/subscriptions/{gym['id']}", json={'active': False}, headers=h))
assert v['subscriptions'][-1]['name'] == 'Gym' and v['subscriptions'][-1]['status'] == 'paused'
assert v['totals']['monthly'][cur] == round(10 * 52 / 12 + 1200, 2), v['totals']
assert v['totals']['active'] == 3

# Bad input, other people, delete
assert c.post('/finances/subscriptions', json={'name': 'X', 'amount': -1, 'next_due': str(today)}, headers=h).status_code == 422
assert c.post('/finances/subscriptions', json={'name': 'X', 'amount': 1, 'cycle': 'daily', 'next_due': str(today)}, headers=h).status_code == 422
h2 = {'Authorization': f"Bearer {ok(c.post('/auth/register', json={'email': 'fin2@example.com', 'password': 'password123'}), 201)['access_token']}"}
assert c.delete(f'/finances/subscriptions/{sid}', headers=h2).status_code == 404
v = ok(c.delete(f'/finances/subscriptions/{sid}', headers=h))
assert 'Netflix' not in [s['name'] for s in v['subscriptions']] and 'USD' not in v['totals']['monthly']
# Baby Steps untouched
assert ok(c.get('/money/baby-steps', headers=h))['current'] == 1
print('finances ok')
