"""Create fixed 3x3 GO patches: python braincodec/simple_pattern_generator.py."""

import math
import json
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk


def dump_yaml(config):
    # JSON scalar and flow-list notation is also valid YAML.
    return "".join(f"{key}: {json.dumps(value)}\n" for key, value in config.items())


def patch_labels(p, n):
    """P and N are the lowest coordinates of a 3x3 patch."""
    if not 1 <= p <= 8 or not 1 <= n <= 8:
        raise ValueError("A 3x3 patch must start at P=1–8 and N=1–8.")
    return " ".join(f"P{x}N{y}" for y in range(n, n + 3) for x in range(p, p + 3))


def build_config(mouse, device, patches, irradiance, nogo_p, nogo_n,
                 nogo_irradiance, duration, frequency, pulses, selection="random",
                 mode="simple_patterns"):
    if not patches:
        raise ValueError("Add at least one GO stimulus.")
    if not mouse.strip() or not device.strip():
        raise ValueError("Mouse ID and device ID are required.")
    values = (irradiance, nogo_irradiance, duration, frequency)
    if not all(math.isfinite(v) and v > 0 for v in values):
        raise ValueError("Irradiance, duration and frequency must be positive finite numbers.")
    if duration * frequency > 1000:
        raise ValueError("Pulse duration cannot exceed the pulse period (1000 / frequency).")
    if pulses < 1:
        raise ValueError("Number of pulses must be at least 1.")
    if selection not in ("random", "cycle"):
        raise ValueError("GO stimulus selection must be random or cycle.")
    if mode not in ("simple_patterns", "dmts_patterns"):
        raise ValueError("Invalid experiment mode.")
    if mode == "dmts_patterns" and len(patches) < 2:
        raise ValueError("DMTS requires at least two stimuli for non-match trials.")
    if mode == "dmts_patterns" and (duration < 5 or 1000 / frequency - duration < 5):
        raise ValueError("DMTS pulse ON and OFF durations must each be at least 5 ms.")
    names = [f"STIM{i}" for i in range(1, len(patches) + 1)]
    config = {"mouse_id": mouse.strip(), "device_id": device.strip(),
              "GO": patch_labels(*patches[0]),
              "GO irradiance (mW/mm2)": irradiance,
              "GO stimuli": names, "GO stimulus selection": selection}
    for name, coordinates in zip(names, patches):
        config[name] = patch_labels(*coordinates)
        config[f"{name} irradiance (mW/mm2)"] = irradiance
    config.update({"NOGO": patch_labels(nogo_p, nogo_n),
                   "NOGO irradiance (mW/mm2)": nogo_irradiance,
                   "Pulse duration (ms)": duration,
                   "Pulse frequency (Hz)": frequency,
                   "Number of pulses": pulses})
    if mode == "dmts_patterns":
        config["experiment_mode"] = mode
        config["DMTS stimuli"] = names
    return config


