from typing import Literal

from langgraph.graph import StateGraph, START, END

from state import AgentState
from agents.research_agent import research_agent
from agents.analyst_agent import analyst_agent


def supervisor(state: AgentState):

    print("\n[SUPERVISOR] Analizando estado...")

    if not state.get("research_result"):
        siguiente = "research"

    elif not state.get("analysis_result"):
        siguiente = "analyst"

    else:
        siguiente = "validation"

    print(f"[SUPERVISOR] Siguiente nodo: {siguiente}")

    return {
        "next_agent": siguiente
    }


def supervisor_router(
    state: AgentState
) -> Literal["research", "analyst", "validation"]:

    return state["next_agent"]


def validation_node(state: AgentState):

    print("\n[VALIDATION] Validando resultados...")

    investigacion = state.get("research_result", "")
    analisis = state.get("analysis_result", "")

    errores = []

    if len(investigacion) < 20:
        errores.append(
            "La investigación es demasiado corta."
        )

    if len(analisis) < 30:
        errores.append(
            "El análisis es insuficiente."
        )

    if errores:

        respuesta = (
            "La respuesta no superó la validación:\n"
            + "\n".join(errores)
        )

        return {
            "validated": False,
            "final_answer": respuesta
        }

    respuesta = (
        "RESPUESTA VALIDADA\n\n"
        f"{analisis}"
    )

    return {
        "validated": True,
        "final_answer": respuesta
    }


builder = StateGraph(AgentState)


builder.add_node(
    "supervisor",
    supervisor
)

builder.add_node(
    "research",
    research_agent
)

builder.add_node(
    "analyst",
    analyst_agent
)

builder.add_node(
    "validation",
    validation_node
)


builder.add_edge(
    START,
    "supervisor"
)


builder.add_conditional_edges(
    "supervisor",
    supervisor_router,
    {
        "research": "research",
        "analyst": "analyst",
        "validation": "validation",
    }
)


builder.add_edge(
    "research",
    "supervisor"
)

builder.add_edge(
    "analyst",
    "supervisor"
)

builder.add_edge(
    "validation",
    END
)


graph = builder.compile()