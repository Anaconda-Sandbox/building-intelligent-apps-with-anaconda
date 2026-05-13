# Anaconda Platform — Model Servers

Anaconda Platform (self-hosted, v7.0.0+) includes a Model Catalog and Model Servers — a governed, managed inference layer for organisations. Model servers expose OpenAI-compatible endpoints that your agents can call directly.

**When to use this:** Enterprise deployments where model access needs to be governed, audited, and managed by an administrator. Models are curated, benchmarked, and security-scanned by Anaconda before they appear in the catalog.

> Anaconda Platform 7.0.0 is available through a limited early access programme. Contact your Anaconda Technical Account Manager if you're interested.

---

## How it works

```
Administrator                          Developer
─────────────────────────────          ─────────────────────────────────────
1. Browse Model Catalog                4. Get server address + API key
2. Apply Model Governance rules        5. Set env vars
3. Create a Model Server               6. Call endpoint with openai client
   (loads model, exposes endpoint)        (identical to vLLM or AI Navigator)
```

---

## Step 1 — Browse the Model Catalog

Log in to Anaconda Platform → **Model Catalog** from the left navigation.

Three views are available:

**Tile view** — grid of models with name, publisher, type, disk space, and RAM per quantization.

**Table view** — same information in a scannable table.

**Chart view** — plot any model against benchmark scores (HellaSwag, WinoGrande, TruthfulQA) vs. resource requirements (RAM or model size). Use this to find the best balance of performance and hardware cost for your use case.

Filter models by:
- Publisher, Purpose, Language, License
- Quantization method, File Size, RAM
- Benchmark score thresholds (useful for governance — "only show models with TruthfulQA ≥ 70")
- **Desktop Deployable** tag — models that run on ≤16GB RAM

**Trusted Publisher badge** — models from publishers verified by Anaconda for legal standing, security practices, documentation standards, and community presence.

---

## Step 2 — Review model details

Select any model to see four tabs:

**Overview** — description, publisher, intended use cases, license terms, links, and a downloadable **AIBOM** (AI Bill of Materials).

The AIBOM is a `.json` file in CycloneDX format containing:
- Model metadata: publisher, version, architecture, license
- File variants: quantization options with file size and RAM requirements
- Cryptographic hashes: SHA-256 checksums per file — verify your download hasn't been tampered with
- Performance metrics: benchmark scores per quantization
- Ethical considerations: documented limitations, bias risks, recommended mitigations
- Software dependencies: libraries required to run the model

```bash
# Verify a downloaded model file against the AIBOM hash
sha256sum your-model-file.gguf
# Compare against the SHA-256 in the downloaded AIBOM
```

**Responsible AI** (requires Gray Swan subscription) — OWASP LLM Top 10 resistance, MITRE ATLAS adversarial robustness, policy compliance, industry fit, and harmful content scores. Each model gets a Robustness Score indicating overall safety posture.

**Files** — side-by-side comparison of quantization levels: file size, RAM required, publication date, SHA-256 hashes.

**Evaluations** — benchmark scores per quantization, normalised 0–100 relative to all models in the catalog.

---

## Step 3 — Model Governance (admin)

Administrators control which models are available to which teams.

**Organisational restrictions** block models org-wide. Filter by:
- Model name, publisher, purpose, language, license
- Quantization, file size, RAM requirements
- HellaSwag, WinoGrande, TruthfulQA score thresholds

Example policy: "Block any model with TruthfulQA < 60 or an active CVE status."

**Group permissions** grant specific groups access to approved models. Org-wide restrictions take precedence over group permissions.

**License agreements** — some models require accepting third-party terms before use. Admins accept on behalf of the organisation from the License Agreements tab.

**Sync** — after creating or modifying rules, sync the catalog to apply changes. Auto-sync runs on a schedule you configure.

---

## Step 4 — Create a Model Server

From a model's details page → **Create Server**, or from **Model Servers** → **Server**.

1. Enter a name for the server
2. Select the model from the dropdown (only models your admin has permitted appear)
3. Select a quantization level
4. Click **Create**

The server provisions and exposes an API endpoint at a fixed IP address and port. Starting a server consumes GPU/CPU resources — stop it when not in use.

---

## Step 5 — Connect your application

From the server's details page:

1. Copy the **Server Address** — this is your `base_url`
2. Generate an **API key** from the API Keys page — this is your `api_key`

```bash
export MODEL_SERVER_BASE_URL="http://your-platform-server-ip:port"
export ANACONDA_API_KEY="your-api-key"
```

Map to the standard env vars used throughout this module:

```bash
export INFERENCE_BASE_URL="$MODEL_SERVER_BASE_URL"
export INFERENCE_API_KEY="$ANACONDA_API_KEY"
export INFERENCE_MODEL=""   # model is already loaded on the server — pass empty string
```

---

## Step 6 — Call the endpoint

```python
from inference_client import get_client, INFERENCE_MODEL

client = get_client()

response = client.chat.completions.create(
    model="",            # required but ignored — model is loaded on the server
    messages=[
        {"role": "system", "content": "You are an astrophysics analysis agent."},
        {"role": "user",   "content": "Classify this transit signal: depth=1.01%"},
    ],
    max_completion_tokens=200,
    temperature=0.1,
)

print(response.choices[0].message.content)
```

The call is **identical** to the vLLM and AI Navigator calls. Only the env vars differ.

---

## What Anaconda Platform adds vs vLLM

| | vLLM (self-hosted) | Anaconda Platform |
|---|---|---|
| Model source | Any HuggingFace model | Anaconda-curated catalog |
| Security scanning | You manage | CVE scanning + Responsible AI scoring |
| Governance | None | Org-wide rules + group permissions |
| AIBOM | Not provided | Downloadable per model |
| Auth | Optional `--api-key` flag | Mandatory API key |
| Admin UI | None | Full web UI |
| Availability | You manage | Platform-managed |
| Benchmark comparison | Not provided | Chart view, normalised scores |

For organisations where "what model is this agent using and has it been approved" needs an answer, Anaconda Platform provides that answer. For teams that just need fast GPU inference under their own control, vLLM is the right choice.

---

## Further reading

- [Model Catalog docs](https://anaconda.com/docs/anaconda-platform/self-hosted/latest/user/model-catalog)
- [Model Servers docs](https://anaconda.com/docs/anaconda-platform/self-hosted/latest/user/model-servers)
- [Model Governance docs](https://anaconda.com/docs/anaconda-platform/self-hosted/latest/admin/model-governance)
- [API Keys docs](https://anaconda.com/docs/anaconda-platform/self-hosted/latest/user/api-keys)
