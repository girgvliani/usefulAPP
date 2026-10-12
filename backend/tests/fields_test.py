"""The field catalog matches the daily-log schema, and every value a formula reads is in it."""
import re
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.schemas import DailyLogIn
from app.services import character_stats

c = TestClient(app)
cat = c.get('/daily-logs/fields').json()
fields = {(f['section'], f['key']): f for f in cat['fields']}
assert [s['key'] for s in cat['sections']] == [k for k in DailyLogIn.model_fields if k != 'custom']  # answers to your own questions: per person

# Every catalog entry is a real schema field
for (section, key) in fields:
    model = DailyLogIn.model_fields[section].annotation.__args__[0]
    assert key in model.model_fields, (section, key)

# Every schema field is listed, except the ones that aren't values you'd edit
skip = {('sleep', 'estimated'), ('screen', 'apps')}
for section, info in ((s, i) for s, i in DailyLogIn.model_fields.items() if s != 'custom'):
    for key in info.annotation.__args__[0].model_fields:
        assert (section, key) in fields or (section, key) in skip, f'{section}.{key} missing from the catalog'

# Every field a formula reads is marked as feeding something
source = Path(character_stats.__file__).read_text(encoding='utf-8')
read = set(re.findall(r"'(sleep|work|mind|screen|body|social)', '([a-z_]+)'", source))
read |= {('screen', k) for k in re.findall(r"average\('([a-z_]+)'\)", source)}
read |= {('screen', k) for k in re.findall(r"part\('[^']+', \d+, '([a-z_]+)'", source)}
read |= {('sleep', k) for k in re.findall(r"sleep\.get\('([a-z_]+)'\)", source)}
for pair in read:
    assert pair in fields and fields[pair]['feeds'], f'{pair} is read by a formula but feeds nothing in the catalog'
codes = {code for code, _ in character_stats.STATS}
assert all(set(f['feeds']) <= codes for f in cat['fields'])
assert all(f['kind'] in {'decimal', 'whole', 'yesno', 'time'} and f['source'] in {'phone', 'checkin', 'both', 'import'} for f in cat['fields'])
print(f"catalog ok: {len(fields)} fields, formulas read {len(read)} of them")
