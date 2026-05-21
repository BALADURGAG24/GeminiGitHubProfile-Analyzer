"""
MCP Server for GitHub Dev Card Generator
Tools: scrape_github, analyze_profile, generate_card_html, save_card
"""

import os
import json
import httpx
from pathlib import Path
from mcp.server.fastmcp import FastMCP

# Initialize FastMCP server
mcp = FastMCP("github-card-generator")

STATIC_DIR = Path(__file__).parent / "static" / "cards"
STATIC_DIR.mkdir(parents=True, exist_ok=True)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"

THEME_STYLES = {
    "hacker": {
        "bg": "#0e0c09",
        "card_bg": "#161210",
        "accent": "#c4622d",
        "text": "#d4cfc8",
        "badge_bg": "#2a1a10",
        "badge_text": "#e8845a",
        "border": "#c4622d",
        "font": "'DM Mono', 'Courier New', monospace",
        "repo_bg": "#110f0c",
    },
    "builder": {
        "bg": "#f5f0e8",
        "card_bg": "#fffdf8",
        "accent": "#c4622d",
        "text": "#1a1610",
        "badge_bg": "#f5e6d8",
        "badge_text": "#8f3d14",
        "border": "#d6cdb8",
        "font": "'DM Sans', 'Segoe UI', sans-serif",
        "repo_bg": "#f0ebe0",
    },
    "researcher": {
        "bg": "#13100d",
        "card_bg": "#1c1713",
        "accent": "#e8845a",
        "text": "#d8d0c4",
        "badge_bg": "#2a1f14",
        "badge_text": "#e8845a",
        "border": "#8f3d14",
        "font": "'Playfair Display', 'Georgia', serif",
        "repo_bg": "#17120e",
    },
    "designer": {
        "bg": "#fdf6ee",
        "card_bg": "#fffdf8",
        "accent": "#8f3d14",
        "text": "#2a1a0e",
        "badge_bg": "#faebd7",
        "badge_text": "#c4622d",
        "border": "#d4a882",
        "font": "'DM Sans', 'Trebuchet MS', sans-serif",
        "repo_bg": "#f5ede0",
    },
    "open-source-hero": {
        "bg": "#0d0b08",
        "card_bg": "#171410",
        "accent": "#d4922a",
        "text": "#e0d8cc",
        "badge_bg": "#281e0a",
        "badge_text": "#d4922a",
        "border": "#8a5e14",
        "font": "'DM Mono', 'Verdana', sans-serif",
        "repo_bg": "#110f0a",
    },
}


@mcp.tool()
async def scrape_github(username: str) -> dict:
    """
    Scrape public GitHub profile data for a given username.
    Returns name, bio, location, public_repos, followers, top repos, and language breakdown.
    """
    async with httpx.AsyncClient(timeout=15.0) as client:
        headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
        github_token = os.getenv("GITHUB_TOKEN", "")
        if github_token:
            headers["Authorization"] = f"Bearer {github_token}"

        # Fetch user profile
        user_resp = await client.get(f"https://api.github.com/users/{username}", headers=headers)
        if user_resp.status_code == 404:
            return {"error": f"GitHub user '{username}' not found."}
        if user_resp.status_code != 200:
            return {"error": f"GitHub API error: {user_resp.status_code}"}

        user = user_resp.json()

        # Fetch repos sorted by stars
        repos_resp = await client.get(
            f"https://api.github.com/users/{username}/repos",
            headers=headers,
            params={"sort": "stars", "direction": "desc", "per_page": 30},
        )
        repos = repos_resp.json() if repos_resp.status_code == 200 else []

        # Build top 6 repos
        top_repos = []
        lang_counts: dict[str, int] = {}
        for repo in repos:
            if repo.get("fork"):
                continue
            lang = repo.get("language") or "Unknown"
            lang_counts[lang] = lang_counts.get(lang, 0) + (repo.get("stargazers_count") or 0) + 1
            if len(top_repos) < 6:
                top_repos.append(
                    {
                        "name": repo.get("name", ""),
                        "stars": repo.get("stargazers_count", 0),
                        "language": lang,
                        "description": repo.get("description") or "",
                        "url": repo.get("html_url", ""),
                    }
                )

        # Sort languages by count
        sorted_langs = sorted(lang_counts.items(), key=lambda x: x[1], reverse=True)
        most_used_languages = [lang for lang, _ in sorted_langs[:6] if lang != "Unknown"]

        return {
            "username": username,
            "name": user.get("name") or username,
            "bio": user.get("bio") or "",
            "location": user.get("location") or "",
            "avatar_url": user.get("avatar_url", ""),
            "profile_url": user.get("html_url", f"https://github.com/{username}"),
            "public_repos": user.get("public_repos", 0),
            "followers": user.get("followers", 0),
            "following": user.get("following", 0),
            "top_repos": top_repos,
            "most_used_languages": most_used_languages,
            "company": user.get("company") or "",
            "blog": user.get("blog") or "",
            "created_at": user.get("created_at", ""),
        }


