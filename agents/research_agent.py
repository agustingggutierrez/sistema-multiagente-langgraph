from state import AgentState
from tools import buscar_informacion


def research_agent(state: AgentState):

    consulta = state["query"]

    resultado = buscar_informacion(consulta)

    print("\n[RESEARCH AGENT]")
    print(resultado)

    return {
        "research_result": resultado
    }