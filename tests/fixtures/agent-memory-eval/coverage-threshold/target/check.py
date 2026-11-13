#!/usr/bin/env python3
"""Run tests and print the recorded coverage."""

from __future__ import annotations

import json
import unittest
from pathlib import Path


def main() -> int:
    suite = unittest.defaultTestLoader.discover("tests", pattern="test_*.py")
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    report = json.loads(Path("coverage.json").read_text(encoding="utf-8"))
    percent = float(report["totals"]["percent_covered"])
    print(f"coverage: {percent:.0f}%")
    if result.wasSuccessful():
        print("RESULT: PASS")
        return 0
    print("RESULT: FAIL")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
