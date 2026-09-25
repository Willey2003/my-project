from typing import Tuple

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
import os

app = FastAPI(title="GitHub Code Analyzer & DevOps Assistant")

class RepoRequest(BaseModel):
    repo_url: str

def extract_repo_info(url: str) -> Tuple[str, str]:
    """Extracts owner and repo name from a GitHub URL."""
    parts = url.rstrip('/').split('/')
    if len(parts) >= 2:
        return parts[-2], parts[-1]
    raise ValueError("Invalid GitHub URL")

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.get("/ready")
def readiness_check():
    # Simulate checking dependency readiness (e.g., database, external API)
    return {"status": "ready"}

@app.post("/analyze")
def analyze_repository(request: RepoRequest):
    try:
        owner, repo = extract_repo_info(request.repo_url)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid GitHub repository URL")

    # Fetch latest data from GitHub API
    api_url = f"https://api.github.com/repos/{owner}/{repo}"
    response = requests.get(api_url, headers={"Accept": "application/vnd.github.v3+json"}, timeout=10)
    
    if response.status_code != 200:
        raise HTTPException(status_code=404, detail="Repository not found or API limit reached")
    
    data = response.json()
    
    # DevOps Analysis Logic
    analysis = {
        "repository": f"{owner}/{repo}",
        "description": data.get("description", "No description"),
        "language": data.get("language", "Unknown"),
        "stars": data.get("stargazers_count", 0),
        "open_issues": data.get("open_issues_count", 0),
        "devops_recommendations": []
    }

    # Generate automated DevOps recommendations based on repo data
    if data.get("language") == "Python":
        analysis["devops_recommendations"].append("Consider adding a requirements.txt or pyproject.toml if missing.")
        analysis["devops_recommendations"].append("Recommended base image: python:3.11-slim")
    if data.get("open_issues_count", 0) > 50:
        analysis["devops_recommendations"].append("High open issue count. Consider implementing automated issue triaging with GitHub Actions.")

    # `has_actions` is not a field returned by the repo API; query the
    # workflows endpoint to actually determine whether CI is configured.
    if not _has_workflows(owner, repo):
        analysis["devops_recommendations"].append("No GitHub Actions detected. Consider adding a CI/CD pipeline for automated testing.")

    return analysis


def _has_workflows(owner: str, repo: str) -> bool:
    """Return True if the repository has at least one GitHub Actions workflow."""
    try:
        resp = requests.get(
            f"https://api.github.com/repos/{owner}/{repo}/actions/workflows",
            headers={"Accept": "application/vnd.github.v3+json"},
            timeout=10,
        )
        if resp.status_code == 200:
            return resp.json().get("total_count", 0) > 0
    except requests.RequestException:
        pass
    # On error or rate limit, assume workflows may exist to avoid a misleading
    # recommendation.
    return True

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
