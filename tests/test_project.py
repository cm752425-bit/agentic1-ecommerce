"""Comprobaciones sin credenciales ni llamadas a servicios externos."""

import sys

from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, HumanMessage

from api.app import app
from main import main
from src.asistente.graph import graph


def test_health(monkeypatch):
    monkeypatch.setenv("MODELO", "modelo-ficticio-de-prueba")
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"ok": True, "modelo": "modelo-ficticio-de-prueba"}


def test_diagrama_sin_credenciales(monkeypatch, capsys):
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.setattr(sys, "argv", ["main.py", "asistente", "--diagrama"])
    main()
    output = capsys.readouterr().out
    assert "graph TD" in output
    assert "responder" in output


def test_agente_y_saltos(monkeypatch, capsys):
    monkeypatch.setenv("GOOGLE_API_KEY", "valor-ficticio-de-prueba")
    monkeypatch.setenv("MODELO", "modelo-ficticio-de-prueba")

    class FakeModel:
        def __init__(self, **kwargs):
            pass

        def invoke(self, messages):
            assert isinstance(messages[-1], HumanMessage)
            assert messages[-1].content == "Hola"
            return AIMessage(content="Respuesta simulada")

    monkeypatch.setattr("src.asistente.graph.ChatGoogleGenerativeAI", FakeModel)
    result = graph.invoke({"messages": [HumanMessage(content="Hola")]})
    assert result["messages"][-1].content == "Respuesta simulada"
    monkeypatch.setattr(sys, "argv", ["main.py", "asistente", "Hola", "--saltos"])
    main()
    output = capsys.readouterr().out
    assert "[salto] responder" in output
    assert "Respuesta simulada" in output
