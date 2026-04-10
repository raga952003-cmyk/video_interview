"""Local development server."""

from pathlib import Path

from dotenv import load_dotenv

_root = Path(__file__).resolve().parent
load_dotenv(_root / ".env")
load_dotenv(_root.parent / ".env")

import os

from app import create_app

app = create_app()

if __name__ == "__main__":
    # Port 5000 is often taken on Windows (e.g. AirPlay / system services). Default 5050.
    port = int(os.environ.get("PORT", "5050"))
    app.run(host="0.0.0.0", port=port, debug=True)
