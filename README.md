# GitHub Code Analyzer & DevOps Assistant

A small FastAPI service that inspects a public GitHub repository and returns
basic metadata plus automated DevOps recommendations.

## Endpoints

| Method | Path       | Description                                            |
|--------|------------|--------------------------------------------------------|
| GET    | `/health`  | Liveness check — returns `{"status": "healthy"}`.      |
| GET    | `/ready`   | Readiness check — returns `{"status": "ready"}`.       |
| POST   | `/analyze` | Analyze a repo. Body: `{"repo_url": "<github url>"}`.  |

### `POST /analyze`

Request:

```json
{ "repo_url": "https://github.com/octocat/Hello-World" }
```

Response (shape):

```json
{
  "repository": "octocat/Hello-World",
  "description": "...",
  "language": "Python",
  "stars": 123,
  "open_issues": 4,
  "devops_recommendations": ["..."]
}
```

Recommendations are generated from the repo's language, open-issue count, and
whether any GitHub Actions workflows are configured (checked live against the
Actions API).

## Running locally

```bash
pip install fastapi uvicorn requests
python app.py            # serves on 0.0.0.0:8080 (override with PORT)
```

Then:

```bash
curl localhost:8080/health
curl -X POST localhost:8080/analyze \
  -H "Content-Type: application/json" \
  -d '{"repo_url":"https://github.com/octocat/Hello-World"}'
```

## Tests

```bash
pip install fastapi httpx pytest
pytest
```

Tests cover the health/readiness endpoints, URL parsing, and input validation
without making network calls. CI runs them on every push via GitHub Actions.

## Configuration

| Variable | Default | Purpose                     |
|----------|---------|-----------------------------|
| `PORT`   | `8080`  | Port the service binds to.  |
