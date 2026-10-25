"""Lanzador de agentes; ejecutar desde la raíz del proyecto."""

import argparse
import importlib
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage


def main() -> None:
    parser = argparse.ArgumentParser(description="Ejecuta un agente LangGraph.")
    parser.add_argument("agente", help="Nombre de la carpeta del agente en src/")
    parser.add_argument("mensaje", nargs="?", help="Mensaje para el agente")
    parser.add_argument("--saltos", action="store_true", help="Imprime los nodos recorridos")
    parser.add_argument("--diagrama", action="store_true", help="Imprime Mermaid sin ejecutar")
    parser.add_argument("--thread-id", default=None, help="Identificador de conversación")
    args = parser.parse_args()

    if not args.agente.isidentifier() or args.agente.startswith("_"):
        parser.error("El nombre del agente debe ser un identificador de Python público.")
    if not args.diagrama and not args.mensaje:
        parser.error("Indica un mensaje o usa --diagrama.")

    root = Path(__file__).resolve().parent
    if not (root / "src" / args.agente / "graph.py").is_file():
        parser.error(f"No existe el agente: src/{args.agente}/graph.py")
    load_dotenv(root / ".env")
    graph = importlib.import_module(f"src.{args.agente}.graph").graph

    if args.diagrama:
        print(graph.get_graph().draw_mermaid())
        return

    try:
        inputs = {"mensaje": args.mensaje, "messages": [HumanMessage(content=args.mensaje)]}
        config = {"configurable": {"thread_id": args.thread_id or str(uuid4())}}
        if args.saltos:
            recorrido = []
            for update in graph.stream(
                inputs, config=config, stream_mode="updates"
            ):
                for node, state in update.items():
                    recorrido.append(node)
                    print(f"[salto] {node}")
                    if state and state.get("motivo"):
                        print(f"Motivo: {state['motivo']}")
                    if state and state.get("respuesta"):
                        print(state["respuesta"])
                    elif state and state.get("messages") and node != "router":
                        print(state["messages"][-1].text)
            print(f"Recorrido: {' → '.join(recorrido)}")
        else:
            result = graph.invoke(inputs, config=config)
            print(result.get("respuesta") or result["messages"][-1].text)
    except (ValueError, RuntimeError) as exc:
        parser.exit(1, f"Error: {exc}\n")


if __name__ == "__main__":
    main()
