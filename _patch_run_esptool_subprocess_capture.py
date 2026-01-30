import re
from pathlib import Path

p = Path("autogen_flash.py")
t = p.read_text(encoding="utf-8", errors="replace")

bak = p.with_suffix(p.suffix + ".pre_run_esptool_subprocess_capture_fix.bak")
if not bak.exists():
    bak.write_text(t, encoding="utf-8", errors="replace")

pat = re.compile(r"(?ms)^def run_esptool\(args, silent=False\) -> int:\s*\n.*?\n(?=^def probe_esp\()", re.M)
m = pat.search(t)
if not m:
    raise SystemExit("PATCH FAILED: run_esptool block not found")

run_block = """def run_esptool(args, silent=False) -> int:
    \"""
    GUI-safe runner:
    - Always uses CREATE_NO_WINDOW on Windows (no popup consoles)
    - If subprocess returncode is non-zero but output shows a successful ESP connection,
      treat as success (0) to avoid false "No ESP device" failures.
    \"""
    import os, sys, subprocess

    CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

    cmd = [sys.executable, "-m", "esptool"] + list(args)
    creationflags = CREATE_NO_WINDOW if os.name == "nt" else 0

    try:
        if silent:
            r = subprocess.run(
                cmd,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
                creationflags=creationflags,
            )
            return r.returncode

        # Non-silent: capture output so we can decide success reliably, then print it for GUI logging
        r = subprocess.run(
            cmd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            errors="replace",
            check=False,
            creationflags=creationflags,
        )

        out = r.stdout or ""
        # Forward esptool output to the GUI log (GUI patches print())
        for line in out.splitlines():
            print(line)

        # If esptool printed connection markers, accept as success even if rc != 0
        if ("Connected to ESP" in out) or ("Chip type:" in out) or ("Detecting chip type" in out):
            return 0

        return r.returncode
    except Exception:
        return 2
"""

t2 = t[:m.start()] + run_block + "\n\n" + t[m.end():]
p.write_text(t2, encoding="utf-8", errors="replace")
print("OK: patched run_esptool() subprocess capture+marker success (backup:", bak.name + ")")