@mcp.tool()
async def analyze_profile(github_data: dict) -> dict:
    """
    Use Gemini 2.5 Flash to analyze a GitHub profile and produce a dev personality card.
    Returns developer_vibe, top_skills, fun_fact, and card_theme.
    """
    if not GEMINI_API_KEY:
        # Fallback analysis without AI
        langs = github_data.get("most_used_languages", ["Code"])
        return {
            "developer_vibe": f"A passionate developer who loves building with {', '.join(langs[:2]) if langs else 'code'}.",
            "top_skills": langs[:3] if langs else ["Programming", "Open Source", "Problem Solving"],
            "fun_fact": f"Has {github_data.get('public_repos', 0)} public repos and {github_data.get('followers', 0)} followers on GitHub.",
            "card_theme": "builder",
        }

    prompt = f"""
You are a witty, insightful developer profile analyst. Analyze this GitHub profile data and respond ONLY with a valid JSON object (no markdown, no explanation):

Profile data:
{json.dumps(github_data, indent=2)}

Respond with exactly this JSON structure:
{{
  "developer_vibe": "A single punchy sentence capturing this developer's personality and style (max 15 words, make it creative and fun)",
  "top_skills": ["skill1", "skill2", "skill3"],
  "fun_fact": "One clever, specific observation inferred from their repos or stats (make it interesting, not generic)",
  "card_theme": "one of: hacker, builder, researcher, designer, open-source-hero"
}}

card_theme guide:
- hacker: systems/security/low-level/kernel work
- builder: full-stack/web/apps/products
- researcher: ML/AI/data science/academic
- designer: UI/UX/creative/frontend-heavy
- open-source-hero: massive OSS contributions/many repos/popular projects
"""

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{GEMINI_URL}?key={GEMINI_API_KEY}",
            json={"contents": [{"parts": [{"text": prompt}]}]},
        )
        if resp.status_code != 200:
            # Fallback
            langs = github_data.get("most_used_languages", ["Code"])
            return {
                "developer_vibe": f"A dedicated developer crafting solutions with {', '.join(langs[:2]) if langs else 'passion'}.",
                "top_skills": langs[:3] if langs else ["Programming", "Open Source", "Collaboration"],
                "fun_fact": f"Maintains {github_data.get('public_repos', 0)} repos with {github_data.get('followers', 0)} followers.",
                "card_theme": "builder",
            }

        data = resp.json()
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        # Strip markdown fences if present
        text = text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        text = text.strip()
        return json.loads(text)


