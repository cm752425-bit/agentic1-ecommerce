# Ecommerce Router API

Proyecto en Python 3.12 que usa LangGraph, LangChain, Gemini y FastAPI para
clasificar mensajes de un ecommerce. El router elige una de estas rutas:

- `preventa`: productos, precios, tallas, stock, promociones, pagos y consultas
  previas a una compra.
- `postventa`: pedidos existentes, seguimiento, reclamos, devoluciones, cambios,
  garantías o productos dañados.
- `generica`: saludos sin pedido y consultas ajenas a la tienda.

Los tres destinos son cascarones. El router usa salida estructurada de Gemini y
`MemorySaver` conserva el contexto por `thread_id` mientras vive el proceso.

## Requisitos

- Python 3.12
- Una clave de Google Gemini con saldo disponible
- Git
- Heroku CLI para desplegar

## Configuración local

Desde la raíz del proyecto, en PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Edita `.env` y configura como mínimo:

```dotenv
GOOGLE_API_KEY=tu_clave_de_google
MODELO=gemini-3.5-flash-lite
```

No publiques `.env`; está excluido por `.gitignore`.

## Ejecutar el router

Clasificar un mensaje:

```powershell
python main.py router "¿Tienen la polera azul en talla M?"
```

Mostrar los nodos recorridos y el motivo:

```powershell
python main.py router "Mi pedido 4521 llegó roto" --saltos --thread-id cliente-123
```

Mostrar el diagrama Mermaid sin llamar a Gemini:

```powershell
python main.py router --diagrama
```

Ejecutar los seis casos de ejemplo contra Gemini:

```powershell
python -m scripts.probar_router
```

`MemorySaver` vive en memoria. Varias invocaciones conservan contexto solamente
si usan el mismo `thread_id` dentro del mismo proceso.

## Levantar la API

Desde la raíz y con `.venv` activo:

```powershell
uvicorn api.app:app --reload --port 8000
```

Abre estos enlaces:

- Swagger: http://localhost:8000/docs
- Salud: http://localhost:8000/health

El grafo se compila una vez al arrancar la aplicación y `/chat` usa `user_id`
como `thread_id`.

Ejemplo con `curl`:

```bash
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"cliente-123","texto":"¿Tienen la polera azul en talla M?"}'
```

Ejemplo para PowerShell 5.1:

```powershell
$body = @{ user_id = "cliente-123"; texto = "¿Tienen la polera azul en talla M?" } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "http://localhost:8000/chat" -ContentType "application/json; charset=utf-8" -Body ([System.Text.Encoding]::UTF8.GetBytes($body))
```

Si falta `texto`, FastAPI responde `422`. Si Gemini falla, responde `502` y deja
el detalle únicamente en el log del servidor.

## Pruebas

Ejecutar todas las pruebas sin consumir Gemini:

```powershell
python -m pytest
```

Ejecutar únicamente las pruebas del router o de la API:

```powershell
python -m pytest tests/test_router.py -v
python -m pytest tests/test_api.py -v
```

## Bruno

Abre la carpeta `bruno/` como colección y selecciona el entorno `Local`. Incluye
peticiones para salud, preventa, postventa y genérica. Para Heroku, reemplaza la
URL de ejemplo en `bruno/environments/Heroku.bru` y selecciona ese entorno.

## Desplegar en Heroku

El proyecto incluye `.python-version` con Python 3.12 y este `Procfile`:

```text
web: uvicorn api.app:app --host 0.0.0.0 --port $PORT
```

Después de publicar el repositorio en GitHub, instala Heroku CLI y ejecuta desde
la raíz. Sustituye `NOMBRE_UNICO_DE_APP` y los valores de configuración:

```powershell
heroku login
heroku create NOMBRE_UNICO_DE_APP
heroku config:set GOOGLE_API_KEY="TU_CLAVE_DE_GOOGLE" MODELO="gemini-3.5-flash-lite" TELEGRAM_TOKEN="" TELEGRAM_SECRET="CAMBIA_ESTE_SECRETO" PUBLIC_URL="https://NOMBRE_UNICO_DE_APP.herokuapp.com" --app NOMBRE_UNICO_DE_APP
git push heroku main
heroku ps:scale web=1 --app NOMBRE_UNICO_DE_APP
heroku logs --tail --app NOMBRE_UNICO_DE_APP
```

