"""Consulta el estado del webhook de Telegram usando únicamente httpx."""

import os
from pathlib import Path

import httpx
from dotenv import load_dotenv


def main() -> None:
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    token = os.getenv("TELEGRAM_TOKEN", "")
    if not token:
        raise SystemExit("Configura TELEGRAM_TOKEN.")

    response = httpx.get(
        f"https://api.telegram.org/bot{token}/getWebhookInfo",
        timeout=20.0,
    )
    print(response.text)
    response.raise_for_status()


if __name__ == "__main__":
    main()
