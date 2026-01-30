import re
from pathlib import Path

p = Path("autogen_flash.py")
t = p.read_text(encoding="utf-8", errors="replace")

bak = p.with_suffix(p.suffix + ".pre_find_cache_only.bak")
if not bak.exists():
    bak.write_text(t, encoding="utf-8", errors="replace")

# Insert cache if missing
if "_CACHED_PORT" not in t:
    m = re.search(r"(?m)^(import .*|from .* import .*)\n(?:import .*|from .* import .*\n)*", t)
    if not m:
        raise SystemExit("PATCH FAILED: import block not found")
    t = t[:m.end()] + "\n# Port cache\n_CACHED_PORT = None\n\n" + t[m.end():]

fd_pat = re.compile(r"(?ms)^def find_device_port\(\)\s*->\s*str:\s*\n.*?\n(?=^#\s*-{5,}|^def\s+run_esptool\()", re.M)
m = fd_pat.search(t)
if not m:
    raise SystemExit("PATCH FAILED: find_device_port not found")

replacement = """def find_device_port() -> str:
    global _CACHED_PORT
    if _CACHED_PORT:
        print(f"ℹ️ Using cached port: {_CACHED_PORT}")
        return _CACHED_PORT

    ports = list_ports()
    if not ports:
        die("No serial ports detected. Plug AutoGen X via USB data cable.")

    print("🔎 Detected ports:")
    for dev, desc in ports:
        print(f"  - {dev}  ({desc})")

    # Prefer CP210x/SLAB, then probe each port ONCE
    def score(dev: str, desc: str) -> int:
        d = (desc or "").lower()
        v = (dev or "").lower()
        if ("cp210" in d) or ("silicon labs" in d) or ("slab" in d):
            return 0
        if ("usb to uart" in d) or ("uart" in d):
            return 1
        if ("usbserial" in v) or ("usb" in v):
            return 2
        return 10

    for dev, desc in sorted(ports, key=lambda x: score(x[0], x[1])):
        print(f"\\n🧪 Probing {dev} ...")
        if probe_esp(dev):
            print(f"✅ Found ESP device on {dev}\\n")
            _CACHED_PORT = dev
            return dev

    die("No ESP device found on detected ports.")
"""

t2 = t[:m.start()] + replacement + "\n" + t[m.end():]
p.write_text(t2, encoding="utf-8", errors="replace")
print("OK: patched find_device_port cache (backup:", bak.name + ")")
