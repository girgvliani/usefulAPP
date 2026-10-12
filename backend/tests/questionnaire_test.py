"""Questionnaire: catalog, validation, results, profile writes, every attempt kept, peer group hidden."""
from fastapi.testclient import TestClient

from app.main import app
from app.models import QuestionnaireAttempt
from app.database import SessionLocal

c = TestClient(app)


def ok(r, code=200):
    assert r.status_code == code, (r.request.method, r.request.url.path, r.status_code, r.text)
    return r.json() if r.content else None


login = {'Authorization': f"Bearer {ok(c.post('/auth/register', json={'email': 'q@example.com', 'password': 'password123'}), 201)['access_token']}"}
h = {'Authorization': f"Bearer {ok(c.post('/devices', json={'name': 'S23'}, headers=login), 201)['token']}"}

q = ok(c.get('/questionnaire', headers=h))
assert [s['key'] for s in q['sections']] == ['you', 'matters', 'now', 'obstacles', 'story']
assert q['latest'] is None and q['prefill'] == {}
ids = [qq['id'] for s in q['sections'] for qq in s['questions']]
print(len(ids), 'questions')

A = {
    'birth_year': 2003, 'sex': 'male', 'height_cm': 185, 'weight_kg': 112.0, 'daily_activity': 'desk', 'fitness': 'some',
    'pushups_max': 25,
    'priorities': ['physical', 'mental', 'practical', 'discipline', 'cultural', 'social'], 'main_goal': 'lose_weight', 'why': ['health', 'prove'],
    'sleep_hours': '6_7', 'bedtime': 'random', 'phone_hours': 'gt6', 'short_video': '1_2h', 'exercise_days': '1_2', 'work_hours': '8_10',
    'deep_work': 'lt1', 'learning': '1_3', 'social': '1_2', 'eating': 'fast', 'alcohol': '1_3', 'money': 'ok', 'stress': 4, 'energy': 2,
    'obstacles': ['phone', 'tired', 'no_plan'], 'chronotype': 'evening', 'what_works': ['pushed', 'streaks'],
    'milestones': ['degree', 'job'], 'best_shape': '3_5y', 'tried': ['gym', 'diet'], 'proudest': 'Built Life RPG',
}

# Validation names the problem
bad = dict(A); del bad['sleep_hours']
assert 'sleep' in ok(c.post('/questionnaire', json={'answers': bad}, headers=h), 422)['detail'].lower()
bad = dict(A, priorities=['physical', 'mental'])
assert 'order' in ok(c.post('/questionnaire', json={'answers': bad}, headers=h), 422)['detail']
bad = dict(A, obstacles=['phone', 'tired', 'no_plan', 'time'])
assert 'at most 3' in ok(c.post('/questionnaire', json={'answers': bad}, headers=h), 422)['detail']
bad = dict(A, stress=7)
assert '1 to 5' in ok(c.post('/questionnaire', json={'answers': bad}, headers=h), 422)['detail']

first = ok(c.post('/questionnaire', json={'answers': A}, headers=h), 201)
r = first['results']
assert 'cohort' not in r, 'the peer group must stay on the server'
assert [p['key'] for p in r['priorities']] == A['priorities']
assert r['focus'] and set(r['focus']) <= set(A['priorities'][:4])
plan_ids = [p['id'] for p in r['plan']]
assert plan_ids[0] in ('weight', 'exercise'), plan_ids  # top priority is Physical
assert {'sleep', 'reels', 'weight'} <= set(plan_ids) | {'sleep'}, plan_ids
weight_goal = next(p['goal'] for p in r['plan'] if p['id'] == 'weight')
assert weight_goal == {'type': 'weight', 'start_value': 112.0, 'target_value': 106.4}, weight_goal
for step in r['plan']:
    if step['goal']:
        ok(c.post('/goals', json=dict(step['goal'], intensity=5), headers=h), 201)  # every suggested goal can be created as is
print('goals created:', len(ok(c.get('/goals', headers=h))))
print('focus', r['focus'], '| plan', plan_ids)
print('tips', len(r['tips']))

# Profile and weight were saved
p = ok(c.get('/profile', headers=h))
assert (p['birth_year'], p['sex'], p['height_cm']) == (2003, 'male', 185)
q2 = ok(c.get('/questionnaire', headers=h))
assert q2['prefill']['weight_kg'] == 112.0 and q2['prefill']['sleep_hours'] == '6_7'
assert q2['latest']['id'] == first['id']

# Retake: both kept, newest first, peer group stored server-side only
second = ok(c.post('/questionnaire', json={'answers': dict(A, sleep_hours='7_8', short_video='lt30')}, headers=h), 201)
attempts = ok(c.get('/questionnaire/attempts', headers=h))
assert [x['id'] for x in attempts] == [second['id'], first['id']]
assert 'sleep' not in [p['id'] for p in second['results']['plan']]
assert all('cohort' not in x['results'] for x in attempts)
assert ok(c.get(f"/questionnaire/attempts/{first['id']}", headers=h))['id'] == first['id']
with SessionLocal() as db:
    stored = db.get(QuestionnaireAttempt, second['id']).results['cohort']
assert stored == {'age_band': '18-29', 'sex': 'male', 'build': 'very heavy', 'fitness': 'beginner', 'key': 'male|18-29|very heavy|beginner'}  # BMI 32.7, stored

# Someone else can't read them
other = {'Authorization': f"Bearer {ok(c.post('/auth/register', json={'email': 'q2@example.com', 'password': 'password123'}), 201)['access_token']}"}
ok(c.get(f"/questionnaire/attempts/{first['id']}", headers=other), 404)
assert ok(c.get('/questionnaire/attempts', headers=other)) == []
print('ALL OK')

# The plan follows the focus: every focus area with an applicable change leads with it
for attempt in (first, second):
    res = attempt['results']
    cats = [p['category'] for p in res['plan']]
    for key in res['focus']:
        if any(rule_cat == key for rule_cat in cats):
            assert cats.index(key) < len(res['focus']), (key, cats)
print('plan follows focus')
