"""Contrato HTTP, documentación y memoria de la API sin llamadas a Gemini."""

import logging
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from api.app import app
from src.router.graph import Decision, graph


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_chat_reutiliza_grafo_y_thread(client, monkeypatch):
    calls = []

    def invoke(inputs, config):
        calls.append((inputs, config))
        return {
            "ruta": "preventa",
            "motivo": "Consulta por un producto.",
            "respuesta": "Respuesta de prueba.",
            "messages": [],
        }

    assert app.state.router_graph is graph
    monkeypatch.setattr(graph, "invoke", invoke)
    body = {"user_id": "cliente-123", "texto": "¿Hay poleras?"}
    for _ in range(2):
        response = client.post("/chat", json=body)
        assert response.status_code == 200
        assert response.json() == {
            "ruta": "preventa", "motivo": "Consulta por un producto.",
            "respuesta": "Respuesta de prueba.",
        }
    assert calls == [
        ({"mensaje": body["texto"]}, {"configurable": {"thread_id": body["user_id"]}})
    ] * 2
    assert app.state.router_graph is graph


@pytest.mark.parametrize("body", [
    {}, {"user_id": "cliente"}, {"texto": "hola"},
    {"user_id": "cliente", "texto": "   "},
    {"user_id": "", "texto": "hola"},
    {"user_id": "cliente", "texto": None},
])
def test_body_invalido(client, body, monkeypatch):
    def unexpected(*args, **kwargs):
        pytest.fail("Un body inválido no debe llegar al grafo")

    monkeypatch.setattr(graph, "invoke", unexpected)
    assert client.post("/chat", json=body).status_code == 422


def test_error_modelo_no_filtra_detalles(client, monkeypatch, caplog):
    def fail(*args, **kwargs):
        raise RuntimeError("detalle-interno-ficticio")

    monkeypatch.setattr(graph, "invoke", fail)
    with caplog.at_level(logging.ERROR, logger="api.app"):
        response = client.post("/chat", json={"user_id": "cliente", "texto": "hola"})
    assert response.status_code == 502
    assert response.json() == {
        "detail": "No se pudo obtener una respuesta del modelo. Inténtalo nuevamente más tarde."
    }
    assert "detalle-interno-ficticio" not in response.text
    assert "Traceback" not in response.text
    assert "detalle-interno-ficticio" in caplog.text


@pytest.mark.parametrize("payload", [{"update_id": 123}, [1, 2], "hola", 42, False])
def test_telegram_ignora_updates_sin_texto(client, payload, monkeypatch):
    monkeypatch.setenv("TELEGRAM_SECRET", "secreto-prueba")
    response = client.post(
        "/telegram", json=payload, headers={"X-Telegram-Bot-Api-Secret-Token": "secreto-prueba"}
    )
    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_telegram_rechaza_secreto_invalido(client, monkeypatch):
    monkeypatch.setenv("TELEGRAM_SECRET", "secreto-correcto")
    response = client.post(
        "/telegram",
        json={},
        headers={"X-Telegram-Bot-Api-Secret-Token": "secreto-incorrecto"},
    )
    assert response.status_code == 403


def test_telegram_invoca_router_y_envia_respuesta(client, monkeypatch):
    monkeypatch.setenv("TELEGRAM_SECRET", "secreto-prueba")
    monkeypatch.setenv("TELEGRAM_TOKEN", "token-ficticio")
    calls = []

    def invoke(inputs, config):
        calls.append((inputs, config))
        return {"ruta": "postventa", "respuesta": "Respuesta de prueba."}

    class FakeResponse:
        def raise_for_status(self):
            pass

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def post(self, url, json):
            calls.append((url, json))
            return FakeResponse()

    monkeypatch.setattr(graph, "invoke", invoke)
    monkeypatch.setattr("api.app.httpx.AsyncClient", lambda timeout: FakeClient())
    update = {"message": {"chat": {"id": 4521}, "text": "Mi pedido llegó roto"}}
    response = client.post(
        "/telegram", json=update, headers={"X-Telegram-Bot-Api-Secret-Token": "secreto-prueba"}
    )
    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert calls == [
        ({"mensaje": "Mi pedido llegó roto"}, {"configurable": {"thread_id": "4521"}}),
        (
            "https://api.telegram.org/bottoken-ficticio/sendMessage",
            {"chat_id": 4521, "text": "Respuesta de prueba."},
        ),
    ]


def test_openapi_y_swagger(client):
    assert client.get("/docs").status_code == 200
    schema = client.get("/openapi.json").json()
    assert schema["info"]["title"] == "Ecommerce Router API"
    assert "/telegram" not in schema["paths"]
    chat = schema["paths"]["/chat"]["post"]
    assert chat["tags"] == ["chat"]
    assert set(chat["responses"]) == {"200", "422", "502"}
    for model in ("ChatRequest", "ChatResponse"):
        for field in schema["components"]["schemas"][model]["properties"].values():
            assert field["description"]
            assert field["examples"]


def test_chat_memoria_real_con_modelo_simulado(client, monkeypatch):
    calls = []
    monkeypatch.setenv("GOOGLE_API_KEY", "valor-ficticio-de-prueba")
    monkeypatch.setenv("MODELO", "modelo-ficticio-de-prueba")

    class FakeModel:
        def __init__(self, **kwargs):
            pass

        def with_structured_output(self, schema):
            return self

        def invoke(self, messages):
            calls.append(messages)
            return Decision(ruta="postventa", motivo="Consulta sobre un pedido existente.")

    monkeypatch.setattr("src.router.graph.ChatGoogleGenerativeAI", FakeModel)
    user_a, user_b = str(uuid4()), str(uuid4())
    for user, text in [(user_a, "Mi pedido llegó roto"), (user_a, "¿Cómo lo devuelvo?"), (user_b, "Mi pedido no llegó")]:
        response = client.post("/chat", json={"user_id": user, "texto": text})
        assert response.status_code == 200
        assert response.json()["ruta"] == "postventa"
    assert len(calls[1]) == 4
    assert calls[1][1].content == "Mi pedido llegó roto"
    assert len(calls[2]) == 2
