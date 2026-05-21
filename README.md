# 🃏 GitHub Dev Card Generator

Generate beautiful, AI-powered developer cards from any public GitHub profile.  
**Stack:** FastAPI · Google ADK · Gemini 2.5 Flash · FastMCP · React/HTML Frontend · Cloud Run

---

## ✨ Features

- 🔍 **GitHub scraper** — fetches profile, repos, languages via GitHub REST API
- 🧠 **AI analysis** — Gemini 2.5 Flash generates a developer vibe, top skills, and fun facts
- 🎨 **5 card themes** — hacker, builder, researcher, designer, open-source-hero
- 💾 **Persistent cards** — saved HTML cards with shareable URLs
- 🤖 **ADK agent** — full orchestration via Google Agent Development Kit (optional)
- ☁️ **Cloud Run ready** — one-command deployment

---

## 🚀 Quick Start (Local)

### 1. Prerequisites

- Python 3.12+
- A Gemini API key → [Get one free](https://aistudio.google.com/app/apikey)
- (Optional) GitHub token for higher rate limits

### 2. Set up environment

```bash
cd github-card-generator
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY
```

### 3. Install dependencies & run backend

```bash
cd backend

# Option A: pip
pip install -r requirements.txt
uvicorn main:app --reload --port 8080

# Option B: uv
uv venv && .venv/Scripts/activate   # Windows
# or: source .venv/bin/activate     # Mac/Linux
uv pip install -r requirements.txt
uvicorn main:app --reload --port 8080
```

### 4. Open the frontend

Just open `frontend/index.html` in your browser — or serve it:

```bash
cd frontend
python -m http.server 3000
# Visit http://localhost:3000
```

The frontend auto-connects to `http://localhost:8080`.

---

## 🐳 Docker Compose (recommended)

```bash
# Copy and fill in your keys
cp .env.example .env

# Start both services
docker-compose up --build

# Frontend: http://localhost:3000
# Backend:  http://localhost:8080
# API docs: http://localhost:8080/docs
```

---

## 🌐 API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/generate` | Generate a dev card `{"username": "torvalds"}` |
| `GET`  | `/card/{username}` | Serve a saved card as HTML |
| `GET`  | `/cards` | List all generated cards |
| `GET`  | `/health` | Health check |
| `GET`  | `/docs` | OpenAPI / Swagger UI |

### Example

```bash
curl -X POST http://localhost:8080/generate \
  -H "Content-Type: application/json" \
  -d '{"username": "torvalds"}'
```

---

## ☁️ Deploy to Google Cloud Run

```bash
chmod +x deploy.sh
./deploy.sh YOUR_GCP_PROJECT_ID YOUR_GEMINI_API_KEY
```

Or set env vars first:

```bash
export GOOGLE_CLOUD_PROJECT=my-project
export GEMINI_API_KEY=AIza...
./deploy.sh
```

---

## 🧠 Architecture

```
User
 │
 ▼
frontend/index.html
 │  POST /generate
 ▼
backend/main.py  (FastAPI)
 │
 ├── Direct mode: calls MCP tools directly
 │    └── mcp_server.py
 │         ├── scrape_github()    → GitHub REST API
 │         ├── analyze_profile()  → Gemini 2.5 Flash
 │         ├── generate_card_html()
 │         └── save_card()
 │
 └── ADK mode (if google-adk installed):
      └── agent.py (github_card_agent)
           └── MCPToolset → mcp_server.py (stdio)
```

---

## 🎨 Card Themes

| Theme | Style | Triggered by |
|-------|-------|--------------|
| `hacker` | Dark, green terminal | Systems/security/kernel work |
| `builder` | Clean light/blue | Full-stack/web/product builders |
| `researcher` | Dark navy/red | ML/AI/data science/academic |
| `designer` | Light purple/pastel | UI/UX/creative/frontend |
| `open-source-hero` | Dark, amber/gold | Massive OSS contributions |

---

## 🔑 Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY` | ✅ Yes | Gemini API key for AI analysis |
| `GITHUB_TOKEN` | Optional | PAT for 5000 req/hr (vs 60) |
| `GOOGLE_CLOUD_PROJECT` | Cloud only | GCP project ID |
| `AGENT_ENGINE_ID` | Optional | Vertex AI memory bank ID |

---

## 🧩 Adding Google ADK (optional)

The backend works without ADK in **direct mode**. To enable full agent orchestration:

```bash
pip install google-adk google-genai
```

The app auto-detects ADK and switches to agent mode.

---

## 📁 Project Structure

```
github-card-generator/
├── backend/
│   ├── mcp_server.py      # 4 MCP tools (scrape, analyze, generate, save)
│   ├── agent.py           # ADK agent definition
│   ├── main.py            # FastAPI app (direct + ADK modes)
│   ├── deploy_memory.py   # Vertex AI memory bank setup
│   ├── requirements.txt
│   ├── Dockerfile
│   └── static/
│       └── cards/         # Generated HTML cards saved here
├── frontend/
│   ├── index.html         # Single-page UI
│   └── Dockerfile
├── docker-compose.yml
├── deploy.sh
├── .env.example
└── README.md
```
