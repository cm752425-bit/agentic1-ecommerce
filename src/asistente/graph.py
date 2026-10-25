"""Construcción y nodos del grafo del asistente."""

import os

from langchain_core.messages import SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import END, START, MessagesState, StateGraph

from .prompts import RESPONDER_PROMPT


def responder(state: MessagesState) -> dict:
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("Configura GOOGLE_API_KEY en .env o en el entorno.")
    model_name = os.getenv("MODELO")
    if not model_name:
        raise ValueError("Configura MODELO en .env o en el entorno.")
    model = ChatGoogleGenerativeAI(model=model_name, api_key=api_key)
    response = model.invoke(
        [SystemMessage(content=RESPONDER_PROMPT), *state["messages"]]
    )
    return {"messages": [response]}


builder = StateGraph(MessagesState)
builder.add_node("responder", responder)
builder.add_edge(START, "responder")
builder.add_edge("responder", END)
graph = builder.compile()
