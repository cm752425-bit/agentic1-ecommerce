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

## Conectar Telegram

La ruta `POST /telegram` es provisional: hoy acepta JSON y responde
`{"ok": true}`, pero todavía no procesa mensajes ni valida el secreto. Antes de
usar un bot real debe implementarse la parte 5: verificar el encabezado
`X-Telegram-Bot-Api-Secret-Token` contra `TELEGRAM_SECRET`, invocar `/chat` y
responder mediante la API de Telegram.

Cuando esa implementación esté terminada:

1. Crea el bot con `@BotFather` y guarda el token únicamente en `TELEGRAM_TOKEN`.
2. Genera un `TELEGRAM_SECRET` privado y configúralo también en Heroku.
3. Configura el webhook HTTPS con estos comandos PowerShell, reemplazando los valores:

```powershell
$env:TELEGRAM_TOKEN = "TOKEN_ENTREGADO_POR_BOTFATHER"
$env:TELEGRAM_SECRET = "SECRETO_LARGO_Y_ALEATORIO"
$env:PUBLIC_URL = "https://NOMBRE_UNICO_DE_APP.herokuapp.com"

$body = @{ url = "$env:PUBLIC_URL/telegram"; secret_token = $env:TELEGRAM_SECRET } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "https://api.telegram.org/bot$env:TELEGRAM_TOKEN/setWebhook" -ContentType "application/json" -Body $body
Invoke-RestMethod -Uri "https://api.telegram.org/bot$env:TELEGRAM_TOKEN/getWebhookInfo"
```

Para eliminar el webhook:

```powershell
Invoke-RestMethod -Method Post -Uri "https://api.telegram.org/bot$env:TELEGRAM_TOKEN/deleteWebhook"
```

No conectes Telegram al endpoint provisional: aún no valida
`X-Telegram-Bot-Api-Secret-Token`.