@mcp.tool()
async def generate_card_html(username: str, github_data: dict, analysis: dict) -> str:
    """
    Generate a beautiful, self-contained HTML dev card from GitHub data and AI analysis.
    Returns an HTML string ready to save or display.
    """
    theme_key = analysis.get("card_theme", "builder")
    theme = THEME_STYLES.get(theme_key, THEME_STYLES["builder"])

    name = github_data.get("name", username)
    bio = github_data.get("bio", "")
    location = github_data.get("location", "")
    avatar_url = github_data.get("avatar_url", "")
    public_repos = github_data.get("public_repos", 0)
    followers = github_data.get("followers", 0)
    following = github_data.get("following", 0)
    profile_url = github_data.get("profile_url", f"https://github.com/{username}")
    top_repos = github_data.get("top_repos", [])[:3]
    languages = github_data.get("most_used_languages", [])[:5]

    vibe = analysis.get("developer_vibe", "")
    top_skills = analysis.get("top_skills", [])
    fun_fact = analysis.get("fun_fact", "")

    # Build badges
    skill_badges = "".join(
        f'<span class="badge">{skill}</span>' for skill in top_skills
    )

    # Build language tags
    lang_tags = "".join(
        f'<span class="lang-tag">{lang}</span>' for lang in languages
    )

    # Build repo cards
    repo_cards_html = ""
    for repo in top_repos:
        stars = repo.get("stars", 0)
        star_display = f"★ {stars}" if stars > 0 else "★ 0"
        lang = repo.get("language", "")
        desc = repo.get("description", "") or "No description"
        if len(desc) > 60:
            desc = desc[:57] + "..."
        repo_cards_html += f"""
        <a class="repo-card" href="{repo.get('url', '#')}" target="_blank">
            <div class="repo-header">
                <span class="repo-name">▸ {repo.get('name', '')}</span>
                <span class="repo-stars">{star_display}</span>
            </div>
            <p class="repo-desc">{desc}</p>
            {f'<span class="repo-lang">{lang}</span>' if lang else ''}
        </a>"""

    # Theme label
    theme_labels = {
        "hacker": "HACKER",
        "builder": "BUILDER",
        "researcher": "RESEARCHER",
        "designer": "DESIGNER",
        "open-source-hero": "OSS HERO",
    }
    theme_label = theme_labels.get(theme_key, "DEVELOPER")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{name} — Dev Card</title>
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,700;0,900;1,700&family=DM+Mono:wght@400;500&family=DM+Sans:wght@400;500;600&display=swap" rel="stylesheet">
<style>
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

  body {{
    background: {theme['bg']};
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 24px;
    font-family: {theme['font']};
  }}

  .card {{
    background: {theme['card_bg']};
    border: 1.5px solid {theme['border']};
    border-radius: 4px;
    width: 100%;
    max-width: 480px;
    padding: 28px 26px;
    box-shadow: 6px 6px 0 {theme['border']}55;
    animation: revealUp 0.5s cubic-bezier(0.16, 1, 0.3, 1);
    position: relative;
    overflow: hidden;
  }}

  .card::before {{
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    background: {theme['accent']};
  }}

  @keyframes revealUp {{
    from {{ opacity: 0; transform: translateY(18px); }}
    to {{ opacity: 1; transform: translateY(0); }}
  }}

  .theme-label {{
    display: inline-flex;
    align-items: center;
    gap: 7px;
    font-family: 'DM Mono', monospace;
    font-size: 9px;
    font-weight: 500;
    letter-spacing: 0.18em;
    color: {theme['accent']};
    background: {theme['badge_bg']};
    border: 1.5px solid {theme['accent']};
    border-radius: 2px;
    padding: 4px 10px;
    margin-bottom: 20px;
    text-transform: uppercase;
  }}

  .theme-label::before {{
    content: '';
    width: 5px; height: 5px;
    background: {theme['accent']};
    border-radius: 50%;
  }}

  .profile-row {{
    display: flex;
    align-items: flex-start;
    gap: 16px;
    margin-bottom: 20px;
  }}

  .avatar {{
    width: 68px;
    height: 68px;
    border-radius: 3px;
    border: 1.5px solid {theme['border']};
    flex-shrink: 0;
    object-fit: cover;
  }}

  .profile-info {{ flex: 1; min-width: 0; }}

  .name {{
    font-family: 'Playfair Display', serif;
    font-size: 22px;
    font-weight: 900;
    color: {theme['accent']};
    line-height: 1.15;
    margin-bottom: 3px;
    letter-spacing: -0.02em;
  }}

  .username {{
    font-family: 'DM Mono', monospace;
    font-size: 11px;
    color: {theme['text']}88;
    margin-bottom: 5px;
  }}

  .location {{
    font-size: 11px;
    color: {theme['text']}77;
    font-family: 'DM Mono', monospace;
  }}

  .divider {{
    height: 1px;
    background: {theme['border']}44;
    margin: 16px 0;
    position: relative;
  }}

  .vibe {{
    font-size: 13px;
    color: {theme['text']};
    line-height: 1.65;
    border-left: 2.5px solid {theme['accent']};
    padding-left: 12px;
    margin-bottom: 16px;
    font-style: italic;
    opacity: 0.9;
  }}

  .skills-row {{
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-bottom: 18px;
  }}

  .badge {{
    font-family: 'DM Mono', monospace;
    font-size: 10px;
    font-weight: 500;
    background: {theme['badge_bg']};
    color: {theme['badge_text']};
    border: 1px solid {theme['accent']}44;
    border-radius: 2px;
    padding: 4px 10px;
    letter-spacing: 0.04em;
  }}

  .stats-row {{
    display: flex;
    gap: 0;
    margin-bottom: 18px;
    border: 1.5px solid {theme['border']}55;
    border-radius: 3px;
    overflow: hidden;
  }}

  .stat {{
    flex: 1;
    text-align: center;
    padding: 10px 4px;
    border-right: 1px solid {theme['border']}33;
  }}

  .stat:last-child {{ border-right: none; }}

  .stat-num {{
    font-family: 'DM Mono', monospace;
    font-size: 20px;
    font-weight: 500;
    color: {theme['accent']};
    display: block;
    line-height: 1.2;
  }}

  .stat-label {{
    font-family: 'DM Mono', monospace;
    font-size: 9px;
    color: {theme['text']}66;
    text-transform: uppercase;
    letter-spacing: 0.1em;
  }}

  .section-title {{
    font-family: 'DM Mono', monospace;
    font-size: 9px;
    font-weight: 500;
    letter-spacing: 0.16em;
    color: {theme['text']}55;
    text-transform: uppercase;
    margin-bottom: 8px;
  }}

  .repos {{ margin-bottom: 16px; }}

  .repo-card {{
    display: block;
    text-decoration: none;
    background: {theme['repo_bg']};
    border: 1px solid {theme['border']}33;
    border-radius: 3px;
    padding: 10px 12px;
    margin-bottom: 6px;
    transition: border-color 0.15s, transform 0.15s, box-shadow 0.15s;
  }}

  .repo-card:hover {{
    border-color: {theme['accent']};
    transform: translate(-2px, -2px);
    box-shadow: 2px 2px 0 {theme['accent']}44;
  }}

  .repo-header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 4px;
  }}

  .repo-name {{
    font-family: 'DM Mono', monospace;
    font-size: 11px;
    font-weight: 500;
    color: {theme['accent']};
  }}

  .repo-stars {{
    font-family: 'DM Mono', monospace;
    font-size: 10px;
    color: {theme['text']}77;
  }}

  .repo-desc {{
    font-size: 11px;
    color: {theme['text']}77;
    line-height: 1.45;
    margin-bottom: 5px;
  }}

  .repo-lang {{
    font-family: 'DM Mono', monospace;
    font-size: 9px;
    background: {theme['badge_bg']};
    color: {theme['badge_text']};
    padding: 2px 7px;
    border-radius: 2px;
    border: 1px solid {theme['accent']}33;
  }}

  .langs-row {{
    display: flex;
    flex-wrap: wrap;
    gap: 5px;
    margin-bottom: 16px;
  }}

  .lang-tag {{
    font-family: 'DM Mono', monospace;
    font-size: 10px;
    background: {theme['repo_bg']};
    color: {theme['text']}88;
    border: 1px solid {theme['border']}44;
    padding: 3px 9px;
    border-radius: 2px;
  }}

  .fun-fact {{
    font-size: 11px;
    color: {theme['text']}88;
    background: {theme['repo_bg']};
    border-radius: 3px;
    padding: 10px 13px;
    line-height: 1.55;
    margin-bottom: 18px;
    border-left: 2.5px solid {theme['accent']}77;
    font-family: 'DM Sans', sans-serif;
  }}

  .footer {{
    text-align: center;
    border-top: 1px solid {theme['border']}33;
    padding-top: 14px;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }}

  .gh-link {{
    font-family: 'DM Mono', monospace;
    font-size: 11px;
    color: {theme['accent']};
    text-decoration: none;
    border-bottom: 1px solid {theme['accent']}44;
    padding-bottom: 1px;
    transition: border-color 0.15s;
  }}

  .gh-link:hover {{ border-color: {theme['accent']}; }}

  .watermark {{
    font-family: 'DM Mono', monospace;
    font-size: 9px;
    color: {theme['text']}33;
    letter-spacing: 0.08em;
  }}
