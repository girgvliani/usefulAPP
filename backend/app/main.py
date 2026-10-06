import logging

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.config import settings
from app.rate_limit import limiter
from app.routers import (
    auth, browsing, customize, daily_logs, devices, friends, goals, habits, income, life_areas, meals, milestones, profile, projects, questionnaire,
    screen_time, sleep, social, stats, todos, xp,
)

logger = logging.getLogger("life_rpg")

docs_kwargs = {} if not settings.is_production else {"docs_url": None, "redoc_url": None, "openapi_url": None}

app = FastAPI(title="Life RPG API", **docs_kwargs)

app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(status_code=status.HTTP_429_TOO_MANY_REQUESTS, content={"detail": "Too many requests"})


@app.exception_handler(Exception)
def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    if settings.is_production:
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"detail": "Internal server error"})
    raise exc


app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],  # PATCH: every edit (profile, goals, quests…)
    allow_headers=["Authorization", "Content-Type"],
)
app.add_middleware(SlowAPIMiddleware)

app.include_router(auth.router)
app.include_router(life_areas.router)
app.include_router(habits.router)
app.include_router(sleep.router)
app.include_router(screen_time.router)
app.include_router(social.router)
app.include_router(projects.router)
app.include_router(todos.router)
app.include_router(milestones.router)
app.include_router(income.router)
app.include_router(xp.router)
app.include_router(stats.router)
app.include_router(daily_logs.router)
app.include_router(devices.router)
app.include_router(profile.router)
app.include_router(goals.router)
app.include_router(meals.router)
app.include_router(questionnaire.router)
app.include_router(friends.router)
app.include_router(browsing.router)
app.include_router(customize.router)


@app.get("/health")
def health():
    return {"status": "ok"}
