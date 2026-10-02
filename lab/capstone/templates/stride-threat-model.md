# Threat model: <system name>

## 1. Scope and data flow
Diagram (Mermaid or draw.io): actors, trust boundaries, data stores, flows. Number every flow.

## 2. Assets
| Asset | Why it matters | Classification (DPDP personal data?) |
|---|---|---|

## 3. STRIDE per element
| # | Element / flow | S | T | R | I | D | E | Threat description | Existing control | Gap | Mitigation | Owner |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Ingress -> API | x | | | | x | | Spoofed client, L7 flood | Istio JWT, rate limit | No WAF | ... | |
| 2 | CI -> registry | | x | | | | | Poisoned image | cosign sign | Not enforced in prod | policy-controller | |
| 3 | Copilot <- logs | | x | | x | | x | Prompt injection via log lines | Spotlighting | No output policy | tool allow-list | |

## 4. AI-specific (OWASP LLM Top 10 / MITRE ATLAS)
| LLM risk | Applies? | Scenario | Control |
|---|---|---|---|
| LLM01 Prompt injection | | | |
| LLM02 Sensitive information disclosure | | | |
| LLM03 Supply chain | | | |
| LLM06 Excessive agency | | | |

## 5. Residual risk + FAIR hand-off
Top 3 residual risks -> scenarios in `risk/fair_montecarlo.py`.
