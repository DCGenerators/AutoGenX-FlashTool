import re
from pathlib import Path

p = Path("autogen_flash.py")
t = p.read_text(encoding="utf-8", errors="replace")

# Replace the non-frozen command builder: cmd = ["esptool"] + list(args)
t2, n = re.subn(
    r'(?m)^\s*cmd\s*=\s*\["esptool"\]\s*\+\s*list\(args\)\s*$',
    '        cmd = [sys.executable, "-m", "esptool"] + list(args)',
    t
)

if n != 1:
    raise SystemExit(f"PATCH FAILED: expected 1 match, got {n}")

bak = p.with_suffix(p.suffix + ".pre_python_m_esptool.bak")
if not bak.exists():
    bak.write_text(t, encoding="utf-8", errors="replace")

p.write_text(t2, encoding="utf-8", errors="replace")
print("OK: non-frozen esptool now runs via python -m esptool (backup:", bak.name + ")")
