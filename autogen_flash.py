import json
import os
import sys
import time
import subprocess

def die(msg, code=1):
    print("\n" + "="*60)
    print("❌ " + str(msg))
    print("="*60 + "\n")
    raise SystemExit(code)

def is_frozen():
    return getattr(sys, "frozen", False)

def app_dir():
    """
    Where the user runs the tool from.
    - In PyInstaller EXE: folder containing the EXE
    - In normal python: folder containing this script
    """
    if is_frozen():
        return os.path.dirname(sys.executable)
    return os.path.abspath(os.path.dirname(__file__))

def bundled_dir():
    """
    Where PyInstaller stores bundled resources at runtime.
    """
    return getattr(sys, "_MEIPASS", app_dir())

def load_cfg():
    # Prefer version.json next to the tool (user-editable), else fall back to bundled
    p1 = os.path.join(app_dir(), "version.json")
    p2 = os.path.join(bundled_dir(), "version.json")
    path = p1 if os.path.exists(p1) else p2
    if not os.path.exists(path):
        die("Missing version.json (next to tool or bundled).")
    with open(path, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    return cfg

def run_esptool(args, silent=False):
    cmd = [sys.executable, "-m", "esptool"] + args
    if silent:
        return subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode
    print("▶️", " ".join(cmd))
    return subprocess.run(cmd).returncode

def list_ports_ranked():
    try:
        from serial.tools import list_ports
    except Exception:
        die("pyserial missing in this build.")
    ports = list(list_ports.comports())
    if not ports:
        return []

    preferred_vids = {0x303A, 0x10C4, 0x1A86, 0x0403}  # Espressif, CP210x, CH340, FTDI

    def score(p):
        s = 0
        if p.vid in preferred_vids:
            s += 50
        desc = (p.description or "").lower()
        dev  = (p.device or "").lower()
        hwid = (p.hwid or "").lower()

        if "usb" in desc or "usb" in hwid: s += 8
        if "uart" in desc or "serial" in desc: s += 8
        if "cp210" in desc or "silabs" in desc: s += 12
        if "ch340" in desc or "wch" in desc: s += 12
        if "ftdi" in desc: s += 10
        if "espressif" in desc: s += 15
        if "usbmodem" in dev or "usbserial" in dev: s += 10
        return -s

    ports.sort(key=score)
    return ports

def probe_esp_port(port: str) -> bool:
    rc = run_esptool(["--port", port, "chip_id"], silent=True)
    return rc == 0

def find_device_port():
    ports = list_ports_ranked()
    if not ports:
        die("No serial ports detected. Plug controller via USB (data cable).")

    print("\n🔎 Detected ports:")
    for p in ports:
        print(f"  - {p.device}  ({p.description})")
    print()

    for p in ports:
        print(f"🧪 Probing {p.device} ...")
        if probe_esp_port(p.device):
            print(f"✅ Found ESP device on {p.device}\n")
            return p.device

    die("Ports detected, but none responded as an ESP device.\n"
        "Possible causes: driver missing, charge-only cable, or auto-boot wiring missing.")

def resolve_firmware_path(cfg, firmware_override=None):
    """
    Priority:
    1) firmware_override (GUI selected file or CLI arg)
    2) firmware.bin next to the tool (external per-customer file)
    3) bundled firmware.bin (legacy embedded)
    """
    if firmware_override:
        if os.path.exists(firmware_override):
            return os.path.abspath(firmware_override)
        die(f"Selected firmware not found: {firmware_override}")

    fw_name = cfg.get("firmware", "firmware.bin")

    # External firmware sitting next to the EXE/app-run folder
    p_external = os.path.join(app_dir(), fw_name)
    if os.path.exists(p_external):
        return p_external

    # Bundled fallback (if you still embed it)
    p_bundled = os.path.join(bundled_dir(), fw_name)
    if os.path.exists(p_bundled):
        return p_bundled

    die(f"Firmware not found.\nExpected either:\n- {p_external}\n- or bundled {fw_name}\n")

def flash(cfg, firmware_override=None):
    offset = str(cfg.get("offset", "0x10000"))          # OTA/app default
    erase  = bool(cfg.get("erase", False))              # safe default
    baud_list = cfg.get("baud_try", [921600, 460800, 230400, 115200])

    fw_path = resolve_firmware_path(cfg, firmware_override)
    port = find_device_port()

    print(f"📦 Target: {cfg.get('name','AutoGen')}  Version: {cfg.get('version','')}")
    print(f"📄 Firmware: {fw_path}")
    print(f"🧠 Mode: offset={offset} erase={erase}")
    print()

    if erase:
        for b in baud_list:
            print(f"🧽 Erasing flash @ baud {b} ...")
            rc = run_esptool(["--port", port, "--baud", str(b), "erase_flash"], silent=False)
            if rc == 0:
                break
        else:
            die("Erase failed on all baud rates.")

    for b in baud_list:
        print(f"⚡ Flashing @ baud {b} ...")
        rc = run_esptool([
            "--port", port,
            "--baud", str(b),
            "write_flash", "-z",
            offset, fw_path
        ], silent=False)

        if rc == 0:
            print("\n✅ Flash successful.\n")
            return

        print("⚠️ Flash failed at this baud, retrying lower...\n")
        time.sleep(0.5)

    die("Flashing failed on all baud rates.")

def main(firmware_override=None):
    print("======================================")
    print("   AutoGen X USB Flash Tool")
    print("======================================\n")
    cfg = load_cfg()
    if "baud_try" not in cfg:
        cfg["baud_try"] = [cfg.get("baud", 921600), 460800, 230400, 115200]

    # Support drag-drop on Windows: EXE <firmware.bin>
    if firmware_override is None and len(sys.argv) >= 2:
        firmware_override = sys.argv[1]

    flash(cfg, firmware_override=firmware_override)

    try:
        input("Press Enter to close...")
    except Exception:
        pass

if __name__ == "__main__":
    main()
