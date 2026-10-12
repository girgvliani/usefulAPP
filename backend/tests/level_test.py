from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient

from app.main import app
from app.services.levels import level_for, xp_for_level

c = TestClient(app)
today = datetime.now(ZoneInfo('Asia/Tbilisi')).date()
D = lambda n: (today - timedelta(days=n)).isoformat()


def ok(r, code=200):
    assert r.status_code == code, (r.request.method, r.request.url.path, r.status_code, r.text)
    return r.json() if r.content else None


# ---- the curve
assert [xp_for_level(n) for n in (0, 1, 2, 5, 10, 20)] == [0, 100, 300, 1500, 5500, 21000]
for xp, level in ((0, 0), (99, 0), (100, 1), (299, 1), (300, 2), (5499, 9), (5500, 10), (21000, 20)):
    assert level_for(xp) == level, (xp, level_for(xp))
print('curve ok')

h = {'Authorization': f"Bearer {ok(c.post('/auth/register', json={'email': 'lvl@example.com', 'password': 'password123'}), 201)['access_token']}"}
lv = ok(c.get('/stats/level', headers=h))
assert (lv['level'], lv['xp'], lv['today_xp']) == (0, 0, 0), lv
print('new account: LV 0, 0 XP')

# Yesterday: a full good day. Phone: 8h sleep, 9000 steps, 20 min reels. Check-in: 3h deep work,
# 45 min learning, 10 min meditation, 50 push-ups (new-account target), shower, 2 contacts.
ok(c.put(f'/daily-logs/{D(1)}?source=auto', headers=h, json={'sleep': {'hours': 8}, 'body': {'steps': 9000}, 'screen': {'short_video_min': 20}}))
ok(c.put(f'/daily-logs/{D(1)}', headers=h, json={'work': {'deep': 3}, 'mind': {'learning_min': 45, 'meditation_min': 10},
                                                'body': {'pushups': 50, 'shower': True}, 'social': {'interactions': 2}}))
# Today so far: only the phone's sleep (6h: no sleep XP) and 90 min of reels (no reels XP)
ok(c.put(f'/daily-logs/{D(0)}?source=auto', headers=h, json={'sleep': {'hours': 6}, 'screen': {'short_video_min': 90}}))
lv = ok(c.get('/stats/level', headers=h))
# check-in 20 + sleep 15 + push-ups 15 + steps 15 + deep 30 + learning 15 + meditation 5 + shower 5 + reels 10 + social 20 = 150
assert lv['sources']['activity'] == 150 and lv['today_xp'] == 0, lv
# plus the first achievements: push-ups (25 + 50 in a day 75), sleep 25, check-in 25, meditation 25 = 175
assert lv['sources']['achievements'] == 175 and lv['xp'] == 325, lv
assert (lv['level'], lv['level_start_xp'], lv['next_level_xp']) == (2, 300, 600), lv
print('one good day:', lv['xp'], 'XP -> LV', lv['level'])

# Quest XP counts too (shower habit gives +10 area XP), and a reached goal +250
ok(c.post('/habits/shower', headers=h))
ok(c.post('/goals', headers=h, json={'type': 'custom', 'title': 'x', 'unit': 'x', 'start_value': 0, 'target_value': 1, 'current_value': 1}), 201)
lv = ok(c.get('/stats/level', headers=h))
# reaching the goal also earns Goal Getter (+100)
assert lv['sources'] == {'activity': 150, 'quests': 10, 'goals': 250, 'achievements': 275, 'paths': 0, 'books': 0} and lv['xp'] == 685 and lv['level'] == 3, lv
assert (lv['title'], lv['next_title']) == ('Novice', 'Apprentice at LV 5'), lv
assert len(lv['history']) == 30 and lv['history'][-2]['xp'] == 150 and lv['history'][-1]['xp'] == 0, lv['history'][-3:]
from app.services.levels import title_for
assert [title_for(n) for n in (0, 4, 5, 12, 20, 29, 30, 49, 50, 99)] == ['Novice', 'Novice', 'Apprentice', 'Adept', 'Elite', 'Elite', 'Master', 'Grandmaster', 'Legend', 'Legend']
print('with quests and a reached goal:', lv['xp'], 'XP -> LV', lv['level'], '| today:', lv['today'])
print('ALL OK')