class Generator(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Simple LED pattern config generator")
        self.patches = []
        self.fields = {}
        form = ttk.Frame(self, padding=12)
        form.grid(row=0, column=0, sticky="nsew")
        defaults = [("Mouse ID", "332"), ("Device ID", "H2-190"),
                    ("GO irradiance (mW/mm2)", "2"),
                    ("NO-GO start P", "8"), ("NO-GO start N", "1"),
                    ("NO-GO irradiance (mW/mm2)", "2"),
                    ("Pulse duration (ms)", "25"), ("Pulse frequency (Hz)", "20"),
                    ("Number of pulses", "10")]
        for row, (label, default) in enumerate(defaults):
            ttk.Label(form, text=label).grid(row=row, column=0, sticky="w", pady=3)
            var = tk.StringVar(value=default)
            self.fields[label] = var
            ttk.Entry(form, textvariable=var, width=18).grid(row=row, column=1, padx=8)
        ttk.Label(form, text="All GO patches use the irradiance above.\nRandom selection allows consecutive repeats.").grid(
            row=9, column=0, columnspan=2, sticky="w", pady=10)
        self.selection = tk.StringVar(value="random")
        ttk.Label(form, text="GO stimulus selection").grid(row=13, column=0, sticky="w", pady=8)
        ttk.Combobox(form, textvariable=self.selection, values=("random", "cycle"),
                     state="readonly", width=15).grid(row=13, column=1)
        self.mode = tk.StringVar(value="simple_patterns")
        ttk.Label(form, text="Experiment mode").grid(row=14, column=0, sticky="w", pady=8)
        ttk.Combobox(form, textvariable=self.mode, values=("simple_patterns", "dmts_patterns"),
                     state="readonly", width=18).grid(row=14, column=1)
        ttk.Label(form, text="DMTS uses the STIM library; GO/NO-GO fields\nand selection above apply to classic sessions.").grid(
            row=15, column=0, columnspan=2, sticky="w", pady=8)
        self.p = tk.IntVar(value=1)
        self.n = tk.IntVar(value=8)
        controls = ttk.Frame(form)
        controls.grid(row=10, column=0, columnspan=2, sticky="ew")
        for label, var in (("Start P", self.p), ("Start N", self.n)):
            ttk.Label(controls, text=label).pack(side="left", padx=3)
            ttk.Spinbox(controls, from_=1, to=8, textvariable=var, width=4,
                        command=self.draw).pack(side="left")
        ttk.Button(controls, text="Add GO patch", command=self.add).pack(side="left", padx=8)
        self.listbox = tk.Listbox(form, height=8, width=46, exportselection=False)
        self.listbox.grid(row=11, column=0, columnspan=2, sticky="ew", pady=8)
        self.listbox.bind("<<ListboxSelect>>", self.select)
        ttk.Button(form, text="Remove selected", command=self.remove).grid(row=12, column=0)
        ttk.Button(form, text="Save YAML", command=self.save).grid(row=12, column=1)
        self.canvas = tk.Canvas(self, width=360, height=390, background="white")
        self.canvas.grid(row=0, column=1, padx=12, pady=12)
        self.canvas.bind("<Button-1>", self.click)
        self.p.trace_add("write", lambda *_: self.draw())
        self.n.trace_add("write", lambda *_: self.draw())
        self.add()

    def draw(self):
        self.canvas.delete("all")
        try:
            p, n = self.p.get(), self.n.get()
        except tk.TclError:
            return
        self.canvas.create_text(180, 15, text="Click the lowest P/N corner of a 3 × 3 patch")
        for x in range(1, 11):
            self.canvas.create_text(45 + (x - 1) * 30, 40, text=f"P{x}")
        for y in range(1, 11):
            top = 55 + (10 - y) * 30
            self.canvas.create_text(18, top + 15, text=f"N{y}")
            for x in range(1, 11):
                left = 30 + (x - 1) * 30
                active = p <= x < p + 3 and n <= y < n + 3
                self.canvas.create_rectangle(left, top, left + 30, top + 30,
                                             fill="#34a853" if active else "#eeeeee", outline="white")
        self.canvas.create_text(180, 375, text="P increases right; N increases up. Logical coordinates.")

    def click(self, event):
        if 30 <= event.x < 330 and 55 <= event.y < 355:
            self.p.set(min(8, (event.x - 30) // 30 + 1))
            self.n.set(min(8, 10 - (event.y - 55) // 30))

    def refresh(self):
        self.listbox.delete(0, tk.END)
        for i, (p, n) in enumerate(self.patches, 1):
            self.listbox.insert(tk.END, f"STIM{i}: P{p}–P{p+2}, N{n}–N{n+2}")

    def add(self):
        try:
            patch = (self.p.get(), self.n.get())
            patch_labels(*patch)
            if patch in self.patches:
                raise ValueError("This GO patch is already in the list.")
            self.patches.append(patch)
            self.refresh()
        except (ValueError, tk.TclError) as exc:
            messagebox.showerror("Invalid patch", str(exc))

    def select(self, _event):
        selection = self.listbox.curselection()
        if selection:
            p, n = self.patches[selection[0]]
            self.p.set(p)
            self.n.set(n)

    def remove(self):
        selection = self.listbox.curselection()
        if selection:
            del self.patches[selection[0]]
            self.refresh()

    def save(self):
        try:
            f = {key: var.get() for key, var in self.fields.items()}
            config = build_config(f["Mouse ID"], f["Device ID"], self.patches,
                                  float(f["GO irradiance (mW/mm2)"]),
                                  int(f["NO-GO start P"]), int(f["NO-GO start N"]),
                                  float(f["NO-GO irradiance (mW/mm2)"]),
                                  float(f["Pulse duration (ms)"]),
                                  float(f["Pulse frequency (Hz)"]), int(f["Number of pulses"]),
                                  selection=self.selection.get(), mode=self.mode.get())
        except ValueError as exc:
            messagebox.showerror("Invalid configuration", str(exc))
            return
        path = filedialog.asksaveasfilename(
            initialdir=str(Path(__file__).parent / "configurations"),
            initialfile="config_simple-patterns.yaml", defaultextension=".yaml",
            filetypes=[("YAML configuration", "*.yaml")])
        if path:
            try:
                Path(path).write_text(
                    "# Named patterns require the corresponding updated driver on PYNQ.\n"
                    + dump_yaml(config), encoding="utf-8")
            except OSError as exc:
                messagebox.showerror("Save failed", str(exc))
                return
            messagebox.showinfo("Saved", f"Saved {len(self.patches)} stimuli.\n"
                                "Install the corresponding PYNQ driver before running.")


if __name__ == "__main__":
    Generator().mainloop()
