import re
from pathlib import Path

p = Path("autogen_flash.py")
t = p.read_text(encoding="utf-8", errors="replace")

bak = p.with_suffix(p.suffix + ".pre_port_cache_fix.bak")
if not bak.exists():
    bak.write_text(t, encoding="utf-8", errors="replace")

# 1) Add module-global cache near the top (after imports or after emoji banner)
if "_CACHED_PORT" not in t:
    # insert after first block of imports (best-effort)
    m = re.search(r"(?m)^(import .*|from .* import .*)\n(?:import .*|from .* import .*\n)*", t)
    if not m:
        raise SystemExit("PATCH FAILED: could not find import block to insert cache")
    insert_at = m.end()
    t = t[:insert_at] + "\n# Port cache (prevents double-probing in frozen builds)\n_CACHED_PORT = None\n\n" + t[insert_at:]

# 2) Wrap find_device_port() to reuse cached port
# Replace the function signature line and immediately add cache logic after it.
# We add at start of function body:
#   global _CACHED_PORT
#   if _CACHED_PORT: return _CACHED_PORT
# And before returning a found dev: set _CACHED_PORT = dev

# a) ensure we inject global/cache early in function
t2, n1 = re.subn(
    r"(?m)^def find_device_port\(\) -> str:\n",
    "def find_device_port() -> str:\n    global _CACHED_PORT\n    if _CACHED_PORT:\n        print(f\"ℹ️ Using cached port: {_CACHED_PORT}\")\n        return _CACHED_PORT\n",
    t
)
if n1 != 1:
    raise SystemExit(f"PATCH FAILED: expected 1 find_device_port def, got {n1}")

# b) whenever we return dev on success inside find_device_port, set cache first
# (covers both old/new variants)
t3, n2 = re.subn(
    r"(?m)^\s*print\(f\"✅ Found ESP device on \{dev\}\\n\"\)\s*\n\s*(?:print\(.+\)\s*\n\s*)?return dev\s*$",
    "        print(f\"✅ Found ESP device on {dev}\\n\")\n        _CACHED_PORT = dev\n        return dev",
    t2
)
if n2 < 1:
    raise SystemExit("PATCH FAILED: could not patch return-dev block(s) in find_device_port")

p.write_text(t3, encoding="utf-8", errors="replace")
print(f"OK: added port cache (_CACHED_PORT). Patched find_device_port def:{n1} return-blocks:{n2} (backup: {bak.name})")
