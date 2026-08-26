import os
import logging
from datetime import datetime
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, HttpUrl
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="GitHub Code Analyzer & DevOps Assistant",
    description="Analyzes GitHub repositories and provides DevOps recommendations",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Rate limiting setup
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class RepoRequest(BaseModel):
    repo_url: str = Field(..., description="GitHub repository URL", example="https://github.com/owner/repo")
    
    @classmethod
    def validate_repo_url(cls, v):
        if not v or not isinstance(v, str):
            raise ValueError("Repository URL must be a non-empty string")
        if not v.startswith("https://github.com/"):
            raise ValueError("URL must be a valid GitHub URL (https://github.com/owner/repo)")
        parts = v.rstrip('/').split('/')
        if len(parts) != 5 or not parts[3] or not parts[4]:
            raise ValueError("Invalid GitHub URL format. Expected: https://github.com/owner/repo")
        return v

def extract_repo_info(url: str) -> tuple:
    """Extracts owner and repo name from a GitHub URL."""
    parts = url.rstrip('/').split('/')
    if len(parts) >= 5:
        return parts[-2], parts[-1]
    raise ValueError("Invalid GitHub URL format")


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests for monitoring and debugging."""
    start_time = datetime.now()
    logger.info(f"{request.method} {request.url.path} - Request from {request.client.host if request.client else 'unknown'}")
    
    response = await call_next(request)
    
    process_time = (datetime.now() - start_time).total_seconds()
    logger.info(f"{request.method} {request.url.path} - Completed in {process_time:.3f}s with status {response.status_code}")
    
    response.headers["X-Process-Time"] = str(process_time)
    return response


@app.get("/health")
async def health_check():
    """Health check endpoint for Kubernetes liveness probe."""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


@app.get("/ready")
async def readiness_check():
    """Readiness check endpoint for Kubernetes readiness probe.
    
    Simulates checking dependency readiness (e.g., database, external API).
    """
    # Check if GitHub API is accessible
    try:
        response = requests.get("https://api.github.com", timeout=5)
        github_available = response.status_code == 200
    except Exception:
        github_available = False
    
    status = "ready" if github_available else "degraded"
    return {
        "status": status,
        "github_api_available": github_available,
        "timestamp": datetime.utcnow().isoformat()
    }

@app.post("/analyze")
async def analyze_repository(request: RepoRequest):
    """Analyze a GitHub repository and provide DevOps recommendations."""
    logger.info(f"Analyzing repository: {request.repo_url}")
    
    try:
        owner, repo = extract_repo_info(request.repo_url)
    except ValueError as e:
        logger.warning(f"Invalid repository URL: {request.repo_url}")
        raise HTTPException(status_code=400, detail=str(e))

    # Fetch latest data from GitHub API with timeout and error handling
    api_url = f"https://api.github.com/repos/{owner}/{repo}"
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "GitHub-Code-Analyzer/2.0"
    }
    
    try:
        response = requests.get(api_url, headers=headers, timeout=10)
    except requests.exceptions.Timeout:
        logger.error(f"Timeout fetching repository data for {owner}/{repo}")
        raise HTTPException(status_code=504, detail="GitHub API request timed out")
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching repository data: {str(e)}")
        raise HTTPException(status_code=503, detail="Unable to reach GitHub API")
    
    if response.status_code == 404:
        logger.warning(f"Repository not found: {owner}/{repo}")
        raise HTTPException(status_code=404, detail="Repository not found")
    elif response.status_code == 403:
        logger.error("GitHub API rate limit exceeded")
        raise HTTPException(status_code=429, detail="GitHub API rate limit exceeded. Please try again later.")
    elif response.status_code != 200:
        logger.error(f"Unexpected GitHub API response: {response.status_code}")
        raise HTTPException(status_code=502, detail=f"GitHub API returned status code {response.status_code}")
    
    data = response.json()
    
    # Get additional repository details (topics, default branch info)
    topics_url = f"https://api.github.com/repos/{owner}/{repo}/topics"
    try:
        topics_response = requests.get(topics_url, headers={**headers, "Accept": "application/vnd.github.mercy-preview+json"}, timeout=5)
        topics = topics_response.json().get("names", []) if topics_response.status_code == 200 else []
    except Exception:
        topics = []
    
    # DevOps Analysis Logic
    analysis = {
        "repository": f"{owner}/{repo}",
        "url": data.get("html_url", ""),
        "description": data.get("description", "No description"),
        "language": data.get("language", "Unknown"),
        "topics": topics,
        "stars": data.get("stargazers_count", 0),
        "forks": data.get("forks_count", 0),
        "watchers": data.get("watchers_count", 0),
        "open_issues": data.get("open_issues_count", 0),
        "has_wiki": data.get("has_wiki", False),
        "has_pages": data.get("has_pages", False),
        "license": data.get("license", {}).get("name", "Unknown") if data.get("license") else "Unknown",
        "created_at": data.get("created_at", ""),
        "updated_at": data.get("updated_at", ""),
        "devops_recommendations": [],
        "security_alerts": []
    }

    # Generate automated DevOps recommendations based on repo data
    language = data.get("language", "")
    
    if language == "Python":
        analysis["devops_recommendations"].append({
            "category": "Dependency Management",
            "priority": "high",
            "message": "Ensure you have a requirements.txt or pyproject.toml for dependency management."
        })
        analysis["devops_recommendations"].append({
            "category": "Containerization",
            "priority": "medium",
            "message": "Recommended base image: python:3.11-slim for Docker containers."
        })
        analysis["devops_recommendations"].append({
            "category": "Testing",
            "priority": "medium",
            "message": "Consider adding pytest or unittest for automated testing."
        })
    elif language == "JavaScript" or language == "TypeScript":
        analysis["devops_recommendations"].append({
            "category": "Dependency Management",
            "priority": "high",
            "message": "Ensure you have package.json with locked dependencies (package-lock.json or yarn.lock)."
        })
        analysis["devops_recommendations"].append({
            "category": "Containerization",
            "priority": "medium",
            "message": "Recommended base image: node:20-alpine for Docker containers."
        })
    elif language == "Go":
        analysis["devops_recommendations"].append({
            "category": "Build",
            "priority": "medium",
            "message": "Ensure go.mod is present for module management."
        })
        analysis["devops_recommendations"].append({
            "category": "Containerization",
            "priority": "high",
            "message": "Consider using multi-stage Docker builds with golang:alpine and alpine/scratch for production."
        })
    elif language == "Java":
        analysis["devops_recommendations"].append({
            "category": "Build",
            "priority": "high",
            "message": "Ensure Maven pom.xml or Gradle build.gradle is properly configured."
        })
        analysis["devops_recommendations"].append({
            "category": "Containerization",
            "priority": "medium",
            "message": "Recommended base image: eclipse-temurin:17-jre-alpine for runtime."
        })

    # Check for CI/CD
    workflows_url = f"https://api.github.com/repos/{owner}/{repo}/actions/workflows"
    try:
        workflows_response = requests.get(workflows_url, headers=headers, timeout=5)
        workflows = workflows_response.json().get("workflows", []) if workflows_response.status_code == 200 else []
        has_actions = len(workflows) > 0
        analysis["github_actions_workflows"] = len(workflows)
    except Exception:
        has_actions = False
        analysis["github_actions_workflows"] = 0
    
    if not has_actions:
        analysis["devops_recommendations"].append({
            "category": "CI/CD",
            "priority": "high",
            "message": "No GitHub Actions detected. Consider adding a CI/CD pipeline for automated testing and deployment."
        })
    else:
        analysis["devops_recommendations"].append({
            "category": "CI/CD",
            "priority": "low",
            "message": f"Found {len(workflows)} GitHub Actions workflow(s). Ensure they cover linting, testing, and security scanning."
        })

    # Check for high open issue count
    open_issues = data.get("open_issues_count", 0)
    if open_issues > 50:
        analysis["devops_recommendations"].append({
            "category": "Issue Management",
            "priority": "medium",
            "message": f"High open issue count ({open_issues}). Consider implementing automated issue triaging with GitHub Actions or bots."
        })
    
    # Check for license
    if analysis["license"] == "Unknown":
        analysis["security_alerts"].append({
            "severity": "warning",
            "message": "No license detected. Consider adding an open source license to clarify usage rights."
        })
    
    # Check for security best practices
    readme_url = f"https://raw.githubusercontent.com/{owner}/{repo}/main/README.md"
    try:
        readme_response = requests.get(readme_url, timeout=5)
        has_readme = readme_response.status_code == 200
    except Exception:
        # Try master branch
        readme_url = f"https://raw.githubusercontent.com/{owner}/{repo}/master/README.md"
        try:
            readme_response = requests.get(readme_url, timeout=5)
            has_readme = readme_response.status_code == 200
        except Exception:
            has_readme = False
    
    if not has_readme:
        analysis["security_alerts"].append({
            "severity": "info",
            "message": "No README.md found. Consider adding documentation for better project maintainability."
        })
    
    # Add contribution guidelines check
    contributing_url = f"https://raw.githubusercontent.com/{owner}/{repo}/main/.github/CONTRIBUTING.md"
    try:
        contrib_response = requests.get(contributing_url, timeout=5)
        has_contributing = contrib_response.status_code == 200
    except Exception:
        has_contributing = False
    
    if not has_contributing and open_issues > 10:
        analysis["devops_recommendations"].append({
            "category": "Documentation",
            "priority": "low",
            "message": "Consider adding CONTRIBUTING.md to help community contributors."
        })

    # Sort recommendations by priority
    priority_order = {"high": 0, "medium": 1, "low": 2}
    analysis["devops_recommendations"].sort(key=lambda x: priority_order.get(x.get("priority", "low"), 3))
    
    logger.info(f"Analysis complete for {owner}/{repo}: {len(analysis['devops_recommendations'])} recommendations generated")
    
    return analysis


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Welcome to GitHub Code Analyzer & DevOps Assistant",
        "version": "2.0.0",
        "endpoints": {
            "health": "/health",
            "ready": "/ready",
            "analyze": "/analyze (POST)",
            "docs": "/docs"
        }
    }


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors."""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "type": type(exc).__name__}
    )

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
