from pathlib import Path
import re

p = Path("autogen_flash.py")
t = p.read_text(encoding="utf-8", errors="replace")

bak = p.with_suffix(p.suffix + ".baseline_before_consolidated_fix.bak")
if not bak.exists():
    bak.write_text(t, encoding="utf-8", errors="replace")

# Ensure module cache exists
if "_CACHED_PORT" not in t:
    m = re.search(r"(?m)^(import .*|from .* import .*)\n(?:import .*|from .* import .*\n)*", t)
    if not m:
        raise SystemExit("PATCH FAILED: could not find import block")
    t = t[:m.end()] + "\n# Port cache (prevents double-probing in frozen builds)\n_CACHED_PORT = None\n\n" + t[m.end():]

# Replace find_device_port() block (from def to the next section header / next def run_esptool)
fd_pat = re.compile(r"(?ms)^def find_device_port\(\)\s*->\s*str:\s*\n.*?\n(?=^#\s*-{5,}|^def\s+run_esptool\()", re.M)
m = fd_pat.search(t)
if not m:
    raise SystemExit("PATCH FAILED: find_device_port() not found")

find_device_port_block = """def find_device_port() -> str:
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

    candidates = sorted(ports, key=lambda x: score(x[0], x[1]))
    for dev, desc in candidates:
        print(f"\\n🧪 Probing {dev} ...")
        if probe_esp(dev):
            print(f"✅ Found ESP device on {dev}\\n")
            _CACHED_PORT = dev
            return dev

    die("No ESP device found on detected ports.")
"""
t = t[:m.start()] + find_device_port_block + "\n" + t[m.end():]

# Patch run_esptool(): ensure non-frozen uses python -m esptool, frozen-Windows uses in-process capture
# We'll replace ONLY the command builder section inside run_esptool after the CREATE_NO_WINDOW line.
re_run = re.compile(r"(?ms)^def run_esptool\(args, silent=False\) -> int:.*?^def probe_esp\(", re.M)
m2 = re_run.search(t)
if not m2:
    raise SystemExit("PATCH FAILED: run_esptool->probe_esp boundary not found")

chunk = t[m2.start():m2.end()]
# Find the point right after CREATE_NO_WINDOW line
m3 = re.search(r"(?m)^\s*CREATE_NO_WINDOW\s*=.*\n", chunk)
if not m3:
    raise SystemExit("PATCH FAILED: CREATE_NO_WINDOW line not found in run_esptool")

head = chunk[:m3.end()]
tail = chunk[m3.end():]

# Remove any existing cmd-builder up to the 'try:' inside run_esptool
m_try = re.search(r"(?m)^\s*try:\s*\n", tail)
if not m_try:
    raise SystemExit("PATCH FAILED: try: not found in run_esptool")

cmd_builder = """\n    # Windows frozen: run esptool in-process (no missing esptool.exe; no popup windows)
    if is_frozen() and os.name == "nt":
        try:
            import esptool, io, contextlib
            buf = io.StringIO()
            if silent:
                with open(os.devnull, "w") as dn:
                    with contextlib.redirect_stdout(dn), contextlib.redirect_stderr(dn):
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

    # Not frozen: run esptool via current python environment (stable on Windows)
    cmd = [sys.executable, "-m", "esptool"] + list(args)
    creationflags = CREATE_NO_WINDOW if os.name == "nt" else 0
"""

tail2 = cmd_builder + tail[m_try.start():]  # keep original subprocess.run try/except block

new_chunk = head + tail2
t = t[:m2.start()] + new_chunk + t[m2.end():]

# Replace probe_esp() with a deterministic version:
probe_pat = re.compile(r"(?ms)^def probe_esp\(port: str\) -> bool:.*?\n(?=^def resolve_firmware_path\()", re.M)
m4 = probe_pat.search(t)
if not m4:
    raise SystemExit("PATCH FAILED: probe_esp() not found")

probe_block = """def probe_esp(port: str) -> bool:
    \"\"\"Probe the ESP reliably across normal python and frozen Windows.\"\"\"
    import os

    # In frozen Windows, run_esptool already handles in-process + output markers.
    rc = run_esptool(["--chip","auto","--port", port, "--baud","115200","flash-id"], silent=True)
    if rc == 0:
        return True

    # One non-silent retry for visibility/markers in frozen path
    rc2 = run_esptool(["--chip","auto","--port", port, "--baud","115200","chip-id"], silent=False)
    return rc2 == 0
"""
t = t[:m4.start()] + probe_block + "\n\n" + t[m4.end():]

# Remove any DEBUG_PROBE lines that may exist from previous injections
t = re.sub(r"(?m)^\s*print\('DEBUG_PROBE:.*\)\s*\n", "", t)
t = re.sub(r"(?m)^\s*print\(f'DEBUG_PROBE:.*\)\s*\n", "", t)

p.write_text(t, encoding="utf-8", errors="replace")
print("OK: applied consolidated fix to autogen_flash.py (backup:", bak.name + ")")
