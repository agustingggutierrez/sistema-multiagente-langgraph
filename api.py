import os
from contextlib import asynccontextmanager

import redis.asyncio as redis
from fastapi import FastAPI, HTTPException, Request
from redis.exceptions import RedisError


REDIS_URL = os.getenv(
    "REDIS_URL",
    "redis://127.0.0.1:6380",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.redis = redis.Redis.from_url(
        REDIS_URL,
        decode_responses=True,
    )

    yield

    await app.state.redis.aclose()


app = FastAPI(
    title="Sistema Multiagente LangGraph API",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health(request: Request):
    try:
        await request.app.state.redis.ping()

    except RedisError as exc:
        raise HTTPException(
            status_code=503,
            detail="Redis no disponible",
        ) from exc

    return {
        "status": "ok",
        "redis": "ok",
    }
