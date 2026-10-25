"""API del router de ecommerce y documentación interactiva."""

from contextlib import asynccontextmanager
import logging
import os
from pathlib import Path
from typing import Annotated, Any, Literal

from dotenv import load_dotenv
from fastapi import Body, FastAPI, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # El módulo compila y exporta un único grafo; las peticiones lo reutilizan.
    from src.router.graph import graph

    app.state.router_graph = graph
    yield


class HealthResponse(BaseModel):
    ok: bool = Field(description="Indica que la API está disponible.", examples=[True])
    modelo: str = Field(
        description="Modelo seleccionado mediante la variable de entorno MODELO.",
        examples=["gemini-3.5-flash-lite"],
    )


class ChatRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    user_id: str = Field(
        min_length=1,
        description="Identificador del usuario; se utiliza como thread_id para la memoria.",
        examples=["cliente-123"],
    )
    texto: str = Field(
        min_length=1,
        description="Mensaje que el router clasificará usando el contexto del usuario.",
        examples=["¿Tienen la polera azul en talla M?"],
    )


class ChatResponse(BaseModel):
    ruta: Literal["preventa", "postventa", "generica"] = Field(
        description="Destino elegido: preventa, postventa o generica.",
        examples=["preventa"],
    )
    motivo: str = Field(
        description="Una frase que explica por qué se eligió esa ruta.",
        examples=["El usuario consulta la disponibilidad de un producto antes de comprar."],
    )
    respuesta: str = Field(
        description="Respuesta del nodo destino; actualmente los destinos son cascarones.",
        examples=[
            "Soy el agente de preventa. Recibí: ¿Tienen la polera azul en talla M?. "
            "Pronto podré ayudarte con productos y compras."
        ],
    )


class ErrorResponse(BaseModel):
    detail: str = Field(
        description="Mensaje de error público, sin credenciales ni detalles internos.",
        examples=["No se pudo obtener una respuesta del modelo. Inténtalo nuevamente más tarde."],
    )


app = FastAPI(
    title="Ecommerce Router API",
    version="0.2.0",
    description=(
        "Clasifica mensajes de una tienda en tres rutas: **preventa** para productos "
        "y compras, **postventa** para pedidos existentes y reclamos, y **generica** "
        "para saludos o consultas ajenas a la tienda. Conserva contexto por usuario."
    ),
    openapi_tags=[
        {"name": "salud", "description": "Disponibilidad de la API y modelo configurado."},
        {"name": "chat", "description": "Clasificación de mensajes con memoria por usuario."},
        {"name": "telegram", "description": "Webhook reservado para la integración de Telegram."},
    ],
    lifespan=lifespan,
)


@app.get(
    "/health",
    tags=["salud"],
    response_model=HealthResponse,
    summary="Comprobar el estado de la API",
    description="Devuelve el modelo configurado; no llama al proveedor ni verifica su saldo.",
)
def health() -> HealthResponse:
    return HealthResponse(ok=True, modelo=os.getenv("MODELO", ""))


@app.post(
    "/chat",
    tags=["chat"],
    response_model=ChatResponse,
    summary="Enrutar un mensaje de ecommerce",
    description=(
        "Envía un mensaje al router y devuelve ruta, motivo y respuesta. "
        "Reutiliza user_id para conservar el contexto mientras el servidor esté activo."
    ),
    responses={
        200: {"description": "Mensaje clasificado y respuesta del nodo destino."},
        422: {"description": "Body inválido: user_id y texto son obligatorios y no pueden estar vacíos."},
        502: {
            "model": ErrorResponse,
            "description": "El modelo falló o no entregó una respuesta válida.",
        },
    },
)
def chat(body: ChatRequest, request: Request) -> ChatResponse:
    try:
        result = request.app.state.router_graph.invoke(
            {"mensaje": body.texto},
            config={"configurable": {"thread_id": body.user_id}},
        )
        return ChatResponse(
            ruta=result["ruta"], motivo=result["motivo"], respuesta=result["respuesta"]
        )
    except Exception:
        logger.exception("Falló la invocación del router de ecommerce")
        raise HTTPException(
            status_code=502,
            detail="No se pudo obtener una respuesta del modelo. Inténtalo nuevamente más tarde.",
        ) from None


@app.post("/telegram", tags=["telegram"], include_in_schema=False)
def telegram(payload: Annotated[Any, Body()] = None) -> dict[str, bool]:
    """Acuse provisional; el procesamiento y la verificación llegan en la parte 5."""
    return {"ok": True}
