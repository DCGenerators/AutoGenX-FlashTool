from pathlib import Path
import re

p = Path("autogen_flash.py")
t = p.read_text(encoding="utf-8", errors="replace")

# Add debug prints inside probe_esp and find_device_port (only if not already present)
if "DEBUG_PROBE:" in t:
    print("DEBUG already present")
    raise SystemExit(0)

def inject_after(pattern, insert):
    global t
    m = re.search(pattern, t, flags=re.M)
    if not m:
        raise SystemExit("INJECT FAILED: " + pattern)
    i = m.end()
    t = t[:i] + insert + t[i:]

bak = p.with_suffix(p.suffix + ".pre_debug_probe.bak")
if not bak.exists():
    bak.write_text(t, encoding="utf-8", errors="replace")

# Inside probe_esp(): right after def line
inject_after(r"^def probe_esp\(port: str\) -> bool:\n", "    print(f'DEBUG_PROBE: probe_esp({port}) frozen={is_frozen()} os={__import__(\"os\").name}')\n")

# In frozen branch: right before checking markers, dump first 120 chars of captured output
inject_after(r"out\s*=\s*buf\.getvalue\(\)\n", "            print('DEBUG_PROBE: captured_out_head=', repr(out[:200]))\n            print('DEBUG_PROBE: rc=', rc)\n")

# In find_device_port(): before returning dev on success
inject_after(r"print\(f\"✅ Found ESP device on \{dev\}\\n\"\)\n\s*return dev\n", "        print('DEBUG_PROBE: find_device_port returning', dev)\n")

p.write_text(t, encoding="utf-8", errors="replace")
print("OK: injected DEBUG_PROBE prints (backup:", bak.name + ")")
