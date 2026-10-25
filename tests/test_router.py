"""Verifica el grafo con decisiones simuladas, sin evaluar el modelo real."""

import sys
from uuid import uuid4

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from main import main
from src.router.graph import Decision, graph


@pytest.fixture
def fake_llm(monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "valor-ficticio-de-prueba")
    monkeypatch.setenv("MODELO", "modelo-ficticio-de-prueba")
    calls = []
    decisions = []

    class FakeModel:
        def __init__(self, **kwargs):
            assert kwargs["model"] == "modelo-ficticio-de-prueba"

        def with_structured_output(self, schema):
            assert schema is Decision
            return self

        def invoke(self, messages):
            calls.append(messages)
            return decisions.pop(0)

    monkeypatch.setattr("src.router.graph.ChatGoogleGenerativeAI", FakeModel)
    return decisions, calls


@pytest.mark.parametrize(
    "ruta,nodo",
    [
        ("preventa", "agente_preventa"),
        ("postventa", "agente_postventa"),
        ("generica", "respuesta_generica"),
    ],
)
def test_aristas_estado_y_cascarones(fake_llm, ruta, nodo):
    decisions, calls = fake_llm
    decisions.append(Decision(ruta=ruta, motivo="Motivo simulado."))
    config = {"configurable": {"thread_id": str(uuid4())}}
    updates = list(graph.stream({"mensaje": "Mensaje de prueba"}, config, stream_mode="updates"))
    assert [next(iter(update)) for update in updates] == ["router", nodo]
    state = graph.get_state(config).values
    assert state["ruta"] == ruta
    assert state["motivo"] == "Motivo simulado."
    assert state["respuesta"] == state["messages"][-1].content
    assert isinstance(state["messages"][0], HumanMessage)
    assert isinstance(state["messages"][-1], AIMessage)
    assert len(calls) == 1  # Ningún cascarón llama al modelo.


def test_memoria_por_thread_id(fake_llm):
    decisions, calls = fake_llm
    config_a = {"configurable": {"thread_id": str(uuid4())}}
    config_b = {"configurable": {"thread_id": str(uuid4())}}
    for config, mensaje, ruta in [
        (config_a, "Mi pedido llegó roto", "postventa"),
        (config_a, "¿Cómo lo devuelvo?", "postventa"),
        (config_b, "hola", "generica"),
    ]:
        decisions.append(Decision(ruta=ruta, motivo="Motivo simulado."))
        graph.invoke({"mensaje": mensaje}, config)

    assert len(calls[1]) == 4  # Sistema, primer usuario, cascarón, segundo usuario.
    assert calls[1][1].content == "Mi pedido llegó roto"
    assert len(calls[2]) == 2  # El hilo B no recibe mensajes del hilo A.
    assert len(graph.get_state(config_a).values["messages"]) == 4
    assert len(graph.get_state(config_b).values["messages"]) == 2


def test_cli_saltos_y_motivo(fake_llm, monkeypatch, capsys):
    decisions, calls = fake_llm
    decisions.append(Decision(ruta="preventa", motivo="Pregunta por un producto."))
    monkeypatch.setattr(sys, "argv", ["main.py", "router", "¿Hay poleras?", "--saltos"])
    main()
    output = capsys.readouterr().out
    assert "router → agente_preventa" in output
    assert "Motivo: Pregunta por un producto." in output
    assert "Soy el agente de preventa. Recibí: ¿Hay poleras?." in output
    assert len(calls[0]) == 2  # El CLI no duplica el mensaje del usuario.


def test_diagrama_no_necesita_modelo(fake_llm, monkeypatch, capsys):
    _, calls = fake_llm
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.setattr(sys, "argv", ["main.py", "router", "--diagrama"])
    main()
    output = capsys.readouterr().out
    for node in ("router", "agente_preventa", "agente_postventa", "respuesta_generica"):
        assert node in output
    assert not calls
