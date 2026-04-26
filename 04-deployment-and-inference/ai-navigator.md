# AI Navigator — Local Inference

AI Navigator is Anaconda's desktop application for running open-source LLMs locally. It manages model downloads, quantization selection, and exposes an API server you can call from your code.

**When to use this:** Development and prototyping. No API key, no cloud bill, no network dependency. Models run on your machine using CPU + RAM + VRAM.

---

## Setup

### 1. Install AI Navigator

Download from [anaconda.com/products/ai-navigator](https://anaconda.com/products/ai-navigator). Available for Windows 11 and macOS 13+.

### 2. Download a model

Open AI Navigator → **Models** tab. For this demo, anything tagged **Desktop Deployable** (≤16GB RAM) works. Recommended starting points:

- **Llama 3.2 3B** — fast, fits in 8GB RAM, good for testing
- **Mistral 7B** — stronger reasoning, needs ~16GB RAM
- Filter by **Tool Calling** tag if you want structured function-call support

Select a quantization level — lower quantization = smaller file + faster but slightly lower quality. `Q4_K_M` is a good default balance.

### 3. Start the API server

Open AI Navigator → **API Server** tab:

1. Open the **Specify Model** dropdown and select your downloaded model
2. Leave **Server Address** as `127.0.0.1` (localhost) and **Server Port** as `8080`
3. Optionally set an **API Key** for the `Authorization: Bearer` header
4. Click **Start**

The server is running when you see "Server listening on 127.0.0.1:8080" in the logs.

### 4. Configure your environment

```bash
# AI Navigator runs on port 8080 by default
# Use /v1 suffix for OpenAI-compatible chat completions endpoint
export INFERENCE_BASE_URL="http://localhost:8080/v1"
export INFERENCE_API_KEY="your-key-if-set"  # or any string if no key configured
export INFERENCE_MODEL="any"                 # ignored — model is set in the UI
```

### 5. Verify

```bash
python inference_client.py
# Expected output:
#   status: ok
#   base_url: http://localhost:8080/v1
#   model: (loaded on server)
#   response: ready
#   latency_s: 0.8
```

---

## Important: endpoint format

AI Navigator's built-in server runs on **llama.cpp**. It has two endpoints:

| Endpoint | Format | Use |
|---|---|---|
| `http://localhost:8080/completion` | llama.cpp native | Direct curl, raw prompts |
| `http://localhost:8080/v1/chat/completions` | OpenAI-compatible | `openai` Python client |

**Always use `http://localhost:8080/v1` as your `base_url`** when using the `openai` client. The `/v1` prefix is required — without it, the client gets a 404.

---

## Limitations

- **Single user, single session.** AI Navigator is not designed for concurrent requests in production. The server has a fixed number of "slots" — one per concurrent request. For multi-agent workloads like the `foreach` in Module 03, requests queue rather than run in parallel.
- **GGUF format only.** Models must be in GGUF quantized format. These are not the same files as HuggingFace safetensors used by vLLM.
- **Windows and macOS only.** No Linux desktop support. For Linux production deployments, use vLLM.
- **No streaming by default** for the OpenAI-compatible endpoint.

---

## Troubleshooting

**Port 8080 already in use:**
Change the port in AI Navigator's API Server settings, then update `INFERENCE_BASE_URL` accordingly.

**Model won't load (Windows, exit code 3221225781):**
Install the [Microsoft Visual C++ Redistributable](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist).

**401 errors:**
Check that the API Key you set in AI Navigator matches `INFERENCE_API_KEY` exactly.

**Slow responses:**
Lower quantization (e.g. Q2_K) or use a smaller model. AI Navigator uses RAM + VRAM — check resource usage in the **Resource Consumption** tab.

---

## What this looks like in code

```python
from inference_client import get_client, INFERENCE_MODEL
from openai import OpenAI
import os

# Identical to vLLM and Anaconda Platform — only base_url differs
client = get_client()

response = client.chat.completions.create(
    model=INFERENCE_MODEL,   # empty string or "any" — AI Navigator ignores it
    messages=[
        {"role": "system", "content": "You are an astrophysics analysis agent."},
        {"role": "user",   "content": "Classify this transit signal: depth=1.01%, 78 anomalous points."},
    ],
    max_tokens=200,
    temperature=0.1,
)

print(response.choices[0].message.content)
```

---

## Further reading

- [AI Navigator API server docs](https://anaconda.com/docs/tools/ai-navigator/user-guide/api-server)
- [AI Navigator model browser](https://anaconda.com/docs/tools/ai-navigator/user-guide/models)
- [AI Navigator chatbot tutorial](https://anaconda.com/docs/tools/ai-navigator/tutorials/chatbot-tutorial)
