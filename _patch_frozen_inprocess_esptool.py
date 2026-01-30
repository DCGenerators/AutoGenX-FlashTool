import re
from pathlib import Path

p = Path("autogen_flash.py")
t = p.read_text(encoding="utf-8", errors="replace")

# Replace the frozen/non-frozen cmd builder with:
# - If frozen on Windows: run esptool in-process (import esptool; esptool.main())
# - Else: use python -m esptool (already patched earlier)
pattern = re.compile(
    r"(?ms)^\s*if\s+is_frozen\(\):\s*\n\s*esptool_bin\s*=.*?\n\s*cmd\s*=\s*\[esptool_bin\]\s*\+\s*list\(args\)\s*\n\s*else:\s*\n\s*cmd\s*=\s*\[.*?\]\s*\+\s*list\(args\)\s*$"
)

replacement = """    if is_frozen() and os.name == "nt":
        try:
            import io, contextlib

            import esptool  # bundled by PyInstaller via import graph

            if silent:
                with open(os.devnull, "w") as dn:
                    with contextlib.redirect_stdout(dn), contextlib.redirect_stderr(dn):
                        try:
                            esptool.main(list(args))
                            return 0
                        except SystemExit as ex:
                            return int(ex.code) if isinstance(ex.code, int) else 1
            else:
                try:
                    esptool.main(list(args))
                    return 0
                except SystemExit as ex:
                    return int(ex.code) if isinstance(ex.code, int) else 1
        except Exception:
            return 2

    # Not frozen (or non-Windows frozen): run module via current Python
    cmd = [sys.executable, "-m", "esptool"] + list(args)"""

m = pattern.search(t)
if not m:
    raise SystemExit("PATCH FAILED: could not locate frozen/non-frozen cmd builder inside run_esptool()")

bak = p.with_suffix(p.suffix + ".pre_frozen_inprocess_esptool.bak")
if not bak.exists():
    bak.write_text(t, encoding="utf-8", errors="replace")

t2 = t[:m.start()] + replacement + t[m.end():]
p.write_text(t2, encoding="utf-8", errors="replace")
print("OK: patched frozen-Windows esptool to in-process (backup:", bak.name + ")")
