from collections import Counter


BASE_CONOCIMIENTO = {
    "langgraph": (
        "LangGraph es una biblioteca para crear aplicaciones "
        "basadas en grafos y agentes con estado."
    ),
    "python": (
        "Python es un lenguaje de programación de propósito general "
        "muy utilizado en inteligencia artificial."
    ),
    "agentes": (
        "Los sistemas multiagente utilizan diferentes agentes "
        "especializados para resolver partes de un problema."
    ),
    "inteligencia artificial": (
        "La inteligencia artificial permite construir sistemas "
        "capaces de realizar tareas que normalmente requieren "
        "razonamiento humano."
    ),
}


def buscar_informacion(consulta: str) -> str:
    """Herramienta utilizada por el Research Agent."""

    consulta = consulta.lower()

    resultados = []

    for tema, informacion in BASE_CONOCIMIENTO.items():

        if tema in consulta:
            resultados.append(informacion)

        else:
            palabras = consulta.split()

            if any(palabra in tema for palabra in palabras):
                resultados.append(informacion)

    if not resultados:
        return (
            "No se encontraron coincidencias exactas en la base local. "
            "La consulta fue: " + consulta
        )

    return " ".join(resultados)


def extraer_palabras_clave(texto: str) -> str:
    """Herramienta utilizada por el Analyst Agent."""

    palabras = [
        palabra.lower().strip(".,")
        for palabra in texto.split()
        if len(palabra) > 5
    ]

    frecuentes = Counter(palabras).most_common(5)

    if not frecuentes:
        return "No se encontraron palabras clave."

    return ", ".join(
        palabra for palabra, _ in frecuentes
    )