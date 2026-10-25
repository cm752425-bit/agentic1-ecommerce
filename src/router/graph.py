"""Estado, nodos y aristas del enrutador de ecommerce."""

import os
from typing import Literal

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, MessagesState, StateGraph
from pydantic import BaseModel, Field

from .prompts import (
    AGENTE_POSTVENTA_PROMPT,
    AGENTE_PREVENTA_PROMPT,
    RESPUESTA_GENERICA_PROMPT,
    ROUTER_PROMPT,
)


class Decision(BaseModel):
    ruta: Literal["preventa", "postventa", "generica"] = Field(
        description="A qué agente va el mensaje."
    )
    motivo: str = Field(description="Una frase: por qué esa ruta.")


class RouterState(MessagesState):
    mensaje: str
    ruta: Literal["preventa", "postventa", "generica"]
    motivo: str
    respuesta: str


def router(state: RouterState) -> dict:
    api_key = os.getenv("GOOGLE_API_KEY")
    model_name = os.getenv("MODELO")
    if not api_key or not model_name:
        raise ValueError("Configura GOOGLE_API_KEY y MODELO en .env o en el entorno.")

    history = list(state.get("messages", []))
    new_messages = []
    if not (
        history
        and isinstance(history[-1], HumanMessage)
        and history[-1].content == state["mensaje"]
    ):
        new_messages = [HumanMessage(content=state["mensaje"])]
        history.extend(new_messages)

    llm = ChatGoogleGenerativeAI(model=model_name, api_key=api_key)
    decision = llm.with_structured_output(Decision).invoke(
        [SystemMessage(content=ROUTER_PROMPT), *history]
    )
    return {
        "ruta": decision.ruta,
        "motivo": decision.motivo,
        "respuesta": "",
        "messages": new_messages,
    }


def agente_preventa(state: RouterState) -> dict:
    respuesta = AGENTE_PREVENTA_PROMPT.format(mensaje=state["mensaje"])
    return {"respuesta": respuesta, "messages": [AIMessage(content=respuesta)]}


def agente_postventa(state: RouterState) -> dict:
    respuesta = AGENTE_POSTVENTA_PROMPT.format(mensaje=state["mensaje"])
    return {"respuesta": respuesta, "messages": [AIMessage(content=respuesta)]}


def respuesta_generica(state: RouterState) -> dict:
    respuesta = RESPUESTA_GENERICA_PROMPT
    return {"respuesta": respuesta, "messages": [AIMessage(content=respuesta)]}


def elegir_ruta(state: RouterState) -> str:
    return state["ruta"]


builder = StateGraph(RouterState)
builder.add_node("router", router)
builder.add_node("agente_preventa", agente_preventa)
builder.add_node("agente_postventa", agente_postventa)
builder.add_node("respuesta_generica", respuesta_generica)
builder.add_edge(START, "router")
builder.add_conditional_edges(
    "router",
    elegir_ruta,
    {
        "preventa": "agente_preventa",
        "postventa": "agente_postventa",
        "generica": "respuesta_generica",
    },
)
for node in ("agente_preventa", "agente_postventa", "respuesta_generica"):
    builder.add_edge(node, END)

graph = builder.compile(checkpointer=MemorySaver())
