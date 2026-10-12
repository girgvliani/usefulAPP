"""/stats/character and /history carry the six categories; TOTAL averages the categories."""
from datetime import date, timedelta
from statistics import mean

from fastapi.testclient import TestClient

from app.main import app

c = TestClient(app)


def ok(r, code=200):
    assert r.status_code == code, (r.request.url.path, r.status_code, r.text)
    return r.json() if r.content else None


login = {'Authorization': f"Bearer {ok(c.post('/auth/register', json={'email': 'cat@example.com', 'password': 'password123'}), 201)['access_token']}"}
h = {'Authorization': f"Bearer {ok(c.post('/devices', json={'name': 'S23'}, headers=login), 201)['token']}"}
today = date.today()
days = [{'date': (today - timedelta(days=i)).isoformat(),
         'sleep': {'hours': 7.5, 'bed': '23:30', 'wake': '07:00'}, 'work': {'deep': 3, 'total': 6},
         'body': {'steps': 9000, 'active_min': 30}, 'mind': {'learning_min': 40},
         'screen': {'short_video_min': 20, 'social_min': 30, 'total_min': 180, 'night_min': 0, 'unlocks': 60}}
        for i in range(6)]
ok(c.post('/daily-logs/batch?source=auto', json={'days': days}, headers=h))

sheet = ok(c.get('/stats/character', headers=h))
cats = {cat['key']: cat for cat in sheet['categories']}
assert list(cats) == ['mental', 'physical', 'practical', 'cultural', 'discipline', 'social']
assert sorted(code for cat in sheet['categories'] for code in cat['stats']) == sorted(s['code'] for s in sheet['stats'])
scores = {s['code']: s['score'] for s in sheet['stats']}
for cat in sheet['categories']:
    known = [scores[code] for code in cat['stats'] if scores[code] is not None]
    assert cat['score'] == (round(mean(known)) if known else None), cat
    assert (cat['grade'] is None) == (cat['score'] is None)
known = [cat['score'] for cat in sheet['categories'] if cat['score'] is not None]
assert sheet['overall'] == round(mean(known))
print({k: (v['score'], v['grade']) for k, v in cats.items()}, 'TOTAL', sheet['overall'], sheet['overall_grade'])

history = ok(c.get(f'/stats/character/history?start={(today - timedelta(days=6)).isoformat()}', headers=h))
assert history[-1]['categories'] == {k: v['score'] for k, v in cats.items()}
print('history ok, %d days' % len(history))
