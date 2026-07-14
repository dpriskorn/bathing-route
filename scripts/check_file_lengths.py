#!/usr/bin/env python3
import sys
from pathlib import Path

MAX_LINES = 500
PATTERNS = ["*.py", "*.ts", "*.vue"]
ROOTS = [Path("backend/src"), Path("frontend/src")]

over = []
for root in ROOTS:
    for pattern in PATTERNS:
        for f in root.glob(pattern):
            lines = f.read_text(errors="ignore").count("\n") + 1
            if lines > MAX_LINES:
                over.append((f, lines))

if over:
    print(f"Files exceeding {MAX_LINES} lines:")
    for f, n in sorted(over):
        print(f"  {f}: {n} lines")
    print(f"\nERROR: {len(over)} file(s) exceed {MAX_LINES} lines")
    sys.exit(1)

print(f"All files within {MAX_LINES}-line limit.")
