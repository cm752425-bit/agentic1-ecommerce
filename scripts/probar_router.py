"""Prueba real de los seis mensajes: python -m scripts.probar_router."""

from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv

from src.router.graph import graph


CASOS = [
    ("¿tienen la polera azul en talla M?", "preventa"),
    ("mi pedido 4521 llegó roto", "postventa"),
    ("hola", "generica"),
    ("¿cuánto cuesta el envío a Valparaíso?", "preventa"),
    ("quiero devolver unas zapatillas", "postventa"),
    ("¿qué hora es en Tokio?", "generica"),
]


def main() -> None:
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    fallos = 0
    for mensaje, esperada in CASOS:
        result = graph.invoke(
            {"mensaje": mensaje},
            config={"configurable": {"thread_id": str(uuid4())}},
        )
        print(f"{mensaje} -> {result['ruta']}", flush=True)
        print(f"  Motivo: {result['motivo']}", flush=True)
        fallos += result["ruta"] != esperada
    if fallos:
        raise SystemExit(f"{fallos} rutas no coinciden con las esperadas.")


if __name__ == "__main__":
    main()
