import re
from pathlib import Path

p = Path("autogen_flash.py")
t = p.read_text(encoding="utf-8", errors="replace")

# Hard fix: find_device_port() MUST use probe_esp(dev) (not rc==0 on flash-id),
# because frozen/in-process esptool can connect but return nonzero for flash-id.
# Replace any: if run_esptool([... "flash-id"], silent=True) == 0:
# with:       if probe_esp(dev):

t2, n = re.subn(
    r'(?m)^\s*if\s+run_esptool\(\[\s*"--chip"\s*,\s*"auto"\s*,\s*"--port"\s*,\s*dev\s*,\s*"--baud"\s*,\s*"115200"\s*,\s*"flash-id"\s*\]\s*,\s*silent\s*=\s*True\s*\)\s*==\s*0\s*:\s*$',
    '        if probe_esp(dev):',
    t
)

if n < 1:
    raise SystemExit("PATCH FAILED: no flash-id probe line found in find_device_port()")

bak = p.with_suffix(p.suffix + ".pre_find_uses_probe_esp.bak")
if not bak.exists():
    bak.write_text(t, encoding="utf-8", errors="replace")

p.write_text(t2, encoding="utf-8", errors="replace")
print(f"OK: find_device_port now uses probe_esp(dev) (replacements: {n}) (backup: {bak.name})")
