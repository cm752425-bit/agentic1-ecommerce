# Reglas del proyecto

- Usar Python 3.12 y el entorno virtual `.venv`.
- Los agentes van en `src/{nombre_agente}/` con `graph.py`, `prompts.py` y `tools.py`.
- Cada nodo tiene su propio prompt en `prompts.py`; no incluir prompts ni reglas de comportamiento en `graph.py`.
- Cada `graph.py` expone el grafo compilado como `graph`. Usar estado de mensajes compatible con `MessagesState`.
- Ejecutar los agentes desde la raíz: `python main.py {nombre_agente} "mensaje"`.
- El flag `--saltos` imprime los nodos por los que pasó el grafo.
- El flag `--diagrama` imprime el Mermaid del grafo sin ejecutarlo y sin necesitar credenciales.
- La API va en `api/app.py` (FastAPI). Levantar con `uvicorn api.app:app --reload --port 8000`.
- Los scripts sueltos van en `scripts/` y las pruebas en `tests/` (pytest).
- Para Heroku, mantener un `Procfile` con `web: uvicorn api.app:app --host 0.0.0.0 --port $PORT` y un archivo `.python-version` con `3.12`.
- Mantener `requirements.txt` siempre actualizado al añadir, quitar o actualizar dependencias.
- Leer la configuración desde variables de entorno; usar `python-dotenv` para cargar `.env` en local sin sobrescribir las variables del entorno.
- Nunca incluir credenciales reales en el código, pruebas ni archivos versionados. Documentar las variables en `.env.example`.
- Mantener `.env`, `.venv`, `__pycache__` y `.langgraph_api` en `.gitignore`.
- En la integración de Telegram, verificar el encabezado `X-Telegram-Bot-Api-Secret-Token` contra `TELEGRAM_SECRET` antes de procesar cada webhook.
