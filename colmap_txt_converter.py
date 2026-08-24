"""
COLMAP BIN -> TXT Converter GUI
--------------------------------
A small Tkinter tool that wraps:

    COLMAP.bat model_converter --input_path <folder> --output_path <folder> --output_type TXT

Paste (or browse to) a sparse-model folder containing cameras.bin, images.bin
and points3D.bin, then click "Convert". The resulting cameras.txt, images.txt
and points3D.txt are written into the SAME folder, alongside the .bin files.

Requires Python 3.8+ (Tkinter ships with the standard Windows installer).
Run with:   python colmap_txt_converter.py
"""

import os
import subprocess
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext

DEFAULT_COLMAP_PATH = r"C:\Program Files\colmap-x64-windows-cuda\COLMAP.bat"
REQUIRED_FILES = ["cameras.bin", "images.bin", "points3D.bin"]


class ColmapConverterApp:
    def __init__(self, root):
        self.root = root
        root.title("COLMAP BIN → TXT Converter")
        root.geometry("640x420")
        root.resizable(True, True)

        pad = {"padx": 10, "pady": 6}

        # --- COLMAP.bat path ---
        tk.Label(root, text="COLMAP.bat location:").grid(row=0, column=0, sticky="w", **pad)
        self.colmap_path_var = tk.StringVar(value=DEFAULT_COLMAP_PATH)
        tk.Entry(root, textvariable=self.colmap_path_var, width=70).grid(
            row=1, column=0, columnspan=2, sticky="we", padx=10
        )
        tk.Button(root, text="Browse...", command=self.browse_colmap).grid(
            row=1, column=2, padx=10
        )

        # --- Source sparse folder ---
        tk.Label(root, text="Sparse model folder (contains cameras.bin / images.bin / points3D.bin):").grid(
            row=2, column=0, columnspan=3, sticky="w", padx=10, pady=(14, 2)
        )
        self.folder_var = tk.StringVar()
        self.folder_entry = tk.Entry(root, textvariable=self.folder_var, width=70)
        self.folder_entry.grid(row=3, column=0, columnspan=2, sticky="we", padx=10)
        tk.Button(root, text="Browse...", command=self.browse_folder).grid(
            row=3, column=2, padx=10
        )

        # --- Start button ---
        self.start_btn = tk.Button(
            root, text="Convert to TXT", command=self.start_conversion,
            bg="#2d7d46", fg="white", height=2
        )
        self.start_btn.grid(row=4, column=0, columnspan=3, sticky="we", padx=10, pady=14)

        # --- Log output ---
        tk.Label(root, text="Log:").grid(row=5, column=0, sticky="w", padx=10)
        self.log_box = scrolledtext.ScrolledText(root, height=14, state="disabled", bg="#1e1e1e", fg="#d4d4d4")
        self.log_box.grid(row=6, column=0, columnspan=3, sticky="nsew", padx=10, pady=(2, 10))

        root.grid_rowconfigure(6, weight=1)
        root.grid_columnconfigure(0, weight=1)
        root.grid_columnconfigure(1, weight=1)

    # ---------- UI helpers ----------

    def browse_colmap(self):
        path = filedialog.askopenfilename(
            title="Locate COLMAP.bat",
            filetypes=[("Batch file", "*.bat"), ("All files", "*.*")],
        )
        if path:
            self.colmap_path_var.set(path)

    def browse_folder(self):
        path = filedialog.askdirectory(title="Select sparse model folder")
        if path:
            self.folder_var.set(path)

    def log(self, text):
        self.log_box.configure(state="normal")
        self.log_box.insert(tk.END, text + "\n")
        self.log_box.see(tk.END)
        self.log_box.configure(state="disabled")

    def clear_log(self):
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", tk.END)
        self.log_box.configure(state="disabled")

    # ---------- Conversion logic ----------

    def start_conversion(self):
        colmap_path = self.colmap_path_var.get().strip().strip('"')
        folder = self.folder_var.get().strip().strip('"')

        if not colmap_path or not os.path.isfile(colmap_path):
            messagebox.showerror("COLMAP not found", f"Can't find COLMAP.bat at:\n{colmap_path}")
            return

        if not folder or not os.path.isdir(folder):
            messagebox.showerror("Folder not found", f"Can't find folder:\n{folder}")
            return

        missing = [f for f in REQUIRED_FILES if not os.path.isfile(os.path.join(folder, f))]
        if missing:
            proceed = messagebox.askyesno(
                "Missing files",
                f"These expected files are missing from the folder:\n"
                f"{', '.join(missing)}\n\nRun anyway?"
            )
            if not proceed:
                return

        self.start_btn.configure(state="disabled", text="Converting...")
        self.clear_log()
        self.log(f"COLMAP: {colmap_path}")
        self.log(f"Folder: {folder}")
        self.log("Running model_converter...\n")

        # Run in a background thread so the UI doesn't freeze
        thread = threading.Thread(target=self.run_colmap, args=(colmap_path, folder), daemon=True)
        thread.start()

    def run_colmap(self, colmap_path, folder):
        cmd = [
            colmap_path,
            "model_converter",
            "--input_path", folder,
            "--output_path", folder,
            "--output_type", "TXT",
        ]
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            for line in process.stdout:
                self.root.after(0, self.log, line.rstrip())
            process.wait()

            if process.returncode == 0:
                produced = [f.replace(".bin", ".txt") for f in REQUIRED_FILES
                            if os.path.isfile(os.path.join(folder, f.replace(".bin", ".txt")))]
                self.root.after(0, self.log, f"\nDone. Files written: {', '.join(produced) or '(none found?)'}")
                self.root.after(0, lambda: messagebox.showinfo("Success", "Conversion complete."))
            else:
                self.root.after(0, self.log, f"\nCOLMAP exited with code {process.returncode}")
                self.root.after(0, lambda: messagebox.showerror(
                    "Conversion failed", f"COLMAP exited with code {process.returncode}. Check the log."
                ))
        except Exception as e:
            self.root.after(0, self.log, f"\nError: {e}")
            self.root.after(0, lambda: messagebox.showerror("Error", str(e)))
        finally:
            self.root.after(0, lambda: self.start_btn.configure(state="normal", text="Convert to TXT"))


if __name__ == "__main__":
    root = tk.Tk()
    app = ColmapConverterApp(root)
    root.mainloop()
