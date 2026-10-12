"""Achievements from real data, bonus XP, unlock notices, worn titles, camera reps, profile photos."""
import io
from datetime import date, timedelta

from fastapi.testclient import TestClient
from PIL import Image

from app.main import app
from app.services import achievements

c = TestClient(app)


def ok(r, code=200):
    assert r.status_code == code, (r.request.method, r.request.url.path, r.status_code, r.text)
    return r.json() if r.content else None


def register(email, name):
    h = {'Authorization': f"Bearer {ok(c.post('/auth/register', json={'email': email, 'password': 'password123'}), 201)['access_token']}"}
    ok(c.patch('/profile', json={'display_name': name, 'public_name': 'name'}, headers=h))
    return h


h = register('ach@example.com', 'Ann')

# Catalog: every story has chapters, every metric exists in the facts
cat = ok(c.get('/achievements/catalog'))
assert len(cat['achievements']) >= 50 and all(any(a['story'] == s['key'] for a in cat['achievements']) for s in cat['stories'])
v = ok(c.get('/achievements', headers=h))
assert v['earned'] == 0 and v['total'] == len(cat['achievements'])
from app.database import SessionLocal
from app.models import User
with SessionLocal() as db:
    user = db.query(User).filter_by(email='ach@example.com').one()
    f = achievements.facts(db, user)
    missing = {a.metric for a in achievements.ACHIEVEMENTS} - set(f)
    assert not missing, missing
a = {x['key']: x for x in v['achievements']}
assert a['run_marathon']['how'].startswith('Run a full marathon') and a['run_marathon']['title'] == 'Jr. Goggins' and a['run_marathon']['xp'] == 1500

# A marathon synced from the phone, 12k steps, a check-in: earned on the next level check
before = ok(c.get('/stats/level', headers=h))
assert before['new_achievements'] == [] and before['sources']['achievements'] == 0
today = date.fromisoformat(ok(c.get('/stats/level', headers=h))['history'][-1]['date'])
ok(c.post('/daily-logs/batch?source=auto', json={'days': [
    {'date': str(today - timedelta(days=1)), 'body': {'steps': 12000, 'run_km': 42.4, 'longest_run_km': 42.4}},
]}, headers=h))
lv = ok(c.get('/stats/level', headers=h))
new = {x['key'] for x in lv['new_achievements']}
assert {'run_first', 'run_5k', 'run_10k', 'run_half', 'run_marathon', 'steps_10k'} <= new, new
assert 'run_100' not in new and 'steps_20k' not in new
bonus = sum(achievements.BY_KEY[k].xp for k in new)
assert lv['sources']['achievements'] == bonus and lv['xp'] >= bonus
# Shown once: after "seen" they stop coming back
ok(c.post('/achievements/seen', headers=h), 204)
assert ok(c.get('/stats/level', headers=h))['new_achievements'] == []

# Progress toward the rest: 42.4 of 100 km
v = ok(c.get('/achievements', headers=h))
a = {x['key']: x for x in v['achievements']}
assert a['run_100']['value'] == 42.4 and a['run_100']['progress'] == 0.424 and a['run_100']['earned_at'] is None
assert a['run_marathon']['progress'] == 1 and a['run_marathon']['earned_at']
goggins = next(s for s in v['stories'] if s['key'] == 'goggins')
assert goggins['done'] == 5 and goggins['next'] == 'run_100'

# Titles: only earned ones with a title can be worn; friends and the board see it
assert c.put('/achievements/title', json={'key': 'push_10000'}, headers=h).status_code == 400  # not earned
assert c.put('/achievements/title', json={'key': 'run_5k'}, headers=h).status_code == 400  # no title
ok(c.put('/achievements/title', json={'key': 'run_marathon'}, headers=h))
assert ok(c.get('/profile', headers=h))['title'] == 'Jr. Goggins'
assert ok(c.get('/friends/global', headers=h))['you']['title'] == 'Jr. Goggins'

