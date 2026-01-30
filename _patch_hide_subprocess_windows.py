from pathlib import Path

p = Path("autogen_flash.py")
bak = p.with_suffix(p.suffix + ".pre_startupinfo_hide_console.bak")
if not bak.exists():
    bak.write_text(p.read_text(encoding="utf-8", errors="replace"), encoding="utf-8", errors="replace")

t = p.read_text(encoding="utf-8", errors="replace").splitlines(True)

out = []
in_run = False
for line in t:
    if line.startswith("def run_esptool("):
        in_run = True
    if in_run and line.strip() == "import os, sys, subprocess":
        out.append(line)
        out.append("\n")
        out.append("    startupinfo = None\n")
        out.append("    if os.name == \"nt\":\n")
        out.append("        startupinfo = subprocess.STARTUPINFO()\n")
        out.append("        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW\n")
        out.append("        startupinfo.wShowWindow = subprocess.SW_HIDE\n")
        continue

    # add startupinfo=startupinfo to BOTH subprocess.run calls
    if in_run and "subprocess.run(" in line:
        out.append(line)
        continue

    if in_run and line.strip().startswith("creationflags=creationflags") and line.rstrip().endswith(","):
        out.append(line)
        out.append("                startupinfo=startupinfo,\n")
        continue
    if in_run and line.strip().startswith("creationflags=creationflags") and not line.rstrip().endswith(","):
        out.append(line.rstrip("\n") + ",\n")
        out.append("            startupinfo=startupinfo,\n")
        continue

    out.append(line)

p.write_text("".join(out), encoding="utf-8", errors="replace")
print("OK: run_esptool now hides subprocess windows via STARTUPINFO (backup:", bak.name + ")")