Comprueba el despliegue:

```powershell
Invoke-RestMethod "https://NOMBRE_UNICO_DE_APP.herokuapp.com/health"
Start-Process "https://NOMBRE_UNICO_DE_APP.herokuapp.com/docs"
```

No configures secretos en archivos versionados. Heroku proporciona `$PORT`
automáticamente; no hace falta añadirlo a `.env`.

## Telegram

La integración usa únicamente `httpx`, sin librerías de bots. El webhook lee
`message.chat.id` y `message.text`, ignora updates sin texto, verifica
`X-Telegram-Bot-Api-Secret-Token` contra `TELEGRAM_SECRET`, invoca el router con
`thread_id=chat_id` y envía la respuesta mediante `sendMessage`. Un secreto
incorrecto devuelve `403`; los updates válidos reciben `200` incluso cuando se
registra un error interno.

Primero crea el bot hablando con `@BotFather`:

1. Envía `/newbot` y sigue sus instrucciones.
2. Copia el token entregado únicamente a `TELEGRAM_TOKEN` en `.env`.
3. Elige un secreto privado y configúralo como `TELEGRAM_SECRET` en `.env`.

Pasos finales, en orden, para Heroku:

1. Configura los secretos en Heroku (ejecuta desde la raíz y reemplaza los valores):

```powershell
heroku config:set TELEGRAM_TOKEN="TOKEN_ENTREGADO_POR_BOTFATHER" TELEGRAM_SECRET="SECRETO_LARGO_Y_ALEATORIO" --app NOMBRE_UNICO_DE_APP
```

2. Haz commit y push de los cambios a GitHub y a Heroku:

```powershell
git add api/app.py scripts/set_webhook.py scripts/webhook_info.py tests/test_api.py README.md
git commit -m "connect telegram webhook"
git push origin main
git push heroku main
```

3. Configura el webhook con la URL pública de Heroku y confirma su estado:

```powershell
$env:PUBLIC_URL = "https://NOMBRE_UNICO_DE_APP.herokuapp.com"
python scripts/set_webhook.py
python scripts/webhook_info.py
```

`set_webhook.py` usa `PUBLIC_URL + "/telegram"` y `TELEGRAM_SECRET`; `webhook_info.py`
permite revisar `url`, `pending_update_count` y cualquier `last_error_message`.

4. Escribe al bot los seis mensajes del prompt 2 y verifica en los logs que cada
   ruta sea correcta:

```powershell
heroku logs --tail --app NOMBRE_UNICO_DE_APP
```

Las rutas esperadas son, en orden: `preventa`, `postventa`, `generica`,
`preventa`, `postventa`, `generica`. La API registra líneas como
`Telegram chat_id=... ruta=postventa`.

5. Si no responde, revisa: el webhook debe apuntar exactamente a
`https://NOMBRE_UNICO_DE_APP.herokuapp.com/telegram`, `TELEGRAM_SECRET` debe ser
idéntico en Heroku y en `set_webhook.py`, y `TELEGRAM_TOKEN` debe ser el token
actual entregado por BotFather. Ejecuta `python scripts/webhook_info.py` y revisa
`last_error_message`.

### Prueba local opcional

Con `cloudflared` instalado, levanta la API local y crea un túnel:

```powershell
uvicorn api.app:app --reload --port 8000
cloudflared tunnel --url http://localhost:8000
```

Usa la URL HTTPS que imprime `cloudflared` como `PUBLIC_URL`, con las variables
`TELEGRAM_TOKEN` y `TELEGRAM_SECRET` cargadas en `.env`, y ejecuta:

```powershell
python scripts/set_webhook.py
python scripts/webhook_info.py
```

Para volver al despliegue de Heroku, ejecuta de nuevo `set_webhook.py` con la URL
de Heroku.
