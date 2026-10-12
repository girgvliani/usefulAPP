"""Global leaderboard: everyone by default, ranked by XP, level/title/XP only, hiding works."""
from datetime import date, timedelta

from fastapi.testclient import TestClient

from app.main import app

c = TestClient(app)


def ok(r, code=200):
    assert r.status_code == code, (r.request.method, r.request.url.path, r.status_code, r.text)
    return r.json() if r.content else None


def account(email, name, days):
    h = {'Authorization': f"Bearer {ok(c.post('/auth/register', json={'email': email, 'password': 'password123'}), 201)['access_token']}"}
    ok(c.patch('/profile', json={'display_name': name, 'public_name': 'name'}, headers=h))
    today = date.today()
    logs = [{'date': (today - timedelta(days=i)).isoformat(), 'sleep': {'hours': 8}, 'body': {'steps': 12000}} for i in range(days)]
    if logs:
        ok(c.post('/daily-logs/batch', json={'days': logs}, headers=h))
    return h


A = account('ga@example.com', 'Ana', 10)
B = account('gb@example.com', 'Ben', 3)
C = account('gc@example.com', 'Cat', 0)

assert ok(c.get('/friends', headers=A))['sharing']['leaderboard'] is True  # on by default
board = ok(c.get('/friends/global', headers=B))
assert board['players'] == 3 and [r['name'] for r in board['top']] == ['Ana', 'Ben', 'Cat'], board
assert [r['rank'] for r in board['top']] == [1, 2, 3] and board['top'][0]['xp'] >= board['top'][1]['xp']
assert board['you']['name'] == 'Ben' and board['you']['rank'] == 2
assert set(board['top'][0]) == {'id', 'name', 'photo_url', 'level', 'title', 'xp', 'me', 'rank', 'badge'}  # nothing else, no email
assert 'ga@example.com' not in str(board)
print('board:', [(r['rank'], r['name'], r['level'], r['xp']) for r in board['top']])

# Ana hides: gone for others, and she sees her own row unranked
ok(c.patch('/friends/sharing', json={'leaderboard': False}, headers=A))
board = ok(c.get('/friends/global', headers=B))
assert [r['name'] for r in board['top']] == ['Ben', 'Cat'] and board['players'] == 2 and board['you']['rank'] == 1
mine = ok(c.get('/friends/global', headers=A))
assert mine['you']['name'] == 'Ana' and mine['you']['rank'] is None and all(not r['me'] for r in mine['top'])
# Hiding from the global board doesn't touch the friend switches
assert ok(c.get('/friends', headers=A))['sharing'] == {'level': False, 'stats': False, 'streaks': False, 'goals': False, 'achievements': False, 'leaderboard': False}
print('ALL OK')