# Camera reps: two sets add up into the check-in field, the best set is kept
ok(c.put(f'/daily-logs/{today}?source=manual', json={'body': {'pushups': 10}}, headers=h))
ok(c.post(f'/daily-logs/{today}/reps', json={'exercise': 'pushups', 'count': 30}, headers=h))
d = ok(c.post(f'/daily-logs/{today}/reps', json={'exercise': 'pushups', 'count': 25}, headers=h))
body = d['merged']['body']
assert body['pushups'] == 65 and body['cam_pushups'] == 55 and body['cam_best_set'] == 30 and body['max_pushups'] == 30, body
d = ok(c.post(f'/daily-logs/{today}/reps', json={'exercise': 'squats', 'count': 40}, headers=h))
assert d['merged']['body']['squats'] == 40 and d['merged']['body']['cam_squats'] == 40
assert c.post(f'/daily-logs/{today}/reps', json={'exercise': 'burpees', 'count': 5}, headers=h).status_code == 422
assert c.post(f'/daily-logs/{today + timedelta(days=2)}/reps', json={'exercise': 'pushups', 'count': 5}, headers=h).status_code == 400
new = {x['key'] for x in ok(c.get('/stats/level', headers=h))['new_achievements']}
assert {'push_first', 'push_50', 'cam_first', 'checkin_first'} <= new and 'cam_100' not in new, new

# Profile photo: re-encoded to a 256 px JPEG without EXIF, served without sign-in
img = Image.new('RGB', (800, 600), (200, 50, 120))
exif = Image.Exif()
exif[0x010F] = 'SecretCam'  # Make
buf = io.BytesIO()
img.save(buf, 'JPEG', exif=exif)
p = ok(c.put('/profile/photo', files={'photo': ('me.jpg', buf.getvalue(), 'image/jpeg')}, headers=h))
url = p['photo_url']
assert url.startswith('/photos/') and url.endswith('.jpg')
r = c.get(url)
assert r.status_code == 200 and r.headers['content-type'] == 'image/jpeg'
served = Image.open(io.BytesIO(r.content))
assert served.size == (256, 256) and not served.getexif(), served.getexif()
assert c.put('/profile/photo', files={'photo': ('x.jpg', b'not an image', 'image/jpeg')}, headers=h).status_code == 415
assert 'photo' in {x['key'] for x in ok(c.get('/stats/level', headers=h))['new_achievements']}

# Others see the photo with the name; "just your code" hides it and retires the old link
h2 = register('bea@example.com', 'Bea')
board = ok(c.get('/friends/global', headers=h2))
ann = next(r for r in board['top'] if r['name'] == 'Ann')
assert ann['photo_url'] == url and ann['title'] == 'Jr. Goggins'
ok(c.patch('/profile', json={'public_name': 'code'}, headers=h))
ann = next(r for r in ok(c.get('/friends/global', headers=h2))['top'] if r['name'].startswith('Player'))
assert ann['photo_url'] is None
assert c.get(url).status_code == 404
ok(c.patch('/profile', json={'public_name': 'name'}, headers=h))

# Friends: badges only with the achievements switch on
code = ok(c.get('/friends', headers=h))['code']
ok(c.post('/friends/requests', json={'code': code}, headers=h2), 201)
req = ok(c.get('/friends', headers=h))['incoming'][0]
ok(c.post(f"/friends/requests/{req['request_id']}/accept", headers=h))
friend = ok(c.get('/friends', headers=h2))['friends'][0]
assert 'achievements' not in friend and friend['photo_url']
assert ok(c.patch('/friends/sharing', json={'achievements': True}, headers=h))['achievements'] is True
friend = ok(c.get('/friends', headers=h2))['friends'][0]
assert friend['achievements']['earned'] >= 10 and friend['achievements']['badges'][0]['icon']
# Making a friend is an achievement too
assert 'friend_first' in {x['key'] for x in ok(c.get('/stats/level', headers=h2))['new_achievements']}

# Delete the photo
assert ok(c.delete('/profile/photo', headers=h))['photo_url'] is None
print('achievements ok:', ok(c.get('/achievements', headers=h))['earned'], 'earned')
