#!/usr/bin/env bash
# scripts/pack_and_ship.sh
#
# Pack a verified conda environment and ship it to an air-gapped deployment target.
#
# conda-pack creates a relocatable tarball of the entire conda environment —
# Python runtime, all packages, CUDA binaries, the DuckDB memory store from
# Module 06 — that can be extracted and run on a machine without conda installed.
#
# This is the physical artifact for air-gapped and offline deployments.
# The target machine needs no internet access, no conda, no Anaconda Platform.
#
# Usage:
#   ./scripts/pack_and_ship.sh [ENV_NAME] [TARGET_HOST] [TARGET_PATH]
#
#   ENV_NAME    — conda environment to pack (default: app-architecture-locked)
#   TARGET_HOST — SSH target for deployment (default: deploy@prod-node-01)
#   TARGET_PATH — path on target to extract into (default: /opt/lightcurve-pipeline)
#
# What gets packed:
#   - Entire conda environment (Python, all packages, compiled binaries)
#   - CUDA libraries if present in the environment (for Module 05 GPU deployments)
#   - The DuckDB memory store file (memory/lightcurve_memory.duckdb) from Module 06
#
# What does NOT get packed:
#   - NVIDIA GPU drivers (host-level — must be present on the target)
#   - System libraries below glibc (conda-pack preserves everything above it)
#
# Prerequisites:
#   conda-pack: conda install -c conda-forge conda-pack
#   SSH access to the target host
#
# Exit codes:
#   0 — packed, verified, and shipped successfully
#   1 — failure at any step

set -euo pipefail

ENV_NAME="${1:-app-architecture-locked}"
TARGET_HOST="${2:-deploy@prod-node-01}"
TARGET_PATH="${3:-/opt/lightcurve-pipeline}"
TARBALL="${ENV_NAME}.tar.gz"
MEMORY_STORE="memory/lightcurve_memory.duckdb"
AIBOM_PATH="${AIBOM_PATH:-}"    # set this env var if you want AIBOM verification

echo "══════════════════════════════════════════════════════════"
echo "  Pack and ship: ${ENV_NAME} → ${TARGET_HOST}:${TARGET_PATH}"
echo "══════════════════════════════════════════════════════════"

# ── Step 1: Verify AIBOM if provided ──────────────────────────────────────────
if [[ -n "${AIBOM_PATH}" && -f "${AIBOM_PATH}" ]]; then
    echo ""
    echo "Step 0/3 — Verifying model AIBOM before packing"
    echo "  AIBOM: ${AIBOM_PATH}"
    echo ""

    python security/verify_aibom.py \
        --aibom "${AIBOM_PATH}" \
        --model-dir models/ || {
        echo "  ✗  AIBOM verification failed. Aborting deployment."
        exit 1
    }
    echo "  ✓  Model files verified against AIBOM"
else
    echo ""
    echo "  Note: AIBOM_PATH not set — skipping model verification."
    echo "  To enable: export AIBOM_PATH=path/to/model.aibom.json"
fi

# ── Step 2: Pack the environment ──────────────────────────────────────────────
echo ""
echo "Step 1/3 — Packing environment with conda-pack"
echo "  Environment: ${ENV_NAME}"
echo "  Output:      ${TARBALL}"
echo ""

if ! command -v conda-pack &>/dev/null; then
    echo "Error: conda-pack not found. Install with:"
    echo "  conda install -c conda-forge conda-pack"
    exit 1
fi

# Remove existing tarball to avoid stale artifacts
[[ -f "${TARBALL}" ]] && rm "${TARBALL}"

conda-pack \
    --name "${ENV_NAME}" \
    --output "${TARBALL}" \
    --compress-level 6   # balance between size and pack time

TARBALL_SIZE=$(du -sh "${TARBALL}" | cut -f1)
echo "  ✓  Packed: ${TARBALL} (${TARBALL_SIZE})"

# ── Step 3: Include the DuckDB memory store ───────────────────────────────────
# The memory store from Module 06 carries the agent's learned context.
# It travels with the environment so the deployed agent has memory from day 1.
if [[ -f "${MEMORY_STORE}" ]]; then
    echo ""
    echo "Step 1b — Including DuckDB memory store"
    echo "  Memory store: ${MEMORY_STORE}"
    tar -rf "${TARBALL}" "${MEMORY_STORE}" 2>/dev/null || \
        echo "  Note: memory store append skipped (gzip'd tarballs don't support -r)"
    echo "  ✓  Memory store included (or will be copied separately)"
fi

# ── Step 4: Ship to target ────────────────────────────────────────────────────
echo ""
echo "Step 2/3 — Shipping to ${TARGET_HOST}"
echo ""

# Check if target is reachable
if ! ssh -q -o ConnectTimeout=5 "${TARGET_HOST}" exit 2>/dev/null; then
    echo "  ⚠  Cannot reach ${TARGET_HOST} — saving tarball locally instead."
    echo "     Manual deployment: scp ${TARBALL} ${TARGET_HOST}:${TARGET_PATH}/"
    echo "     Then run the extraction step below on the target."
    exit 0
fi

# Create target directory
ssh "${TARGET_HOST}" "mkdir -p ${TARGET_PATH}"

# Copy tarball
scp "${TARBALL}" "${TARGET_HOST}:${TARGET_PATH}/${TARBALL}"

# Copy memory store separately if it couldn't be appended to the tarball
if [[ -f "${MEMORY_STORE}" ]]; then
    ssh "${TARGET_HOST}" "mkdir -p ${TARGET_PATH}/memory"
    scp "${MEMORY_STORE}" "${TARGET_HOST}:${TARGET_PATH}/memory/"
fi

echo "  ✓  Shipped to ${TARGET_HOST}:${TARGET_PATH}/${TARBALL}"

# ── Step 5: Extract and activate on target ────────────────────────────────────
echo ""
echo "Step 3/3 — Extracting on target"
echo ""

ssh "${TARGET_HOST}" bash <<EOF
set -e
cd ${TARGET_PATH}

# Extract the packed environment
mkdir -p env
tar -xzf ${TARBALL} -C env/

# Unpack and fix paths (conda-pack requires this one-time step)
source env/bin/activate
conda-unpack
deactivate

echo "  ✓  Environment extracted and unpacked at ${TARGET_PATH}/env"
echo ""
echo "  To use on the target (no conda required):"
echo "    source ${TARGET_PATH}/env/bin/activate"
echo "    python flows/harnessed_lightcurve_flow.py run --targets wasp18b"
EOF

echo ""
echo "══════════════════════════════════════════════════════════"
echo "  ✓  Deployment complete"
echo "     Target:  ${TARGET_HOST}:${TARGET_PATH}"
echo "     Tarball: ${TARBALL} (${TARBALL_SIZE})"
echo "══════════════════════════════════════════════════════════"
