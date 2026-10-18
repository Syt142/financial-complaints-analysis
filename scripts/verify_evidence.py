"""Verify the exact bytes listed in an evidence manifest using only the stdlib."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def verify(evidence_dir: Path) -> bool:
    root = evidence_dir.resolve()
    try:
        manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
        if not isinstance(manifest, dict) or not manifest:
            raise ValueError("manifest must be a non-empty filename-to-SHA-256 object")
    except (OSError, ValueError) as exc:
        print(f"ERROR: cannot read manifest: {exc}")
        return False

    passed = 0
    for name, expected in manifest.items():
        try:
            target = (root / name).resolve()
            if not target.is_relative_to(root) or target == root:
                raise ValueError("path must stay within the evidence directory")
            if (
                not isinstance(expected, str)
                or len(expected) != 64
                or any(char not in "0123456789abcdefABCDEF" for char in expected)
            ):
                raise ValueError("invalid SHA-256 digest")
            digest = hashlib.sha256()
            with target.open("rb") as source:
                for chunk in iter(lambda: source.read(1024 * 1024), b""):
                    digest.update(chunk)
            actual = digest.hexdigest()
            if actual != expected.lower():
                print(f"FAIL {name}: expected {expected.lower()}, got {actual}")
                continue
            passed += 1
            print(f"PASS {name}")
        except (OSError, TypeError, ValueError) as exc:
            print(f"FAIL {name}: {exc}")

    print(f"Evidence SHA-256: {passed}/{len(manifest)} passed")
    return passed == len(manifest)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "evidence_dir",
        nargs="?",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "evidence",
        help="directory containing manifest.json (default: project evidence/)",
    )
    args = parser.parse_args()
    return 0 if verify(args.evidence_dir) else 1


if __name__ == "__main__":
    raise SystemExit(main())
