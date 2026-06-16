"""
Production entry point.

Run locally:
    python run.py

Run with Gunicorn (production):
    gunicorn --bind 0.0.0.0:8000 --workers 2 "run:app"
"""
from src.api.app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=app.config.get("DEBUG", False))
