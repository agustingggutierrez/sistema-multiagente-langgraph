import os

import redis.asyncio as redis
from langgraph.checkpoint.redis.aio import AsyncRedisSaver
from langgraph.types import Command

from graph import builder
from job_store import JobStatus, JobStore


REDIS_URL = os.getenv(
    "REDIS_URL",
    "redis://127.0.0.1:6380",
)


async def process_job(
    *,
    job_id: str,
    query: str,
    thread_id: str,
) -> None:
    client = redis.Redis.from_url(
        REDIS_URL,
        decode_responses=True,
    )

    store = JobStore(client)

    config = {
        "configurable": {
            "thread_id": thread_id,
        }
    }

    try:
        print(f"[WORKER] Iniciando job {job_id}")

        await store.set_status(
            job_id,
            JobStatus.RUNNING,
        )

        async with AsyncRedisSaver.from_conn_string(
            REDIS_URL
        ) as checkpointer:

            graph = builder.compile(
                checkpointer=checkpointer
            )

            print(
                f"[WORKER] Ejecutando LangGraph para {job_id}"
            )

            async for _ in graph.astream(
                {
                    "query": query,
                },
                config=config,
                stream_mode="updates",
            ):
                pass

            state = await graph.aget_state(config)

            if state.interrupts:
                print(
                    f"[WORKER] Job {job_id} "
                    "esperando aprobación humana"
                )

                await store.set_status(
                    job_id,
                    JobStatus.WAITING_APPROVAL,
                )

                return

            final_answer = state.values.get(
                "final_answer",
                "",
            )

            print(f"[WORKER] Job {job_id} finalizado")

            await store.set_status(
                job_id,
                JobStatus.DONE,
                result=final_answer,
            )

    except Exception as exc:
        print(
            f"[WORKER] Error en job {job_id}: "
            f"{type(exc).__name__}: {exc}"
        )

        await store.set_status(
            job_id,
            JobStatus.FAILED,
            error=f"{type(exc).__name__}: {exc}",
        )

    finally:
        await client.aclose()


async def resume_job(
    *,
    job_id: str,
    approved: bool,
) -> dict[str, str]:
    client = redis.Redis.from_url(
        REDIS_URL,
        decode_responses=True,
    )

    store = JobStore(client)

    try:
        job = await store.get_job(job_id)

        if job is None:
            raise ValueError(
                f"Job inexistente: {job_id}"
            )

        if job["status"] != JobStatus.WAITING_APPROVAL.value:
            raise ValueError(
                "El job no está esperando aprobación. "
                f"Estado actual: {job['status']}"
            )

        thread_id = job["thread_id"]

        config = {
            "configurable": {
                "thread_id": thread_id,
            }
        }

        print(
            f"[WORKER] Reanudando job {job_id} "
            f"con approved={approved}"
        )

        await store.set_status(
            job_id,
            JobStatus.RUNNING,
        )

        async with AsyncRedisSaver.from_conn_string(
            REDIS_URL
        ) as checkpointer:

            graph = builder.compile(
                checkpointer=checkpointer
            )

            async for _ in graph.astream(
                Command(
                    resume={
                        "approved": approved,
                    }
                ),
                config=config,
                stream_mode="updates",
            ):
                pass

            state = await graph.aget_state(config)

            if state.interrupts:
                await store.set_status(
                    job_id,
                    JobStatus.WAITING_APPROVAL,
                )

                job = await store.get_job(job_id)

                if job is None:
                    raise RuntimeError(
                        "No se pudo recuperar el job pausado."
                    )

                return job

            final_answer = state.values.get(
                "final_answer",
                "",
            )

            approval_decision = state.values.get(
                "approval_decision"
            )

            if approval_decision is False:
                print(
                    f"[WORKER] Job {job_id} rechazado"
                )

                updated_job = await store.set_status(
                    job_id,
                    JobStatus.REJECTED,
                    result=final_answer,
                )

            else:
                print(
                    f"[WORKER] Job {job_id} completado "
                    "después de aprobación"
                )

                updated_job = await store.set_status(
                    job_id,
                    JobStatus.DONE,
                    result=final_answer,
                )

            if updated_job is None:
                raise RuntimeError(
                    f"No se pudo actualizar el job {job_id}"
                )

            return updated_job

    except ValueError:
        raise

    except Exception as exc:
        print(
            f"[WORKER] Error reanudando job {job_id}: "
            f"{type(exc).__name__}: {exc}"
        )

        await store.set_status(
            job_id,
            JobStatus.FAILED,
            error=f"{type(exc).__name__}: {exc}",
        )

        raise

    finally:
        await client.aclose()
