"""Unlock ladder, turning parts off (LV 7+), re-scoring, standard scores for friends, daily tips."""
from datetime import date, timedelta

from fastapi.testclient import TestClient

from app.main import app

c = TestClient(app)


def ok(r, code=200):
    assert r.status_code == code, (r.request.method, r.request.url.path, r.status_code, r.text)
    return r.json() if r.content else None


h = {'Authorization': f"Bearer {ok(c.post('/auth/register', json={'email': 'cu@example.com', 'password': 'password123'}), 201)['access_token']}"}
today = date.today()
days = [{'date': (today - timedelta(days=i)).isoformat(), 'sleep': {'hours': 8, 'bed': '23:30', 'wake': '07:30'},
         'work': {'deep': 3, 'total': 7}, 'body': {'steps': 9000, 'active_min': 30}, 'mind': {'meditation_min': 0}} for i in range(0, 7)]
ok(c.post('/daily-logs/batch', json={'days': days}, headers=h))

# Fitting the stats to your life is free from the start: turning parts off is unlocked at LV 0
view = ok(c.get('/customize', headers=h))
assert view['ladder'][0]['key'] == 'parts_off' and view['ladder'][0]['level'] == 0 and view['ladder'][0]['unlocked']
assert [u['level'] for u in view['ladder']][:3] == [0, 15, 20] and view['ladder'][-1]['title'] == 'Genius'
assert view['next']['key'] == 'weights' and not view['ladder'][1]['unlocked']

mp_before = next(s for s in ok(c.get('/stats/character', headers=h))['stats'] if s['code'] == 'MP')
assert any(p['name'] == 'Meditation' and p['score'] == 0 for p in mp_before['components'])
ok(c.put('/customize/off', json={'stat': 'MP', 'part': 'Meditation', 'off': True}, headers=h))
mp_after = next(s for s in ok(c.get('/stats/character', headers=h))['stats'] if s['code'] == 'MP')
assert mp_after['off'] == ['Meditation'] and all(p['name'] != 'Meditation' for p in mp_after['components'])
assert mp_after['score'] > mp_before['score'], (mp_before['score'], mp_after['score'])
print('MP', mp_before['score'], '->', mp_after['score'], 'with meditation off')

# Unknown part, and every part off, are refused
ok(c.put('/customize/off', json={'stat': 'MP', 'part': 'Juggling', 'off': True}, headers=h), 404)
soc = next(s for s in view['stats'] if s['code'] == 'SOC')
assert 'at least one' in ok(c.put('/customize/off', json={'stat': 'SOC', 'part': soc['parts'][0]['name'], 'off': True}, headers=h), 400)['detail']

# Friends see the standard score, not the customized one
friend = {'Authorization': f"Bearer {ok(c.post('/auth/register', json={'email': 'cu2@example.com', 'password': 'password123'}), 201)['access_token']}"}
code = ok(c.get('/friends', headers=h))['code']
ok(c.post('/friends/requests', json={'code': code}, headers=friend), 201)
req = ok(c.get('/friends', headers=h))['incoming'][0]['request_id']
ok(c.post(f'/friends/requests/{req}/accept', headers=h))
ok(c.patch('/friends/sharing', json={'stats': True}, headers=h))
seen = ok(c.get('/friends', headers=friend))['friends'][0]['stats']['stats']
assert next(s['score'] for s in seen if s['code'] == 'MP') == mp_before['score']

# Turn it back on; reset clears everything
ok(c.put('/customize/off', json={'stat': 'MP', 'part': 'Meditation', 'off': False}, headers=h))
assert ok(c.get('/customize', headers=h))['off'] == {}
ok(c.put('/customize/off', json={'stat': 'MP', 'part': 'Outdoors', 'off': True}, headers=h))
assert ok(c.delete('/customize', headers=h))['off'] == {}

# Tips
morning = ok(c.get('/stats/tip?when=morning', headers=h))
evening = ok(c.get('/stats/tip?when=evening', headers=h))
assert morning['title'].startswith('💡') and evening['title']
print('morning:', morning['title'], '|', morning['detail'])
print('evening:', evening['title'], '|', evening['detail'])
print('ALL OK')
