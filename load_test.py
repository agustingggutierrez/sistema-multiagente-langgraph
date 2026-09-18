import asyncio
import time

import httpx


API_URL = "http://127.0.0.1:8000"

TERMINAL_STATUSES = {
    "DONE",
    "FAILED",
    "REJECTED",
    "WAITING_APPROVAL",
}

QUERIES = [
    "Que es LangGraph?",
    "Explica Python.",
    "Que son los agentes?",
    "Que es inteligencia artificial?",
    "Explica sistemas multiagente.",
]


def percentile(
    values: list[float],
    percent: float,
) -> float:
    ordered = sorted(values)

    if len(ordered) == 1:
        return ordered[0]

    position = (
        len(ordered) - 1
    ) * (percent / 100)

    lower_index = int(position)

    upper_index = min(
        lower_index + 1,
        len(ordered) - 1,
    )

    weight = position - lower_index

    lower_value = ordered[lower_index]
    upper_value = ordered[upper_index]

    return (
        lower_value * (1 - weight)
        + upper_value * weight
    )


async def run_job(
    client: httpx.AsyncClient,
    number: int,
    query: str,
) -> dict:
    start = time.perf_counter()

    response = await client.post(
        "/tasks",
        json={
            "query": query,
        },
    )

    post_finished = time.perf_counter()

    response.raise_for_status()

    created = response.json()

    job_id = created["job_id"]

    while True:
        await asyncio.sleep(0.05)

        status_response = await client.get(
            f"/tasks/{job_id}"
        )

        status_response.raise_for_status()

        job = status_response.json()

        if job["status"] in TERMINAL_STATUSES:
            break

    finished = time.perf_counter()

    return {
        "number": number,
        "query": query,
        "job_id": job_id,
        "initial_status": created["status"],
        "final_status": job["status"],
        "post_ms": (post_finished - start) * 1000,
        "total_ms": (finished - start) * 1000,
    }


async def main():
    print(
        "=== PRUEBA DE 5 SOLICITUDES CONCURRENTES ==="
    )

    global_start = time.perf_counter()

    async with httpx.AsyncClient(
        base_url=API_URL,
        timeout=30.0,
    ) as client:

        tasks = [
            run_job(
                client=client,
                number=index,
                query=query,
            )
            for index, query in enumerate(
                QUERIES,
                start=1,
            )
        ]

        results = await asyncio.gather(*tasks)

    global_finished = time.perf_counter()

    print("\n=== RESULTADOS INDIVIDUALES ===")

    for result in results:
        print(
            f"Solicitud {result['number']}: "
            f"POST={result['post_ms']:.2f} ms | "
            f"TOTAL={result['total_ms']:.2f} ms | "
            f"{result['initial_status']} -> "
            f"{result['final_status']}"
        )

    post_times = [
        result["post_ms"]
        for result in results
    ]

    total_times = [
        result["total_ms"]
        for result in results
    ]

    wall_clock_ms = (
        global_finished - global_start
    ) * 1000

    post_p95 = percentile(
        post_times,
        95,
    )

    total_p95 = percentile(
        total_times,
        95,
    )

    print("\n=== RESUMEN ===")

    print(
        "Solicitudes:",
        len(results),
    )

    print(
        "POST promedio:",
        f"{sum(post_times) / len(post_times):.2f} ms",
    )

    print(
        "POST mínimo:",
        f"{min(post_times):.2f} ms",
    )

    print(
        "POST máximo:",
        f"{max(post_times):.2f} ms",
    )

    print(
        "POST p95:",
        f"{post_p95:.2f} ms",
    )

    print(
        "Procesamiento promedio:",
        f"{sum(total_times) / len(total_times):.2f} ms",
    )

    print(
        "Procesamiento p95:",
        f"{total_p95:.2f} ms",
    )

    print(
        "Tiempo total de la prueba concurrente:",
        f"{wall_clock_ms:.2f} ms",
    )

    print(
        "Estados finales:",
        [
            result["final_status"]
            for result in results
        ],
    )


asyncio.run(main())
