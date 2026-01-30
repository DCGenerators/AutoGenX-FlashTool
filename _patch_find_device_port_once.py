import re
from pathlib import Path

p = Path("autogen_flash.py")
t = p.read_text(encoding="utf-8", errors="replace")

# Replace find_device_port() entirely (it currently probes the same COM twice via two loops)
pat = re.compile(r"(?ms)^def find_device_port\(\)\s*->\s*str:\s*\n.*?\n(?=^#\s*-{5,}|^def\s+run_esptool\()", re.M)
m = pat.search(t)
if not m:
    raise SystemExit("PATCH FAILED: could not locate find_device_port() block")

bak = p.with_suffix(p.suffix + ".pre_find_device_port_fix.bak")
if not bak.exists():
    bak.write_text(t, encoding="utf-8", errors="replace")

replacement = """def find_device_port() -> str:
    ports = list_ports()
    if not ports:
        die("No serial ports detected. Plug AutoGen X via USB data cable.")

    print("🔎 Detected ports:")
    for dev, desc in ports:
        print(f"  - {dev}  ({desc})")

    def score(dev: str, desc: str) -> int:
        d = (desc or "").lower()
        v = (dev or "").lower()
        # Lower score = higher priority
        if ("cp210" in d) or ("silicon labs" in d) or ("slab" in d):
            return 0
        if ("usb to uart" in d) or ("uart" in d):
            return 1
        if ("usbserial" in v) or ("usb" in v):
            return 2
        return 10

    # Probe each detected port ONCE (prevents COM port being left busy by repeated probes)
    candidates = sorted(ports, key=lambda x: score(x[0], x[1]))
    for dev, desc in candidates:
        print(f"\\n🧪 Probing {dev} ...")
        if run_esptool(["--chip","auto","--port",dev,"--baud","115200","flash-id"], silent=True) == 0:
            print(f"✅ Found ESP device on {dev}\\n")
            return dev

    die("No ESP device found on detected ports.")
"""

t2 = t[:m.start()] + replacement + t[m.end():]
p.write_text(t2, encoding="utf-8", errors="replace")
print("OK: patched find_device_port() to probe each COM once (backup:", bak.name + ")")
