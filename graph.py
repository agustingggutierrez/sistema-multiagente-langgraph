from typing import Literal

from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt

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
        siguiente = "approval"

    print(f"[SUPERVISOR] Siguiente nodo: {siguiente}")

    return {
        "next_agent": siguiente
    }


def supervisor_router(
    state: AgentState
) -> Literal["research", "analyst", "approval"]:

    return state["next_agent"]


def approval_node(state: AgentState):

    consulta = state.get("query", "")

    requiere_aprobacion = "[critical]" in consulta.lower()

    if not requiere_aprobacion:

        print("\n[APPROVAL] No requiere aprobación humana.")

        return {
            "requires_approval": False,
            "approval_decision": True,
        }

    print(
        "\n[APPROVAL] Operación crítica detectada. "
        "Esperando aprobación humana..."
    )

    decision = interrupt(
        {
            "type": "approval_required",
            "message": "La operación fue marcada como crítica.",
            "query": consulta,
        }
    )

    if isinstance(decision, dict):
        aprobada = bool(decision.get("approved", False))
    else:
        aprobada = bool(decision)

    if aprobada:

        print("\n[APPROVAL] Operación aprobada.")

        return {
            "requires_approval": True,
            "approval_decision": True,
        }

    print("\n[APPROVAL] Operación rechazada.")

    return {
        "requires_approval": True,
        "approval_decision": False,
        "validated": False,
        "final_answer": "Operación rechazada por aprobación humana.",
    }


def approval_router(
    state: AgentState
) -> Literal["validation", "rejected"]:

    if state.get("approval_decision"):
        return "validation"

    return "rejected"


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
    "approval",
    approval_node
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
        "approval": "approval",
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


builder.add_conditional_edges(
    "approval",
    approval_router,
    {
        "validation": "validation",
        "rejected": END,
    }
)


builder.add_edge(
    "validation",
    END
)


graph = builder.compile()
