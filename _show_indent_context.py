import re
import py_compile

path="autogen_flash.py"

try:
    py_compile.compile(path, doraise=True)
except Exception as e:
    line = getattr(e, "lineno", None)
    if not line:
        m = re.search(r"line (\d+)", str(e))
        line = int(m.group(1)) if m else 1

    start = max(1, line - 40)
    end = line + 40

    with open(path, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()

    for i in range(start, min(end, len(lines)) + 1):
        prefix = ">>" if i == line else "  "
        print(f"{prefix}{i:6d}: {lines[i-1].rstrip()}")

    raise
