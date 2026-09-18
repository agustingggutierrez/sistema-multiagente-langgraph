from langchain_google_genai import ChatGoogleGenerativeAI

from state import AgentState


model = ChatGoogleGenerativeAI(
    model="gemini-3.6-flash",
    thinking_level="minimal",
    max_output_tokens=512,
)


def research_agent(state: AgentState):
    consulta = state["query"]

    prompt = (
        "Actua como agente de investigacion dentro de un sistema "
        "multiagente de LangGraph. "
        "Responde en español de forma clara y breve, en un maximo "
        "de 3 oraciones. "
        "Entrega solamente informacion util para que otro agente "
        "pueda analizarla despues.\n\n"
        f"Consulta: {consulta}"
    )

    response = model.invoke(prompt)

    resultado = response.text.strip()

    if not resultado:
        raise RuntimeError(
            "Gemini devolvio una respuesta vacia."
        )

    print("\n[RESEARCH AGENT - GEMINI]")
    print(resultado)

    if response.usage_metadata:
        print(
            "[RESEARCH AGENT - TOKENS]",
            response.usage_metadata,
        )

    return {
        "research_result": resultado
    }
