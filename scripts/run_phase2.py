"""PyCharm entry: hand example -> all tests -> historical hashes -> real baseline."""
from pathlib import Path
import sys
import json
import hashlib
import platform
import subprocess
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from complaints_analyzer.phase2 import score_point, run


def main():
    out = ROOT / "results/phase2"
    out.mkdir(parents=True, exist_ok=True)
    log = []
    def record(text):
        print(text, flush=True)
        log.append(text)
    record(f"PHASE 2 | {datetime.now(timezone.utc).isoformat()} | Python {platform.python_version()}")
    hand = score_point(130, [100] * 12)
    assert hand["baseline"] == 100 and hand["score"] == 30 and hand["zero_mad"]
    record("HAND EXAMPLE PASS: median=100, MAD=0, scale=1, score=30; not a probability")
    for command in ([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
                    [sys.executable, "scripts/verify_evidence.py"]):
        completed = subprocess.run(command, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                   encoding="utf-8", errors="replace")
        record(completed.stdout)
        if completed.returncode:
            (out / "run_log.txt").write_text("\n".join(log), encoding="utf-8")
            raise SystemExit(completed.returncode)
    metrics = run(ROOT / "evidence/cross_tables.csv", ROOT / "configs/phase2.json", out)
    record(json.dumps(metrics, ensure_ascii=False, indent=2))
    record("PHASE 2 COMPLETE: test scores deferred; raw CSV was not opened.")
    (out / "run_log.txt").write_text("\n".join(log), encoding="utf-8")
    manifest = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.iterdir())
                if p.is_file() and p.name != "manifest.json"}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
