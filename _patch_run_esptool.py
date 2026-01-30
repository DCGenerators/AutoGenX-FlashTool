import re
from pathlib import Path

path = Path("autogen_flash.py")
text = path.read_text(encoding="utf-8", errors="replace")

pattern = re.compile(
    r"(?ms)^def run_esptool\(.*?\n.*?^def probe_esp\(",
)

replacement = """def run_esptool(args, silent=False) -> int:
    \"""
    GUI-safe runner:
    - Frozen (.exe): run bundled esptool.exe from sys._MEIPASS
    - Not frozen: run 'esptool' from environment
    \"""
    import subprocess, os, sys

    # Windows: prevent popping console windows
    CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

    if is_frozen():
        esptool_bin = os.path.join(sys._MEIPASS, "esptool.exe")
        cmd = [esptool_bin] + list(args)
    else:
        cmd = ["esptool"] + list(args)

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

def probe_esp("""

m = pattern.search(text)
if not m:
    raise SystemExit("PATCH FAILED: could not locate run_esptool/probe_esp boundary")

bak = path.with_suffix(path.suffix + ".pre_run_esptool_patch.bak")
if not bak.exists():
    bak.write_text(text, encoding="utf-8", errors="replace")

new_text = text[:m.start()] + replacement + text[m.end():]
path.write_text(new_text, encoding="utf-8", errors="replace")
print("OK: patched run_esptool() (backup:", bak.name + ")")
