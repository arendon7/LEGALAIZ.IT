#!/usr/bin/env python3
from hashlib import sha256
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
MANIFEST = ROOT / "SHA256SUMS_FINAL.txt"

if not MANIFEST.is_file():
    print("FALLO: no existe SHA256SUMS_FINAL.txt")
    raise SystemExit(1)

failures = []
checked = 0
for line in MANIFEST.read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if not line or line.startswith("#"):
        continue
    expected, relative = line.split("  ", 1)
    path = ROOT / relative
    if not path.is_file():
        failures.append(f"Falta: {relative}")
        continue
    actual = sha256(path.read_bytes()).hexdigest()
    checked += 1
    if actual != expected:
        failures.append(f"Hash incorrecto: {relative}")

if failures:
    print("INTEGRIDAD FALLIDA")
    for item in failures:
        print("-", item)
    raise SystemExit(1)
print(f"INTEGRIDAD OK · {checked} archivos verificados")
