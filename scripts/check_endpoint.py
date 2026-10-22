"""Inspect configured endpoint origins without emitting or persisting any secret value."""

import json
import os
from urllib.parse import urlsplit

names = ["BENCHLAB_MODEL_BASE_URL", "OPENAI_BASE_URL", "OLLAMA_HOST", "LITELLM_API_BASE"]
findings = []
for name in names:
    value = os.environ.get(name)
    if not value:
        continue
    parsed = urlsplit(value if "://" in value else "http://" + value)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
    ):
        findings.append({"variable": name, "status": "unsafe or credential-bearing URL withheld"})
        continue
    findings.append(
        {
            "variable": name,
            "endpoint": value,
            "status": "configured; authorization and model identity must be confirmed",
        }
    )

if not findings:
    findings.append(
        {
            "status": "BLOCKED — endpoint unavailable",
            "reason": "No explicit model endpoint environment configuration is present; local Ollama was checked separately and is not running. Cached 7B/14B weights were not loaded.",
        }
    )
print(json.dumps({"real_model_smoke": findings, "credentials_printed": False}, indent=2))
