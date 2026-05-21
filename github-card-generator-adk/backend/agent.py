"""
ADK Agent: github_card_agent
Orchestrates the 4 MCP tools to generate dev cards from GitHub profiles.
"""

import os
import sys
from pathlib import Path

# Try to import google-adk; fall back gracefully if not installed
try:
    from google.adk.agents import Agent
    from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StdioServerParameters

    MCP_SERVER_PATH = str(Path(__file__).parent / "mcp_server.py")
    PYTHON_EXE = sys.executable

    github_card_agent = Agent(
        name="github_card_agent",
        model="gemini-2.5-flash",
        description="GitHub profile analyst and dev card generator",
        instruction="""You are a GitHub profile analyst and dev card generator.

When a user gives you a GitHub username, you ALWAYS follow this EXACT sequence — never skip any step:

1. Call `scrape_github` with the provided username to fetch their GitHub profile data.
2. Call `analyze_profile` with the FULL result from step 1 to get personality analysis.
3. Call `generate_card_html` with:
   - username (string)
   - github_data (full dict from step 1)
   - analysis (full dict from step 2)
4. Call `save_card` with the username and the HTML string from step 3.

After completing all steps, respond enthusiastically with:
- The card URL returned by save_card
- A brief, exciting summary of the developer's vibe and top skills

If the profile is private or doesn't exist (scrape_github returns an error key), say so clearly and stop.
Be warm, enthusiastic, and celebrate developers' work!""",
        tools=[
            MCPToolset(
                connection_params=StdioServerParameters(
                    command=PYTHON_EXE,
                    args=[MCP_SERVER_PATH],
                    env={
                        "GEMINI_API_KEY": os.getenv("GEMINI_API_KEY", ""),
                        "GITHUB_TOKEN": os.getenv("GITHUB_TOKEN", ""),
                    },
                )
            )
        ],
    )

    ADK_AVAILABLE = True

except ImportError:
    # ADK not installed — define a stub so main.py can detect this
    github_card_agent = None
    ADK_AVAILABLE = False
