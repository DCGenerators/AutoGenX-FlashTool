import re
from pathlib import Path

p = Path("autogen_flash.py")
t = p.read_text(encoding="utf-8", errors="replace")

# Replace probe_esp() with a frozen-Windows aware version that captures esptool output
pat = re.compile(r"(?ms)^def probe_esp\(port: str\) -> bool:.*?\n(?=^def resolve_firmware_path\()", re.M)
m = pat.search(t)
if not m:
    raise SystemExit("PATCH FAILED: probe_esp() block not found")

bak = p.with_suffix(p.suffix + ".pre_probe_capture_fix.bak")
if not bak.exists():
    bak.write_text(t, encoding="utf-8", errors="replace")

new_probe = """def probe_esp(port: str) -> bool:
    \"\"\"Reliable probe.
    In frozen Windows builds we run esptool in-process, so return-code can be misleading.
    We treat 'Connected to ESP' output as success.
    \"\"\"
    import os, io, contextlib

    # Frozen Windows: run esptool.main() here and capture output
    if is_frozen() and os.name == "nt":
        try:
            import esptool
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
                try:
                    esptool.main(["--chip","auto","--port", port, "--baud","115200","flash-id"])
                    rc = 0
                except SystemExit as ex:
                    rc = int(ex.code) if isinstance(ex.code, int) else 1
            out = buf.getvalue()
            if ("Connected to ESP" in out) or ("Chip type:" in out) or ("Detecting chip type" in out):
                return True
            return rc == 0
        except Exception:
            return False

    # Not frozen: trust subprocess return code
    rc = run_esptool(["--chip","auto","--port", port, "--baud","115200","flash-id"], silent=True)
    return rc == 0
"""

t2 = t[:m.start()] + new_probe + "\n\n" + t[m.end():]
p.write_text(t2, encoding="utf-8", errors="replace")
print("OK: patched probe_esp() to accept 'Connected to ESP' output in frozen Windows (backup:", bak.name + ")")
