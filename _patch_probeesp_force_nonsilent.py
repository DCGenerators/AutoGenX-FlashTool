from pathlib import Path

p = Path("autogen_flash.py")
bak = p.with_suffix(p.suffix + ".pre_probeesp_force_nonsilent.bak")
if not bak.exists():
    bak.write_text(p.read_text(encoding="utf-8", errors="replace"),
                   encoding="utf-8", errors="replace")

L = p.read_text(encoding="utf-8", errors="replace").splitlines(True)

def find_func(name):
    for i, line in enumerate(L):
        if line.startswith(f"def {name}"):
            return i
    return -1

def end_of_block(start):
    i = start + 1
    while i < len(L):
        if L[i].startswith("def ") or L[i].startswith("# ----------------"):
            return i
        i += 1
    return len(L)

s = find_func("probe_esp")
if s < 0:
    raise SystemExit("PATCH FAILED: probe_esp not found")

e = end_of_block(s)

L[s:e] = [
    "def probe_esp(port: str) -> bool:\n",
    "    \"\"\"Deterministic probe across Windows / frozen / normal.\n",
    "    Always non-silent so run_esptool can detect success markers.\n",
    "    \"\"\"\n",
    "    rc = run_esptool([\n",
    "        \"--chip\", \"auto\",\n",
    "        \"--port\", port,\n",
    "        \"--baud\", \"115200\",\n",
    "        \"flash-id\"\n",
    "    ], silent=False)\n",
    "    return rc == 0\n",
    "\n",
]

p.write_text("".join(L), encoding="utf-8", errors="replace")
print("OK: probe_esp now forces silent=False (backup:", bak.name + ")")
