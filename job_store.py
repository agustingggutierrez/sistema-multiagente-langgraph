from datetime import datetime, timezone
from enum import Enum
from typing import Optional

import redis.asyncio as redis


class JobStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    DONE = "DONE"
    FAILED = "FAILED"
    REJECTED = "REJECTED"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class JobStore:
    def __init__(self, client: redis.Redis):
        self.client = client

    @staticmethod
    def _key(job_id: str) -> str:
        return f"job:{job_id}"

    async def create_job(
        self,
        *,
        job_id: str,
        query: str,
        thread_id: str,
    ) -> dict[str, str]:
        now = utc_now_iso()

        data = {
            "job_id": job_id,
            "status": JobStatus.PENDING.value,
            "input": query,
            "thread_id": thread_id,
            "result": "",
            "error": "",
            "created_at": now,
            "updated_at": now,
            "started_at": "",
            "finished_at": "",
        }

        await self.client.hset(
            self._key(job_id),
            mapping=data,
        )

        job = await self.get_job(job_id)

        if job is None:
            raise RuntimeError(
                f"No se pudo recuperar el job recién creado: {job_id}"
            )

        return job

    async def get_job(
        self,
        job_id: str,
    ) -> Optional[dict[str, str]]:
        data = await self.client.hgetall(
            self._key(job_id)
        )

        if not data:
            return None

        return data

    async def set_status(
        self,
        job_id: str,
        status: JobStatus,
        *,
        result: Optional[str] = None,
        error: Optional[str] = None,
    ) -> Optional[dict[str, str]]:
        key = self._key(job_id)

        if not await self.client.exists(key):
            return None

        now = utc_now_iso()

        updates = {
            "status": status.value,
            "updated_at": now,
        }

        if status == JobStatus.RUNNING:
            started_at = await self.client.hget(
                key,
                "started_at",
            )

            if not started_at:
                updates["started_at"] = now

        if status in {
            JobStatus.DONE,
            JobStatus.FAILED,
            JobStatus.REJECTED,
        }:
            updates["finished_at"] = now

        if result is not None:
            updates["result"] = result

        if error is not None:
            updates["error"] = error

        await self.client.hset(
            key,
            mapping=updates,
        )

        return await self.get_job(job_id)
