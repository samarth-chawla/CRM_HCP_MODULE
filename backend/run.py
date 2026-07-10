"""Run the FastAPI backend.

Usage:
    cd backend
    pip install -r requirements.txt
    cp .env.example .env   # add your GROQ_API_KEY
    python run.py
"""
from app.main import app
import uvicorn

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