</style>
</head>
<body>
<div class="card">
  <div class="theme-label">{theme_label}</div>

  <div class="profile-row">
    <img class="avatar" src="{avatar_url}" alt="{name}" onerror="this.src='https://github.com/identicons/{username}.png'">
    <div class="profile-info">
      <div class="name">{name}</div>
      <div class="username">@{username}</div>
      {f'<div class="location">◎ {location}</div>' if location else ''}
    </div>
  </div>

  <div class="divider"></div>

  {f'<div class="vibe">"{vibe}"</div>' if vibe else ''}

  <div class="skills-row">
    {skill_badges}
  </div>

  <div class="stats-row">
    <div class="stat">
      <span class="stat-num">{public_repos}</span>
      <span class="stat-label">Repos</span>
    </div>
    <div class="stat">
      <span class="stat-num">{followers}</span>
      <span class="stat-label">Followers</span>
    </div>
    <div class="stat">
      <span class="stat-num">{following}</span>
      <span class="stat-label">Following</span>
    </div>
  </div>

  {f'<div class="repos"><div class="section-title">Top Repos</div>{repo_cards_html}</div>' if repo_cards_html else ''}

  {f'<div><div class="section-title">Languages</div><div class="langs-row">{lang_tags}</div></div>' if lang_tags else ''}

  {f'<div class="fun-fact">{fun_fact}</div>' if fun_fact else ''}

  <div class="footer">
    <a class="gh-link" href="{profile_url}" target="_blank">github.com/{username} →</a>
    <span class="watermark">DevCard Generator</span>
  </div>
</div>
</body>
</html>"""

    return html


@mcp.tool()
async def save_card(username: str, html: str) -> str:
    """
    Save the generated HTML card to disk and return the URL path.
    """
    filename = STATIC_DIR / f"{username}.html"
    filename.write_text(html, encoding="utf-8")
    return f"/card/{username}"


if __name__ == "__main__":
    mcp.run(transport="stdio")