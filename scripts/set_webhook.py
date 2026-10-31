"""Configura el webhook de Telegram usando únicamente httpx."""

import os
from pathlib import Path

import httpx
from dotenv import load_dotenv


def main() -> None:
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    token = os.getenv("TELEGRAM_TOKEN", "")
    secret = os.getenv("TELEGRAM_SECRET", "")
    public_url = os.getenv("PUBLIC_URL", "").rstrip("/")
    if not token or not secret or not public_url:
        raise SystemExit("Configura TELEGRAM_TOKEN, TELEGRAM_SECRET y PUBLIC_URL.")
    if not public_url.startswith("https://"):
        raise SystemExit("PUBLIC_URL debe ser una URL pública HTTPS.")

    response = httpx.post(
        f"https://api.telegram.org/bot{token}/setWebhook",
        json={"url": f"{public_url}/telegram", "secret_token": secret},
        timeout=20.0,
    )
    print(response.text)
    response.raise_for_status()


if __name__ == "__main__":
    main()
