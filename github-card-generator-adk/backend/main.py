"""
FastAPI backend for GitHub Dev Card Generator.
Supports two modes:
  1. ADK Agent mode (full Google ADK + Gemini orchestration)
  2. Direct mode (calls MCP tools directly via httpx — no ADK required)
"""

import os
import json
import asyncio
from pathlib import Path
from typing import Optional

# ── LOAD ENV VARIABLES ───────────────────────────────────────────────────────
from dotenv import load_dotenv

# Load backend/.env
ENV_PATH = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=ENV_PATH)

# Gemini SDK expects GOOGLE_API_KEY
if os.getenv("GEMINI_API_KEY") and not os.getenv("GOOGLE_API_KEY"):
    os.environ["GOOGLE_API_KEY"] = os.getenv("GEMINI_API_KEY")

print("GOOGLE_API_KEY Loaded:", bool(os.getenv("GOOGLE_API_KEY")))
print("GITHUB_TOKEN Loaded:", bool(os.getenv("GITHUB_TOKEN")))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Import MCP tools directly (always available)
from mcp_server import scrape_github, analyze_profile, generate_card_html, save_card

# Try ADK imports
try:
    from agent import github_card_agent, ADK_AVAILABLE
except Exception as e:
    print("ADK import failed:", e)
    github_card_agent = None
    ADK_AVAILABLE = False

# ── FastAPI app ──────────────────────────────────────────────────────────────

app = FastAPI(title="GitHub Dev Card Generator", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = Path(__file__).parent / "static" / "cards"
STATIC_DIR.mkdir(parents=True, exist_ok=True)

app.mount(
    "/static",
    StaticFiles(directory=str(Path(__file__).parent / "static")),
    name="static",
)

# ── Request / Response models ────────────────────────────────────────────────

class GenerateRequest(BaseModel):
    username: str


class GenerateResponse(BaseModel):
    username: str
    card_url: str
    card_html: str
    analysis: dict
    github_data: dict
    mode: str  # "adk" or "direct"


# ── ADK session store (in-memory) ────────────────────────────────────────────

_sessions: dict[str, str] = {}  # username -> session_id


async def _run_adk_agent(username: str) -> GenerateResponse:
    """Run the full ADK agent pipeline."""

    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    from google.genai.types import Content, Part

    # Create ONE persistent session service
    global _sessions

    session_service = InMemorySessionService()

    runner = Runner(
        agent=github_card_agent,
        app_name="github_card_generator",
        session_service=session_service,
    )

    # Always create a NEW session to avoid "Session not found"
    session = await session_service.create_session(
        app_name="github_card_generator",
        user_id=username,
    )

    session_id = session.id
    _sessions[username] = session_id

    user_message = Content(
        role="user",
        parts=[Part(text=f"Generate a dev card for {username}")]
    )

    final_response = ""

    async for event in runner.run_async(
        user_id=username,
        session_id=session_id,
        new_message=user_message,
    ):
        if event.is_final_response() and event.content:
            for part in event.content.parts:
                if hasattr(part, "text") and part.text:
                    final_response += part.text

    # The card was saved by the agent; read it back
    card_path = STATIC_DIR / f"{username}.html"

    card_html = (
        card_path.read_text(encoding="utf-8")
        if card_path.exists()
        else ""
    )

    return GenerateResponse(
        username=username,
        card_url=f"/card/{username}",
        card_html=card_html,
        analysis={},
        github_data={},
        mode="adk",
    )


async def _run_direct(username: str) -> GenerateResponse:
    """Call MCP tool functions directly — no ADK required."""

    # Step 1: Scrape
    github_data = await scrape_github(username)

    if "error" in github_data:
        raise HTTPException(
            status_code=404,
            detail=github_data["error"]
        )

    # Step 2: Analyze
    analysis = await analyze_profile(github_data)

    # Step 3: Generate HTML
    card_html = await generate_card_html(
        username,
        github_data,
        analysis
    )

    # Step 4: Save
    card_url = await save_card(username, card_html)

    return GenerateResponse(
        username=username,
        card_url=card_url,
        card_html=card_html,
        analysis=analysis,
        github_data=github_data,
        mode="direct",
    )


# ── Endpoints ────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "adk_available": ADK_AVAILABLE,
        "google_api_key_loaded": bool(os.getenv("GOOGLE_API_KEY")),
        "github_token_loaded": bool(os.getenv("GITHUB_TOKEN")),
    }


@app.post("/generate", response_model=GenerateResponse)
async def generate(req: GenerateRequest):

    username = req.username.strip().lstrip("@")

    if not username:
        raise HTTPException(
            status_code=400,
            detail="Username is required."
        )

    # Try ADK mode first
    if (
        ADK_AVAILABLE
        and github_card_agent is not None
        and os.getenv("GOOGLE_API_KEY")
    ):
        try:
            print(f"Using ADK mode for: {username}")
            return await _run_adk_agent(username)

        except Exception as e:
            # Fall through to direct mode on ADK error
            print(f"ADK error, falling back to direct mode: {e}")

    # Direct mode fallback
    print(f"Using DIRECT mode for: {username}")

    return await _run_direct(username)


@app.get("/card/{username}", response_class=HTMLResponse)
async def serve_card(username: str):

    card_path = STATIC_DIR / f"{username}.html"

    if not card_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Card for '{username}' not found. Generate it first."
        )

    return HTMLResponse(
        content=card_path.read_text(encoding="utf-8")
    )


@app.get("/cards", response_class=JSONResponse)
async def list_cards():
    """List all generated cards."""

    cards = [p.stem for p in STATIC_DIR.glob("*.html")]

    return {
        "cards": sorted(cards),
        "count": len(cards),
    }


@app.get("/")
async def root():
    return {
        "message": "GitHub Dev Card Generator API",
        "docs": "/docs",
        "health": "/health",
    }


# ── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8080,
        reload=True,
    )