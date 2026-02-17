"""
Run the full weekly pipeline:
fetch -> parse -> metrics -> report -> dashboard

Usage:
    python run_weekly.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def run_step(name: str, script_path: Path) -> None:
    if not script_path.exists():
        raise FileNotFoundError(f"Step '{name}' not found: {script_path}")

    print(f"\n=== [{name}] ===")
    cmd = [sys.executable, str(script_path)]
    completed = subprocess.run(cmd, capture_output=True, text=True)

    if completed.stdout:
        print(completed.stdout.rstrip())
    if completed.returncode != 0:
        if completed.stderr:
            print(completed.stderr.rstrip())
        raise RuntimeError(f"Step '{name}' failed with exit code {completed.returncode}")


def main() -> None:
    project_root = Path(__file__).resolve().parent
    src = project_root / "src"

    steps = [
        ("fetch", src / "fetch.py"),
        ("parse", src / "parse.py"),
        ("metrics", src / "metrics.py"),
        ("report", src / "report.py"),
        ("dashboard", src / "dashboard.py"),
    ]

    print("TravelTech Ops Monitor — weekly run")
    print(f"Project root: {project_root}")

    for name, path in steps:
        run_step(name, path)

    print("\n Pipeline finished successfully.")
    print("Outputs:")
    print(f"- data/processed/* (parsed items + metrics)")
    print(f"- reports/* (md report + html dashboard)")


if __name__ == "__main__":
    main()