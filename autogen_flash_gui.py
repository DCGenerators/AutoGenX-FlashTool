import threading
import queue
import tkinter as tk
from tkinter import ttk, messagebox
import traceback

import autogen_flash  # uses your existing logic

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("AutoGen X Flash Tool (macOS)")
        self.geometry("820x520")
        self.minsize(720, 420)

        self.q = queue.Queue()

        top = ttk.Frame(self, padding=12)
        top.pack(fill="x")

        self.status = ttk.Label(top, text="Ready. Plug controller via USB, then click Start Flash.")
        self.status.pack(side="left", fill="x", expand=True)

        self.btn = ttk.Button(top, text="Start Flash", command=self.start)
        self.btn.pack(side="right")

        sep = ttk.Separator(self)
        sep.pack(fill="x")

        body = ttk.Frame(self, padding=12)
        body.pack(fill="both", expand=True)

        self.txt = tk.Text(body, wrap="word")
        self.txt.pack(fill="both", expand=True)
        self.txt.insert("end", "AutoGen X macOS Flash Tool\n\n")
        self.txt.insert("end", "Steps:\n1) Plug AutoGen X into USB (data cable)\n2) Click Start Flash\n\n")
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
                if msg["type"] == "log":
                    self.log(msg["text"])
                elif msg["type"] == "status":
                    self.status.config(text=msg["text"])
                elif msg["type"] == "done":
                    self.btn.config(state="normal")
                    self.status.config(text="✅ Done.")
                    messagebox.showinfo("AutoGen X", "✅ Flash successful.")
                elif msg["type"] == "error":
                    self.btn.config(state="normal")
                    self.status.config(text="❌ Failed.")
                    messagebox.showerror("AutoGen X", msg["text"])
        except queue.Empty:
            pass
        self.after(120, self.pump)

    def start(self):
        self.btn.config(state="disabled")
        self.q.put({"type": "status", "text": "Flashing... do not unplug USB."})
        self.q.put({"type": "log", "text": "Starting flash...\n"})

        t = threading.Thread(target=self.worker, daemon=True)
        t.start()

    def worker(self):
        try:
            # Monkey-patch autogen_flash print output to our GUI
            orig_print = __builtins__.print

            def gui_print(*args, **kwargs):
                text = " ".join(str(a) for a in args)
                self.q.put({"type": "log", "text": text})

            __builtins__.print = gui_print

            # Run the existing tool (same behavior as CLI)
            autogen_flash.main()

            __builtins__.print = orig_print
            self.q.put({"type": "done"})
        except SystemExit as e:
            # autogen_flash uses SystemExit for clean errors
            self.q.put({"type": "error", "text": f"{e}"})
        except Exception:
            self.q.put({"type": "error", "text": traceback.format_exc()})

if __name__ == "__main__":
    App().mainloop()
