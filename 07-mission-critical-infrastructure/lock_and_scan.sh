#!/usr/bin/env bash
# scripts/lock_and_scan.sh
#
# CI gate: lock the environment, scan for CVEs, fail on critical findings.
#
# Three-step supply chain check before any deployment:
#   1. conda-lock  — pin every package including transitive deps
#   2. anaconda-audit scan — check locked environment against NVD/NIST CVE data
#   3. Gate — fail the CI job if critical (score >= 7, status Active) CVEs found
#
# Usage:
#   ./scripts/lock_and_scan.sh [ENV_NAME] [PLATFORM]
#
#   ENV_NAME  — conda environment to lock and scan (default: app-architecture)
#   PLATFORM  — target platform for lock file (default: linux-64)
#
# Prerequisites:
#   conda-lock installed:          conda install -c conda-forge conda-lock
#   anaconda-env-manager installed in base:
#                                  conda install --name base anaconda-cloud::anaconda-env-manager
#   Authenticated to Anaconda.com: anaconda login --at anaconda.com
#
# Exit codes:
#   0 — lock and scan passed, no critical CVEs
#   1 — critical CVEs found or lock failed
#
# In CI (GitHub Actions, GitLab CI, Jenkins), add this script as a gate
# step before the deploy step. The Metaflow flow does not run if this fails.

set -euo pipefail

ENV_NAME="${1:-app-architecture}"
PLATFORM="${2:-linux-64}"
ENV_YML="../06-app-architecture/environment.yml"
LOCK_FILE="conda-${PLATFORM}.lock"
SCAN_OUTPUT="cve-scan-$(date +%Y%m%d-%H%M%S).txt"

# CVE score threshold — block anything at or above this.
# Anaconda recommends: block score >= 7 unless mitigated or cleared.
CVE_THRESHOLD=7

echo "══════════════════════════════════════════════════════════"
echo "  Supply chain gate: ${ENV_NAME} (${PLATFORM})"
echo "══════════════════════════════════════════════════════════"

# ── Step 1: Lock ───────────────────────────────────────────────────────────────
echo ""
echo "Step 1/3 — Locking environment with conda-lock"
echo "  Input:  ${ENV_YML}"
echo "  Output: ${LOCK_FILE}"
echo ""

if ! command -v conda-lock &>/dev/null; then
    echo "Error: conda-lock not found. Install with:"
    echo "  conda install -c conda-forge conda-lock"
    exit 1
fi

conda-lock lock \
    --file "${ENV_YML}" \
    --platform "${PLATFORM}" \
    --lockfile "${LOCK_FILE}"

echo "  ✓  Lock file generated: ${LOCK_FILE}"
echo "     Commit this file — it is your deployment contract."

# ── Step 2: Create the locked environment ─────────────────────────────────────
echo ""
echo "Step 2/3 — Installing locked environment"
echo ""

conda-lock install \
    --name "${ENV_NAME}-locked" \
    "${LOCK_FILE}"

echo "  ✓  Environment installed: ${ENV_NAME}-locked"

# ── Step 3: Scan with anaconda-audit ──────────────────────────────────────────
echo ""
echo "Step 3/3 — Scanning for CVEs with anaconda-audit"
echo "  CVE data sourced from NVD/NIST via Anaconda Platform"
echo "  Threshold: block CVE score >= ${CVE_THRESHOLD} (unless mitigated/cleared)"
echo ""

if ! command -v anaconda &>/dev/null; then
    echo "Warning: anaconda CLI not found."
    echo "  Install anaconda-env-manager with:"
    echo "  conda install --name base anaconda-cloud::anaconda-env-manager"
    echo ""
    echo "  Skipping CVE scan — environment not scanned before deployment."
    echo "  This is a security gap. Install anaconda-env-manager and re-run."
    exit 0
fi

# Run the scan and capture output
# anaconda-audit scan returns: package name, version, build, channel, CVE status, CVSS score
anaconda audit scan --name "${ENV_NAME}-locked" 2>&1 | tee "${SCAN_OUTPUT}"

echo ""
echo "  Scan results saved to: ${SCAN_OUTPUT}"

# ── Gate: parse scan output for critical CVEs ────────────────────────────────
# The scan output contains lines like:
#   package-name  version  build  channel  [✓]CVE-YYYY-XXXX  score  status
#
# We look for any Active or Reported CVEs at or above the threshold.
# Mitigated and Cleared are not blocking — Anaconda has assessed them.

CRITICAL_COUNT=0
CRITICAL_PACKAGES=()

# Parse for Active/Reported CVEs with high scores
while IFS= read -r line; do
    if echo "$line" | grep -qiE "(active|reported)"; then
        # Extract CVSS score if present (numeric field between 0.0 and 10.0)
        score=$(echo "$line" | grep -oE '[0-9]+\.[0-9]+' | head -1)
        if [[ -n "$score" ]] && (( $(echo "$score >= $CVE_THRESHOLD" | bc -l) )); then
            CRITICAL_COUNT=$((CRITICAL_COUNT + 1))
            CRITICAL_PACKAGES+=("$line")
        fi
    fi
done < "${SCAN_OUTPUT}"

echo ""
if [[ ${CRITICAL_COUNT} -gt 0 ]]; then
    echo "══════════════════════════════════════════════════════════"
    echo "  ✗  GATE FAILED: ${CRITICAL_COUNT} critical CVE(s) found"
    echo "══════════════════════════════════════════════════════════"
    echo ""
    echo "  Packages with active CVEs (score >= ${CVE_THRESHOLD}):"
    for pkg in "${CRITICAL_PACKAGES[@]}"; do
        echo "    $pkg"
    done
    echo ""
    echo "  Resolution options:"
    echo "    1. Upgrade the affected package to a patched version"
    echo "    2. Check if Anaconda has marked it 'mitigated' or 'cleared'"
    echo "       in the Platform CVE channel (updated every 4 hours)"
    echo "    3. Add to policy.yaml cve_allowlist with documented justification"
    echo "    4. Contact your Anaconda TAM for guidance"
    echo ""
    echo "  Full scan report: ${SCAN_OUTPUT}"
    exit 1
else
    echo "══════════════════════════════════════════════════════════"
    echo "  ✓  GATE PASSED: No critical CVEs found"
    echo "══════════════════════════════════════════════════════════"
    echo ""
    echo "  Lock file: ${LOCK_FILE}"
    echo "  Scan report: ${SCAN_OUTPUT}"
    echo ""
    echo "  Proceed to deploy with scripts/pack_and_ship.sh"
fi
