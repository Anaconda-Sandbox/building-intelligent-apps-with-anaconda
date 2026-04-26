# vLLM — Self-Hosted GPU Inference

vLLM is an open-source inference server optimised for throughput on NVIDIA GPUs. It serves HuggingFace models via an OpenAI-compatible API, handles concurrent requests through continuous batching, and manages GPU memory efficiently via PagedAttention.

**When to use this:** Production workloads, GPU hardware you control, maximum throughput, or when you need to serve a specific model that isn't available in Anaconda Platform's catalog.

---

## Hardware requirements

| GPU | VRAM | Suitable models |
|---|---|---|
| L4, T4, A10G | 16–24 GB | 7B–13B parameter models |
| L40S, A100 40GB | 40–48 GB | 30B–70B parameter models |
| A100 80GB, H100 | 80 GB | 70B+ models, full precision |

Use [Brev](https://brev.nvidia.com) to provision a GPU instance on demand — the setup in Module 05 uses this path. For permanent infrastructure, any EC2 `p3`/`g5`/`p4` instance or GCP/Azure GPU VM works.

---

## Setup

### 1. Provision a Linux box with a GPU

```bash
# On Brev (from your local machine):
brev create vllm-server --gpu L40S
brev shell vllm-server

# Verify GPU
nvidia-smi
```

### 2. Set up the conda environment

```bash
# Install Miniconda if not present
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash Miniconda3-latest-Linux-x86_64.sh -b && source ~/.bashrc

# Create environment
# Note: vLLM is PyPI-only — this is the conda-pypi pattern from Module 05
conda create -n vllm-serve python=3.11 -y
conda activate vllm-serve

# Install vLLM (pip section — fastest changing GPU tooling on PyPI)
pip install vllm>=0.4.0
```

### 3. Start the server

```bash
# Serve a model from HuggingFace
# First run downloads the model (~7GB for a 7B model)
python -m vllm.entrypoints.openai.api_server \
    --model mistralai/Mistral-7B-Instruct-v0.3 \
    --host 0.0.0.0 \
    --port 8000

# For Nemotron (Module 05 default, needs ~20GB VRAM):
python -m vllm.entrypoints.openai.api_server \
    --model nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16 \
    --host 0.0.0.0 \
    --port 8000 \
    --max-model-len 32768
```

Server is ready when you see: `INFO: Application startup complete.`

### 4. Configure your environment (on the calling machine)

```bash
export INFERENCE_BASE_URL="http://your-server-ip:8000/v1"
export INFERENCE_API_KEY="not-needed"     # vLLM has no auth by default
export INFERENCE_MODEL="mistralai/Mistral-7B-Instruct-v0.3"
```

### 5. Verify

```bash
python inference_client.py
# Expected output:
#   status: ok
#   base_url: http://your-server-ip:8000/v1
#   model: mistralai/Mistral-7B-Instruct-v0.3
#   response: ready
#   latency_s: 0.3
```

---

## vLLM vs AI Navigator

| | AI Navigator | vLLM |
|---|---|---|
| Model format | GGUF (quantized) | HuggingFace safetensors |
| Concurrency | Serial (slots) | Continuous batching |
| GPU requirement | Optional (CPU works) | Required for production throughput |
| Auth | API key (optional) | None by default (add `--api-key` flag) |
| Platform | Windows, macOS | Linux (primary), any GPU node |
| OpenAI compat | `/v1` prefix required | Native at `/v1` |

**The models are not interchangeable.** A GGUF file downloaded in AI Navigator cannot be loaded by vLLM. They're different format representations of the same underlying model weights. Download from HuggingFace for vLLM.

---

## Adding authentication

For production, add an API key:

```bash
python -m vllm.entrypoints.openai.api_server \
    --model mistralai/Mistral-7B-Instruct-v0.3 \
    --api-key your-secret-key \
    --host 0.0.0.0 \
    --port 8000
```

Then set `INFERENCE_API_KEY="your-secret-key"` on the calling side.

---

## Running as a systemd service

For a persistent server that survives reboots:

```ini
# /etc/systemd/system/vllm.service
[Unit]
Description=vLLM inference server
After=network.target

[Service]
Type=simple
User=ubuntu
Environment="HF_HOME=/data/hf_cache"
ExecStart=/home/ubuntu/miniconda3/envs/vllm-serve/bin/python \
    -m vllm.entrypoints.openai.api_server \
    --model mistralai/Mistral-7B-Instruct-v0.3 \
    --host 0.0.0.0 \
    --port 8000
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable vllm
sudo systemctl start vllm
sudo systemctl status vllm
```

---

## Checking throughput (optional)

vLLM exposes a `/metrics` endpoint (Prometheus format) and a `/health` endpoint:

```bash
curl http://localhost:8000/health
# {"status":"ok"}

curl http://localhost:8000/metrics | grep vllm_request
# vllm_request_success_total ...
# vllm_request_prompt_tokens_total ...
```

This is the throughput data shown in the Module 05 benchmark cell.

---

## conda-pypi note

vLLM is a PyPI-only package — it moves faster than conda-forge packaging can track. The `environment.yml` in Module 05 uses a `pip:` section for vLLM. `conda-pypi` (experimental, Q1 2026) is the safer long-term path for integrating PyPI wheels into conda environments: [conda/conda-pypi](https://github.com/conda/conda-pypi).

---

## Further reading

- [vLLM documentation](https://docs.vllm.ai)
- [Supported models](https://docs.vllm.ai/en/stable/models/supported_models.html)
- [Brev GPU provisioning](https://docs.nvidia.com/brev)
- [Module 05 — GPU-Accelerated Intelligence](../../05-gpu-accelerated-intelligence/README.md)
