from graph import graph


def main():

    print("=" * 50)
    print("SISTEMA MULTIAGENTE CON LANGGRAPH")
    print("=" * 50)

    consulta = input(
        "\nIngrese una consulta: "
    )

    resultado = graph.invoke(
        {
            "query": consulta
        }
    )

    print("\n" + "=" * 50)
    print("RESULTADO FINAL")
    print("=" * 50)

    print(
        resultado["final_answer"]
    )


if __name__ == "__main__":
    main()