from graph import graph


def main():
    grafo = graph.get_graph()

    # Generar código Mermaid desde el grafo real
    mermaid = grafo.draw_mermaid()

    with open("graph.mmd", "w", encoding="utf-8") as archivo:
        archivo.write(mermaid)

    # Generar imagen PNG desde el mismo grafo
    png = grafo.draw_mermaid_png()

    with open("graph.png", "wb") as archivo:
        archivo.write(png)

    print("Diagramas generados correctamente.")
    print("Archivo Mermaid: graph.mmd")
    print("Imagen PNG: graph.png")


if __name__ == "__main__":
    main()