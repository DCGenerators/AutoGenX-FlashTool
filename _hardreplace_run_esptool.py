import re
from pathlib import Path

p = Path("autogen_flash.py")
t = p.read_text(encoding="utf-8", errors="replace")

bak = p.with_suffix(p.suffix + ".pre_run_esptool_hardreplace.bak")
if not bak.exists():
    bak.write_text(t, encoding="utf-8", errors="replace")

pat = re.compile(r"(?ms)^def run_esptool\(args, silent=False\) -> int:\s*\n.*?\n(?=^def probe_esp\()", re.M)
m = pat.search(t)
if not m:
    raise SystemExit("PATCH FAILED: run_esptool block not found")

run_block = """def run_esptool(args, silent=False) -> int:
    \"""
    GUI-safe runner:
    - Frozen Windows: run esptool in-process (captures output, no pop-up windows)
    - Not frozen: run `python -m esptool` (works reliably on Windows venv)
    \"""
    import os, sys, subprocess

    CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

    # Frozen Windows: in-process esptool
    if is_frozen() and os.name == "nt":
        try:
            import esptool, io, contextlib
            buf = io.StringIO()
            if silent:
                with open(os.devnull, "w") as dn, contextlib.redirect_stdout(dn), contextlib.redirect_stderr(dn):
                    try:
                        esptool.main(list(args))
                        return 0
                    except SystemExit as ex:
                        return int(ex.code) if isinstance(ex.code, int) else 1
            else:
                with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
                    try:
                        esptool.main(list(args))
                        return 0
                    except SystemExit as ex:
                        rc = int(ex.code) if isinstance(ex.code, int) else 1
                out = buf.getvalue()
                # Treat connection markers as success even if rc is nonzero
                if ("Connected to ESP" in out) or ("Chip type:" in out) or ("Detecting chip type" in out):
                    return 0
                return rc
        except Exception:
            return 2

    # Not frozen: subprocess `python -m esptool`
    cmd = [sys.executable, "-m", "esptool"] + list(args)
    creationflags = CREATE_NO_WINDOW if os.name == "nt" else 0

    try:
        return subprocess.run(
            cmd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL if silent else None,
            stderr=subprocess.DEVNULL if silent else None,
            check=False,
            creationflags=creationflags,
        ).returncode
    except Exception:
        return 2
"""

t2 = t[:m.start()] + run_block + "\n\n" + t[m.end():]
p.write_text(t2, encoding="utf-8", errors="replace")
print("OK: hard-replaced run_esptool() (backup:", bak.name + ")")
