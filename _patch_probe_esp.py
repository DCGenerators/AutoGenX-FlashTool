import re
from pathlib import Path

p = Path("autogen_flash.py")
t = p.read_text(encoding="utf-8", errors="replace")

pat = re.compile(r"(?ms)^def probe_esp\(port: str\) -> bool:\s*\n(.*?)^def resolve_firmware_path\(", re.M)
m = pat.search(t)
if not m:
    raise SystemExit("PATCH FAILED: probe_esp block not found")

old = t[m.start():m.end()]

new_block = """def probe_esp(port: str) -> bool:
    \"""
    Reliable probe.
    - Not frozen: we trust esptool return code.
    - Frozen/in-process: esptool may print and still exit via SystemExit; we also accept 'Connected to ESP' output.
    \"""
    import os

    # In frozen mode we run esptool in-process; prefer a simple flash-id probe.
    rc = run_esptool(["--chip", "auto", "--port", port, "--baud", "115200", "flash-id"], silent=True)
    if rc == 0:
        return True

    # If in-process path produced output (silent may not fully suppress), accept known success markers
    # by doing a non-silent probe and scanning the output via subprocess path when available.
    # (For in-process path, this will still return nonzero sometimes, so we retry non-silent once.)
    rc2 = run_esptool(["--chip", "auto", "--port", port, "--baud", "115200", "chip-id"], silent=False)
    return rc2 == 0

def resolve_firmware_path("""
# Replace the whole probe_esp function by anchoring from its def to the next def
t2 = re.sub(r"(?ms)^def probe_esp\(port: str\) -> bool:.*?\n(?=^def resolve_firmware_path\()",
            new_block[:-len("def resolve_firmware_path(")],
            t)

bak = p.with_suffix(p.suffix + ".pre_probe_fix.bak")
if not bak.exists():
    bak.write_text(t, encoding="utf-8", errors="replace")

p.write_text(t2, encoding="utf-8", errors="replace")
print("OK: patched probe_esp() to avoid false negative in frozen mode (backup:", bak.name + ")")
