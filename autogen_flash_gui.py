import threading
import queue
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import traceback
# PYI_BOOTSTRAP_AUTOGEN_FLASH
import os, sys, importlib.util

def _import_autogen_flash():
    try:
        import autogen_flash  # normal import
        return autogen_flash
    except ModuleNotFoundError:
        # PyInstaller onefile: load bundled autogen_flash.py from _MEIPASS
        base = getattr(sys, "_MEIPASS", None)
        if not base:
            raise
        path = os.path.join(base, "autogen_flash_pyi.py")
        spec = importlib.util.spec_from_file_location("autogen_flash", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        sys.modules["autogen_flash"] = mod
        return mod

autogen_flash = _import_autogen_flash()
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("AutoGen X Flash Tool (macOS)")
        self.geometry("860x560")
        self.minsize(740, 440)

        self.q = queue.Queue()
        self.fw_path = None

        top = ttk.Frame(self, padding=12)
        top.pack(fill="x")

        self.status = ttk.Label(top, text="Select firmware, plug controller via USB, then click Start Flash.")
        self.status.pack(side="left", fill="x", expand=True)

        btns = ttk.Frame(top)
        btns.pack(side="right")

        self.btn_fw = ttk.Button(btns, text="Select Firmware", command=self.pick_firmware)
        self.btn_fw.pack(side="left", padx=(0,8))

        self.btn = ttk.Button(btns, text="Start Flash", command=self.start)
        self.btn.pack(side="left")

        sep = ttk.Separator(self)
        sep.pack(fill="x")

        body = ttk.Frame(self, padding=12)
        body.pack(fill="both", expand=True)

        self.txt = tk.Text(body, wrap="word")
        self.txt.pack(fill="both", expand=True)
        self.txt.insert("end", "AutoGen X macOS Flash Tool\n\n")
        self.txt.insert("end", "1) Click Select Firmware and choose the firmware.bin you received.\n")
        self.txt.insert("end", "2) Plug AutoGen X into USB (data cable)\n")
        self.txt.insert("end", "3) Click Start Flash\n\n")
        self.txt.configure(state="disabled")

        self.after(100, self.pump)

    def log(self, s: str):
        self.txt.configure(state="normal")
        self.txt.insert("end", s + "\n")
        self.txt.see("end")
        self.txt.configure(state="disabled")

    def pump(self):
        try:
            while True:
                msg = self.q.get_nowait()
                t = msg.get("type")
                if t == "log":
                    self.log(msg["text"])
                elif t == "status":
                    self.status.config(text=msg["text"])
                elif t == "done":
                    self.btn.config(state="normal")
                    self.btn_fw.config(state="normal")
                    self.status.config(text="✅ Done.")
                    messagebox.showinfo("AutoGen X", "✅ Flash successful.")
                elif t == "error":
                    self.btn.config(state="normal")
                    self.btn_fw.config(state="normal")
                    self.status.config(text="❌ Failed.")
                    messagebox.showerror("AutoGen X", msg["text"])
        except queue.Empty:
            pass
        self.after(120, self.pump)

    def pick_firmware(self):
        path = filedialog.askopenfilename(
            title="Select firmware.bin",
            filetypes=[("Firmware", "*.bin"), ("All files", "*.*")]
        )
        if path:
            self.fw_path = path
            self.q.put({"type":"log", "text": f"📄 Selected firmware: {self.fw_path}"})
            self.q.put({"type":"status", "text": "Firmware selected. Plug controller via USB, then click Start Flash."})

    def start(self):
        if not self.fw_path:
            messagebox.showwarning("AutoGen X", "Please select the firmware.bin first.")
            return

        self.btn.config(state="disabled")
        self.btn_fw.config(state="disabled")
        self.q.put({"type": "status", "text": "Flashing... do not unplug USB."})
        self.q.put({"type": "log", "text": "Starting flash...\n"})
        threading.Thread(target=self.worker, daemon=True).start()

    def worker(self):
        try:
            orig_print = __builtins__.print

            def gui_print(*args, **kwargs):
                text = " ".join(str(a) for a in args)
                self.q.put({"type": "log", "text": text})

            __builtins__.print = gui_print

            autogen_flash.main(firmware_override=self.fw_path)

            __builtins__.print = orig_print
            self.q.put({"type": "done"})
        except SystemExit as e:
            self.q.put({"type": "error", "text": str(e)})
        except Exception:
            self.q.put({"type": "error", "text": traceback.format_exc()})

if __name__ == "__main__":
    App().mainloop()
