from state import AgentState
from tools import extraer_palabras_clave


def analyst_agent(state: AgentState):

    investigacion = state["research_result"]

    palabras_clave = extraer_palabras_clave(investigacion)

    analisis = (
        f"Análisis de la investigación:\n"
        f"{investigacion}\n\n"
        f"Conceptos principales: {palabras_clave}"
    )

    print("\n[ANALYST AGENT]")
    print(analisis)

    return {
        "analysis_result": analisis
    }