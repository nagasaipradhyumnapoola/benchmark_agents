"""A minimal real endpoint harness for controlled subprocess integration.

Not a full coding agent: it makes one chat request and prints observable final text.
Credentials are passed only through the explicit harness environment binding.
"""

import argparse
import json
import os
import sys
import urllib.request

parser = argparse.ArgumentParser()
parser.add_argument("--model", required=True)
args = parser.parse_args()
headers = {"Content-Type": "application/json"}
if os.environ.get("HARNESS_API_KEY"):
    headers["Authorization"] = "Bearer " + os.environ["HARNESS_API_KEY"]
base = os.environ["HARNESS_BASE_URL"].rstrip("/")
if not base.startswith(("http://", "https://")):
    raise SystemExit("An HTTP(S) endpoint is required")
request = urllib.request.Request(  # noqa: S310 - endpoint scheme explicitly validated above
    base + "/chat/completions",
    data=json.dumps(
        {
            "model": args.model,
            "messages": [{"role": "user", "content": sys.stdin.read()}],
            "max_tokens": 1024,
            "stream": False,
        }
    ).encode(),
    headers=headers,
    method="POST",
)
with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310 - explicitly validated configured HTTP(S) endpoint
    print(json.load(response)["choices"][0]["message"]["content"])
