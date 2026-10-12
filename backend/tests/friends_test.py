"""Friends: codes and emails, requests, sharing switches (all off by default), leaderboard, privacy."""
from datetime import date, timedelta

from fastapi.testclient import TestClient

from app.main import app

c = TestClient(app)


def ok(r, code=200):
    assert r.status_code == code, (r.request.method, r.request.url.path, r.status_code, r.text)
    return r.json() if r.content else None


def account(email, name):
    h = {'Authorization': f"Bearer {ok(c.post('/auth/register', json={'email': email, 'password': 'password123'}), 201)['access_token']}"}
    ok(c.patch('/profile', json={'display_name': name, 'public_name': 'name'}, headers=h))
    return h


A, B, C = account('a@example.com', 'Ana'), account('b@example.com', 'Ben'), account('c@example.com', 'Cat')

# Give B some data so there's something to share
today = date.today()
days = [{'date': (today - timedelta(days=i)).isoformat(), 'sleep': {'hours': 7.5}, 'body': {'steps': 9000, 'weight_kg': 100 - i * 0.2},
         'screen': {'short_video_min': 20, 'social_min': 20, 'total_min': 150, 'night_min': 0, 'unlocks': 50}} for i in range(9)]
ok(c.post('/daily-logs/batch', json={'days': days}, headers=B))
ok(c.post('/goals', json={'type': 'weight', 'target_value': 90, 'start_value': 101}, headers=B), 201)

a = ok(c.get('/friends', headers=A))
assert len(a['code']) == 9 and a['code'][4] == '-' and a['sharing'] == {'level': False, 'stats': False, 'streaks': False, 'goals': False, 'achievements': False, 'leaderboard': True}
assert a['friends'] == [] and a['incoming'] == []

# Errors say what's wrong
assert 'code' in ok(c.post('/friends/requests', json={'code': 'ZZZZ-ZZZZ'}, headers=B), 404)['detail']
assert ok(c.post('/friends/requests', json={'code': a['code']}, headers=A), 400)['detail'] == "That's you"

# B asks A by code (lowercase, no dash works too); A accepts
r = ok(c.post('/friends/requests', json={'code': a['code'].replace('-', '').lower()}, headers=B), 201)
assert r['status'] == 'pending' and r['name'] == 'Ana'
assert 'already sent' in ok(c.post('/friends/requests', json={'code': a['code']}, headers=B), 409)['detail']
incoming = ok(c.get('/friends', headers=A))['incoming']
assert [x['name'] for x in incoming] == ['Ben'] and 'email' not in incoming[0]
ok(c.post(f"/friends/requests/{incoming[0]['request_id']}/accept", headers=B), 403)  # only the one asked can accept
ok(c.post(f"/friends/requests/{incoming[0]['request_id']}/accept", headers=A))

# Nothing is shared until B turns it on
view = ok(c.get('/friends', headers=A))['friends'][0]
assert view['name'] == 'Ben' and set(view) == {'id', 'name', 'code', 'shares', 'photo_url', 'badge'}, view
ok(c.patch('/friends/sharing', json={'level': True, 'stats': True}, headers=B))
view = ok(c.get('/friends', headers=A))['friends'][0]
assert 'level' in view and 'stats' in view and 'goals' not in view and 'streaks' not in view
assert len(view['stats']['categories']) == 6 and len(view['stats']['stats']) == 9
print('B shares level + stats:', view['level'], 'TOTAL', view['stats']['total'], view['stats']['total_grade'], 'change', view['stats']['total_change'])

# Goals: progress only, never the numbers
ok(c.patch('/friends/sharing', json={'goals': True, 'streaks': True}, headers=B))
view = ok(c.get('/friends', headers=A))['friends'][0]
assert view['goals'][0]['title'] == 'Lose weight' and '101' not in str(view['goals']) and '90' not in view['goals'][0]['title']
assert view['streaks'] and 'rule' not in view['streaks'][0]
print('goals as A sees them:', view['goals'])

# B asks C by email; C asking back accepts it
ok(c.post('/friends/requests', json={'email': 'C@Example.com'}, headers=B), 201)
assert ok(c.post('/friends/requests', json={'code': ok(c.get('/friends', headers=B))['code']}, headers=C), 201)['status'] == 'accepted'
assert sorted(f['name'] for f in ok(c.get('/friends', headers=B))['friends']) == ['Ana', 'Cat']
# A and C aren't friends: A doesn't see C
assert [f['name'] for f in ok(c.get('/friends', headers=A))['friends']] == ['Ben']

# Leaderboard: me with everything, friends with what they share
board = ok(c.get('/friends/leaderboard', headers=A))
assert [r['name'] for r in board] == ['Ana', 'Ben'] and board[0]['me'] and 'stats' in board[0] and 'level' in board[0]
assert 'goals' not in board[1] and 'streaks' not in board[1]
ok(c.patch('/friends/sharing', json={'stats': False}, headers=B))
assert 'stats' not in ok(c.get('/friends/leaderboard', headers=A))[1]

# A declines nothing pending; C cancels a request to A
ok(c.post('/friends/requests', json={'email': 'a@example.com'}, headers=C), 201)
out = ok(c.get('/friends', headers=C))['outgoing']
ok(c.delete(f"/friends/requests/{out[0]['request_id']}", headers=C), 204)
assert ok(c.get('/friends', headers=A))['incoming'] == []

# Unfriend: both stop seeing each other
ok(c.delete(f"/friends/{view['id']}", headers=A), 204)
assert ok(c.get('/friends', headers=A))['friends'] == []
assert [f['name'] for f in ok(c.get('/friends', headers=B))['friends']] == ['Cat']
ok(c.delete(f"/friends/{view['id']}", headers=A), 404)
print('ALL OK')
