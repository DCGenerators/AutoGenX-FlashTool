import json
import os
import sys
import time
import subprocess

# --------------------------
# Helpers
# --------------------------
def die(msg, code=1):
    print("\n" + "="*60)
    print("❌ " + msg)
    print("="*60 + "\n")
    raise SystemExit(code)

def resource_path(rel_path: str) -> str:
    """
    PyInstaller-safe path resolver.
    """
    base = getattr(sys, "_MEIPASS", os.path.abspath(os.path.dirname(__file__)))
    return os.path.join(base, rel_path)

def run_esptool(args, silent=False):
    """
    Runs esptool as a module so it works in normal python + in PyInstaller EXE.
    """
    cmd = [sys.executable, "-m", "esptool"] + args
    if silent:
        return subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode
    print("▶️", " ".join(cmd))
    return subprocess.run(cmd).returncode

def load_cfg():
    cfg_file = resource_path("version.json")
    if not os.path.exists(cfg_file):
        die("Missing version.json рядом με το εργαλείο (next to tool).")
    with open(cfg_file, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    # Basic sanity
    if "firmware" not in cfg:
        die("version.json missing 'firmware' field.")
    return cfg

def list_ports_ranked():
    try:
        from serial.tools import list_ports
    except Exception:
        die("Missing serial support. (pyserial not present in build).")

    ports = list(list_ports.comports())
    if not ports:
        return []

    # Prefer likely USB-UART / Espressif / CDC ports
    preferred_vids = {0x303A, 0x10C4, 0x1A86, 0x0403}  # Espressif, CP210x, CH340, FTDI

    def score(p):
        s = 0
        if p.vid in preferred_vids:
            s += 50
        desc = (p.description or "").lower()
        dev  = (p.device or "").lower()
        hwid = (p.hwid or "").lower()

        # common patterns
        if "usb" in desc or "usb" in hwid: s += 8
        if "uart" in desc or "serial" in desc: s += 8
        if "cp210" in desc or "silabs" in desc: s += 12
        if "ch340" in desc or "wch" in desc: s += 12
        if "ftdi" in desc: s += 10
        if "espressif" in desc: s += 15
        if "usbmodem" in dev or "usbserial" in dev: s += 10  # mac patterns
        return -s

    ports.sort(key=score)
    return ports

def probe_esp_port(port: str) -> bool:
    # chip_id is read-only; good probe
    rc = run_esptool(["--port", port, "chip_id"], silent=True)
    return rc == 0

def find_device_port():
    ports = list_ports_ranked()
    if not ports:
        die("No serial ports detected. Plug controller via USB (data cable) and retry.\n"
            "If on Windows, you may need CP210x/CH340 drivers.")

    print("\n🔎 Detected ports:")
    for p in ports:
        print(f"  - {p.device}  ({p.description})")
    print()

    # Probe in ranked order
    for p in ports:
        print(f"🧪 Probing {p.device} ...")
        if probe_esp_port(p.device):
            print(f"✅ Found ESP device on {p.device}\n")
            return p.device

    die("Ports detected, but none responded as an ESP device.\n"
        "Possible causes:\n"
        " - Wrong USB driver (Windows)\n"
        " - Charge-only USB cable\n"
        " - Board not presenting serial port / boot auto-reset wiring missing\n")

def flash(cfg):
    fw_name = cfg.get("firmware", "firmware.bin")
    fw_path = resource_path(fw_name)
    if not os.path.exists(fw_path):
        die(f"Missing firmware file: {fw_name}")

    offset = str(cfg.get("offset", "0x10000"))       # OTA-style default
    erase  = bool(cfg.get("erase", False))           # safe default: False
    baud_list = cfg.get("baud_try", [921600, 460800, 230400, 115200])

    port = find_device_port()

    print(f"📦 Target: {cfg.get('name','AutoGen')}  Version: {cfg.get('version','')}")
    print(f"🧠 Mode: offset={offset} erase={erase}")
    print()

    # Optional erase (OFF by default for OTA/app bin)
    if erase:
        for b in baud_list:
            print(f"🧽 Erasing flash @ baud {b} ...")
            rc = run_esptool(["--port", port, "--baud", str(b), "erase_flash"], silent=False)
            if rc == 0:
                break
        else:
            die("Erase failed on all baud rates.")

    # Write with baud retries
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

    die("Flashing failed on all baud rates.\n"
        "Try a different USB port/cable, or install the correct USB driver.")

def main():
    print("======================================")
    print("   AutoGen X USB Flash Tool")
    print("======================================\n")
    cfg = load_cfg()

    # Provide default baud_try if not present
    if "baud_try" not in cfg:
        cfg["baud_try"] = [cfg.get("baud", 921600), 460800, 230400, 115200]

    flash(cfg)

    print("You can now unplug/replug the controller.\n")
    try:
        input("Press Enter to close...")
    except Exception:
        pass

if __name__ == "__main__":
    main()
