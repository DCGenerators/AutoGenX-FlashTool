import re
from pathlib import Path

path = Path("autogen_flash.py")
data = path.read_text(encoding="utf-8", errors="replace").splitlines(True)

fixed = []
for ln in data:
    m = re.match(r"^([ \t]+)", ln)
    if m:
        ws = m.group(1).replace("\t", "    ")
        ln = ws + ln[len(m.group(1)):]
    fixed.append(ln)

new_text = "".join(fixed)

bak = path.with_suffix(path.suffix + ".bak")
if not bak.exists():
    bak.write_text("".join(data), encoding="utf-8", errors="replace")

path.write_text(new_text, encoding="utf-8", errors="replace")
print("OK: wrote autogen_flash.py (backup:", bak.name + ")")
