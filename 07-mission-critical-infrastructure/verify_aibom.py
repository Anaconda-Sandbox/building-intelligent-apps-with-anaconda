"""
security/verify_aibom.py

Verify a downloaded model file against its AIBOM (AI Bill of Materials).

Anaconda Platform provides an AIBOM for every model in the Model Catalog
as a .json file in CycloneDX format. Download it from:
  Model Catalog → [model] → Overview tab → Download AIBOM

The AIBOM contains SHA-256 checksums for every quantization variant.
This script verifies your downloaded model file hasn't been tampered with.

Usage:
    python security/verify_aibom.py \\
        --aibom model.aibom.json \\
        --model model.gguf

    # Or check all files in a directory against the AIBOM:
    python security/verify_aibom.py \\
        --aibom model.aibom.json \\
        --model-dir ./models/

Exit codes:
    0 — all files verified
    1 — one or more files failed verification or AIBOM parsing error

References:
    Anaconda Platform Model Catalog docs:
    https://anaconda.com/docs/anaconda-platform/self-hosted/latest/user/model-catalog
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path


# ── AIBOM parsing ─────────────────────────────────────────────────────────────

def load_aibom(aibom_path: Path) -> dict:
    """
    Load and parse an Anaconda Platform AIBOM (CycloneDX JSON format).
    Returns a dict of { filename: expected_sha256 }.
    """
    with open(aibom_path) as f:
        aibom = json.load(f)

    hashes: dict[str, str] = {}

    # CycloneDX structure: components[].externalReferences[].hashes[]
    # or components[].hashes[] depending on model publisher disclosure.
    # Anaconda Platform populates SHA-256 in the Files tab metadata.
    components = aibom.get("components", [])

    for component in components:
        name = component.get("name", "")

        # Direct hashes on the component (common for model files)
        for h in component.get("hashes", []):
            if h.get("alg", "").upper() in ("SHA-256", "SHA256"):
                hashes[name] = h["content"].lower()

        # External references (some AIBOMs store file hashes here)
        for ref in component.get("externalReferences", []):
            ref_name = Path(ref.get("url", "")).name
            for h in ref.get("hashes", []):
                if h.get("alg", "").upper() in ("SHA-256", "SHA256"):
                    hashes[ref_name] = h["content"].lower()

    # Also check top-level metadata.component (the model itself)
    meta_component = aibom.get("metadata", {}).get("component", {})
    for h in meta_component.get("hashes", []):
        if h.get("alg", "").upper() in ("SHA-256", "SHA256"):
            name = meta_component.get("name", "model")
            hashes[name] = h["content"].lower()

    return hashes


def compute_sha256(file_path: Path) -> str:
    """Compute SHA-256 of a file, streaming to avoid loading it all into memory."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


# ── Verification ──────────────────────────────────────────────────────────────

def verify_file(file_path: Path, expected_hash: str) -> bool:
    """Verify a single file against its expected SHA-256."""
    print(f"  Verifying {file_path.name}...")
    actual = compute_sha256(file_path)

    if actual == expected_hash.lower():
        print(f"  ✓  SHA-256 match: {actual[:16]}...")
        return True
    else:
        print(f"  ✗  SHA-256 MISMATCH")
        print(f"     Expected: {expected_hash}")
        print(f"     Actual:   {actual}")
        return False


def verify_against_aibom(
    aibom_path: Path,
    model_files: list[Path],
    strict: bool = True,
) -> dict:
    """
    Verify model files against AIBOM checksums.

    Args:
        aibom_path:   Path to the CycloneDX JSON AIBOM from Anaconda Platform
        model_files:  List of model files to verify
        strict:       If True, fail if a model file has no AIBOM entry.
                      If False, warn and continue.

    Returns:
        {
            "passed": bool,
            "verified": list[str],     # files that matched
            "failed": list[str],       # files that didn't match
            "unverified": list[str],   # files with no AIBOM entry
            "aibom_entries": int,      # total entries found in AIBOM
        }
    """
    print(f"\nLoading AIBOM: {aibom_path}")
    expected_hashes = load_aibom(aibom_path)
    print(f"  Found {len(expected_hashes)} hash entries in AIBOM")

    if not expected_hashes:
        print("  ⚠  No SHA-256 hashes found in AIBOM.")
        print("     The model publisher may not have disclosed checksums.")
        print("     Contact your Anaconda TAM to request a complete AIBOM.")

    verified   = []
    failed     = []
    unverified = []

    for file_path in model_files:
        fname = file_path.name

        # Look for an exact filename match, then try partial matches
        expected = expected_hashes.get(fname)
        if expected is None:
            # Try matching by stem (without extension) or partial name
            for key, val in expected_hashes.items():
                if fname in key or key in fname:
                    expected = val
                    break

        if expected is None:
            msg = f"  {'✗' if strict else '⚠'}  No AIBOM entry for {fname}"
            print(msg)
            unverified.append(fname)
            continue

        if verify_file(file_path, expected):
            verified.append(fname)
        else:
            failed.append(fname)

    all_passed = (
        len(failed) == 0
        and (not strict or len(unverified) == 0)
    )

    return {
        "passed":        all_passed,
        "verified":      verified,
        "failed":        failed,
        "unverified":    unverified,
        "aibom_entries": len(expected_hashes),
    }


def print_summary(result: dict) -> None:
    print("\n── Verification Summary ─────────────────────────────────────────")
    print(f"  AIBOM entries:   {result['aibom_entries']}")
    print(f"  Verified:        {len(result['verified'])}")
    print(f"  Failed:          {len(result['failed'])}")
    print(f"  No AIBOM entry:  {len(result['unverified'])}")
    print()

    if result["failed"]:
        print("  FAILED FILES (do not use these models):")
        for f in result["failed"]:
            print(f"    ✗  {f}")

    if result["unverified"]:
        print("  UNVERIFIED FILES (no checksum in AIBOM):")
        for f in result["unverified"]:
            print(f"    ⚠  {f}")

    if result["passed"]:
        print("  ✓  All files verified successfully.")
    else:
        print("  ✗  Verification FAILED. Do not deploy unverified models.")

    print("─────────────────────────────────────────────────────────────────")


# ── CLI ───────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify model files against an Anaconda Platform AIBOM."
    )
    parser.add_argument(
        "--aibom", required=True, type=Path,
        help="Path to the CycloneDX JSON AIBOM downloaded from Anaconda Platform",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--model", type=Path,
        help="Path to a single model file to verify",
    )
    group.add_argument(
        "--model-dir", type=Path,
        help="Directory of model files to verify (all files in directory)",
    )
    parser.add_argument(
        "--no-strict", action="store_true",
        help="Warn instead of failing when a file has no AIBOM entry",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if not args.aibom.exists():
        print(f"Error: AIBOM file not found: {args.aibom}", file=sys.stderr)
        return 1

    if args.model:
        if not args.model.exists():
            print(f"Error: model file not found: {args.model}", file=sys.stderr)
            return 1
        model_files = [args.model]
    else:
        if not args.model_dir.is_dir():
            print(f"Error: model directory not found: {args.model_dir}", file=sys.stderr)
            return 1
        model_files = [
            p for p in args.model_dir.iterdir()
            if p.is_file() and not p.name.startswith(".")
        ]
        if not model_files:
            print(f"Error: no files found in {args.model_dir}", file=sys.stderr)
            return 1

    result = verify_against_aibom(
        aibom_path=args.aibom,
        model_files=model_files,
        strict=not args.no_strict,
    )
    print_summary(result)
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
