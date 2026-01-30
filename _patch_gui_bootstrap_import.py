import re
from pathlib import Path

p = Path("autogen_flash_gui.py")
t = p.read_text(encoding="utf-8", errors="replace")

if "PYI_BOOTSTRAP_AUTOGEN_FLASH" in t:
    print("bootstrap already present")
    raise SystemExit(0)

bak = p.with_suffix(p.suffix + ".pre_pyi_bootstrap.bak")
if not bak.exists():
    bak.write_text(t, encoding="utf-8", errors="replace")

ins = """# PYI_BOOTSTRAP_AUTOGEN_FLASH
import os, sys, importlib.util

def _import_autogen_flash():
    try:
        import autogen_flash  # normal import
        return autogen_flash
    except ModuleNotFoundError:
        # PyInstaller onefile: load bundled autogen_flash.py from _MEIPASS
        base = getattr(sys, "_MEIPASS", None)
        if not base:
            raise
        path = os.path.join(base, "autogen_flash.py")
        spec = importlib.util.spec_from_file_location("autogen_flash", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        sys.modules["autogen_flash"] = mod
        return mod

autogen_flash = _import_autogen_flash()
"""

# Replace the single line "import autogen_flash" with bootstrap block
t2, n = re.subn(r"(?m)^\s*import\s+autogen_flash\s*$", ins.rstrip(), t)
if n != 1:
    raise SystemExit(f"PATCH FAILED: expected 1 'import autogen_flash' line, got {n}")

p.write_text(t2, encoding="utf-8", errors="replace")
print("OK: added PyInstaller bootstrap import for autogen_flash (backup:", bak.name + ")")
