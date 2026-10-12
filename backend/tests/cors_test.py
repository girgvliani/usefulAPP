"""The website's origin may use every method the API has, PATCH included (browser preflight)."""
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app

c = TestClient(app)
for method in ("GET", "POST", "PUT", "PATCH", "DELETE"):
    r = c.options("/profile", headers={"Origin": settings.frontend_origin, "Access-Control-Request-Method": method,
                                      "Access-Control-Request-Headers": "authorization,content-type"})
    assert r.status_code == 200 and method in r.headers.get("access-control-allow-methods", ""), (method, r.status_code, r.text)
print("preflight ok for", settings.frontend_origin)
