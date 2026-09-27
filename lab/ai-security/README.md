# AI / LLM & agentic security sandbox (weeks 59-66)

Safety: test only the local model you run here. The `lab` network is `internal`, the agent uses mock tools,
and no credentials exist in the sandbox.

```bash
docker compose --profile pull run --rm puller            # one-time model download (egress allowed)
docker compose up -d ollama                              # model server, no internet
docker compose --profile tools build scanner             # once, needs internet
docker compose --profile tools run --rm scanner bash     # offline from here
  ./garak-ollama.sh                                      # week 61
  python mock_agent.py ; python mock_agent.py --guard    # week 62: compare attack success rate
  modelscan -p /path/to/model.pkl                        # week 63 (try a pickle you create with an os.system payload that only echoes)
```

| Week | Deliverable | Where |
|---|---|---|
| 59 | LLM threat model (OWASP LLM Top 10 + MITRE ATLAS mapping) | `../capstone/templates/stride-threat-model.md` style |
| 60 | PyRIT scan report | PyRIT orchestrator against `ollama` (OpenAI-compatible endpoint `http://ollama:11434/v1`) |
| 61 | Garak report + remediation notes | `reports/` |
| 62 | MCP / agent injection PoC + mitigation checklist | `mock_agent.py` |
| 63 | ModelScan CI job | add a step to `../cicd/.github/workflows/ci.yml` |
| 64 | OPA policy pack for model deployment gating | `../security/gatekeeper-policies.yaml` pattern (e.g. require `model-scan: passed` label) |
| 65 | Governance crosswalk (NIST AI RMF / ISO 42001 / EU AI Act / DPDP) | spreadsheet |
| 66 | Sigma rules + portfolio index | Sigma YAML in your portfolio repo |
