import re
from pathlib import Path

p = Path("autogen_flash_gui.py")
t = p.read_text(encoding="utf-8", errors="replace")

bak = p.with_suffix(p.suffix + ".pre_bootstrap_point_fix.bak")
if not bak.exists():
    bak.write_text(t, encoding="utf-8", errors="replace")

t2, n = re.subn(r'(?m)path\s*=\s*os\.path\.join\(base,\s*"autogen_flash\.py"\)',
                'path = os.path.join(base, "autogen_flash_pyi.py")', t)

if n != 1:
    raise SystemExit(f"PATCH FAILED: expected 1 path join for autogen_flash.py, got {n}")

p.write_text(t2, encoding="utf-8", errors="replace")
print("OK: bootstrap now loads autogen_flash_pyi.py from _MEIPASS (backup:", bak.name + ")")
