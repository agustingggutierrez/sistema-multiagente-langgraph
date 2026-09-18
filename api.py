import asyncio
import os
from contextlib import asynccontextmanager
from uuid import uuid4

import redis.asyncio as redis
from fastapi import FastAPI, HTTPException, Request, status
from pydantic import BaseModel, Field
from redis.exceptions import RedisError

from job_store import JobStatus, JobStore
from worker import process_job, resume_job


REDIS_URL = os.getenv(
    "REDIS_URL",
    "redis://127.0.0.1:6380",
)


class TaskRequest(BaseModel):
    query: str = Field(
        min_length=1,
        description="Consulta que procesará el sistema multiagente",
    )


class TaskCreatedResponse(BaseModel):
    job_id: str
    thread_id: str
    status: str


class ApprovalRequest(BaseModel):
    approved: bool


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.redis = redis.Redis.from_url(
        REDIS_URL,
        decode_responses=True,
    )

    app.state.background_tasks = set()

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


@app.post(
    "/tasks",
    response_model=TaskCreatedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_task(
    payload: TaskRequest,
    request: Request,
):
    job_id = str(uuid4())
    thread_id = str(uuid4())

    store = JobStore(
        request.app.state.redis
    )

    try:
        job = await store.create_job(
            job_id=job_id,
            query=payload.query,
            thread_id=thread_id,
        )

    except RedisError as exc:
        raise HTTPException(
            status_code=503,
            detail="No se pudo crear el job en Redis",
        ) from exc

    background_task = asyncio.create_task(
        process_job(
            job_id=job_id,
            query=payload.query,
            thread_id=thread_id,
        )
    )

    request.app.state.background_tasks.add(
        background_task
    )

    background_task.add_done_callback(
        request.app.state.background_tasks.discard
    )

    return {
        "job_id": job["job_id"],
        "thread_id": job["thread_id"],
        "status": job["status"],
    }


@app.get("/tasks/{job_id}")
async def get_task(
    job_id: str,
    request: Request,
):
    store = JobStore(
        request.app.state.redis
    )

    try:
        job = await store.get_job(job_id)

    except RedisError as exc:
        raise HTTPException(
            status_code=503,
            detail="No se pudo consultar Redis",
        ) from exc

    if job is None:
        raise HTTPException(
            status_code=404,
            detail="Job no encontrado",
        )

    return job


@app.post("/tasks/{job_id}/approve")
async def approve_task(
    job_id: str,
    payload: ApprovalRequest,
    request: Request,
):
    store = JobStore(
        request.app.state.redis
    )

    try:
        job = await store.get_job(job_id)

    except RedisError as exc:
        raise HTTPException(
            status_code=503,
            detail="No se pudo consultar Redis",
        ) from exc

    if job is None:
        raise HTTPException(
            status_code=404,
            detail="Job no encontrado",
        )

    if job["status"] != JobStatus.WAITING_APPROVAL.value:
        raise HTTPException(
            status_code=409,
            detail=(
                "El job no está esperando aprobación. "
                f"Estado actual: {job['status']}"
            ),
        )

    try:
        updated_job = await resume_job(
            job_id=job_id,
            approved=payload.approved,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        ) from exc

    except RedisError as exc:
        raise HTTPException(
            status_code=503,
            detail="Error de Redis al reanudar el job",
        ) from exc

    return updated_job
