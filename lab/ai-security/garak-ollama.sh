#!/usr/bin/env bash
# Week 61: vulnerability scan of the LOCAL model only. Run inside the scanner container.
set -euo pipefail
MODEL=${MODEL:-llama3.2:1b}
mkdir -p reports
python -m garak --model_type ollama --model_name "$MODEL" \
  --probes promptinject,dan,encoding,leakreplay \
  --report_prefix "reports/garak-$(date +%F)"
echo "report: reports/ (the .html file is your portfolio artifact; add remediation notes)"
