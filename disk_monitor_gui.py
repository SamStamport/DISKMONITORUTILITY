"""
disk_monitor_gui.py

Simple GUI front-end for the disk monitor utility (Windows).

- Single-file GUI design using Tkinter (no external GUI deps).
- Uses a background thread to sample per-PID IO deltas (avoids double-counting).
- Exports JSON and shows top N processes by IO.

Requires:
    Python 3.12 on Windows (includes Tkinter), psutil installed:
    pip install psutil

Run (for testing before packaging):
    python disk_monitor_gui.py
"""

from __future__ import annotations
import json
import threading
import time
import queue
from collections import defaultdict
from typing import Dict, Tuple

import psutil
import tkinter as tk
from tkinter import ttk, filedialog, messagebox


SampleResult = Dict[Tuple[int, str], Dict[str, float]]


class DiskMonitorWorker(threading.Thread):
    """
    Background worker sampling psutil and sending aggregated results to a queue.
    """

    def __init__(self, duration: int, interval: float, top_n: int, out_queue: "queue.Queue[SampleResult]"):
        super().__init__(daemon=True)
        self.duration = duration
        self.interval = interval
        self.top_n = top_n
        self.out_queue = out_queue
        self._stop_event = threading.Event()

    def stop(self) -> None:
        self._stop_event.set()

    def stopped(self) -> bool:
        return self._stop_event.is_set()

    def run(self) -> None:
        """
        Collect per-interval IO deltas for 'duration' seconds and put the totals in out_queue.
        """
        prev_io: Dict[int, Tuple[int, int]] = {}
        totals: Dict[Tuple[int, str], Dict[str, float]] = defaultdict(lambda: {'read_bytes': 0.0, 'write_bytes': 0.0})
        end_time = time.time() + self.duration

        while time.time() < end_time and not self.stopped():
            for proc in psutil.process_iter(['pid', 'name']):
                pid = proc.info.get('pid')
                name = proc.info.get('name') or f"pid:{pid}"
                try:
                    io = proc.io_counters()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

                read = getattr(io, 'read_bytes', 0)
                write = getattr(io, 'write_bytes', 0)

                prev = prev_io.get(pid)
                if prev is None:
                    prev_io[pid] = (read, write)
                    continue

                delta_read = max(0, read - prev[0])
                delta_write = max(0, write - prev[1])

                key = (pid, name)
                totals[key]['read_bytes'] += delta_read
                totals[key]['write_bytes'] += delta_write

                prev_io[pid] = (read, write)

            time.sleep(self.interval)

        # Send final aggregated results (top N)
        # Convert to simple dict for transfer
        out: SampleResult = {}
        for (pid, name), io in totals.items():
            out[(pid, name)] = {'read_bytes': io['read_bytes'], 'write_bytes': io['write_bytes']}
        self.out_queue.put(out)


class DiskMonitorGUI:
    """
    Tkinter GUI application for the disk monitor.
    """

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Disk Monitor")
        self.root.geometry("760x480")

        self._build_controls()
        self._build_table()

        self.worker: DiskMonitorWorker | None = None
        self.result_queue: "queue.Queue[SampleResult]" = queue.Queue()
        self.root.after(500, self._periodic_poll)

    def _build_controls(self) -> None:
        frm = ttk.Frame(self.root, padding=8)
        frm.pack(fill=tk.X)

        ttk.Label(frm, text="Duration (s):").grid(row=0, column=0, sticky=tk.W)
        self.duration_var = tk.IntVar(value=30)
        ttk.Entry(frm, width=8, textvariable=self.duration_var).grid(row=0, column=1, sticky=tk.W, padx=(0, 12))

        ttk.Label(frm, text="Interval (s):").grid(row=0, column=2, sticky=tk.W)
        self.interval_var = tk.DoubleVar(value=1.0)
        ttk.Entry(frm, width=8, textvariable=self.interval_var).grid(row=0, column=3, sticky=tk.W, padx=(0, 12))

        ttk.Label(frm, text="Top N:").grid(row=0, column=4, sticky=tk.W)
        self.top_var = tk.IntVar(value=15)
        ttk.Entry(frm, width=6, textvariable=self.top_var).grid(row=0, column=5, sticky=tk.W, padx=(0, 12))

        self.start_button = ttk.Button(frm, text="Start", command=self.start_monitor)
        self.start_button.grid(row=0, column=6, padx=(6, 0))
        self.stop_button = ttk.Button(frm, text="Stop", command=self.stop_monitor, state=tk.DISABLED)
        self.stop_button.grid(row=0, column=7, padx=(6, 0))

        self.export_button = ttk.Button(frm, text="Export JSON", command=self.export_json, state=tk.DISABLED)
        self.export_button.grid(row=0, column=8, padx=(6, 0))

        for i in range(9):
            frm.grid_columnconfigure(i, weight=0)

    def _build_table(self) -> None:
        cols = ("pid", "name", "read_mb", "write_mb", "total_mb")
        self.tree = ttk.Treeview(self.root, columns=cols, show="headings", selectmode="browse")
        self.tree.heading("pid", text="PID")
        self.tree.heading("name", text="Process")
        self.tree.heading("read_mb", text="Read (MB)")
        self.tree.heading("write_mb", text="Write (MB)")
        self.tree.heading("total_mb", text="Total (MB)")

        self.tree.column("pid", width=60, anchor=tk.CENTER)
        self.tree.column("name", width=340)
        self.tree.column("read_mb", width=110, anchor=tk.E)
        self.tree.column("write_mb", width=110, anchor=tk.E)
        self.tree.column("total_mb", width=110, anchor=tk.E)

        vsb = ttk.Scrollbar(self.root, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=vsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        self.status_var = tk.StringVar(value="Idle")
        ttk.Label(self.root, textvariable=self.status_var).pack(anchor=tk.W, padx=8, pady=(0, 8))

    def start_monitor(self) -> None:
        if self.worker and self.worker.is_alive():
            messagebox.showinfo("Disk Monitor", "Monitoring already in progress.")
            return

        duration = max(1, int(self.duration_var.get()))
        interval = max(0.1, float(self.interval_var.get()))
        top_n = max(1, int(self.top_var.get()))
        self.status_var.set("Starting...")
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.export_button.config(state=tk.DISABLED)
        self.tree.delete(*self.tree.get_children())

        self.result_queue = queue.Queue()
        self.worker = DiskMonitorWorker(duration=duration, interval=interval, top_n=top_n, out_queue=self.result_queue)
        self.worker.start()
        self.status_var.set(f"Monitoring for {duration}s (interval {interval}s)...")

    def stop_monitor(self) -> None:
        if self.worker and self.worker.is_alive():
            self.worker.stop()
            self.status_var.set("Stopping...")
            self.stop_button.config(state=tk.DISABLED)

    def _periodic_poll(self) -> None:
        """
        Poll for results and update the table when available.
        """
        try:
            result = self.result_queue.get_nowait()
        except queue.Empty:
            self.root.after(500, self._periodic_poll)
            return

        # Convert result mapping to sorted rows
        rows = []
        for (pid, name), io in result.items():
            read_mb = io['read_bytes'] / (1024 * 1024)
            write_mb = io['write_bytes'] / (1024 * 1024)
            total_mb = read_mb + write_mb
            rows.append((pid, name, read_mb, write_mb, total_mb))

        rows.sort(key=lambda r: r[4], reverse=True)
        top_n = self.top_var.get()
        displayed = rows[:top_n]

        for pid, name, read_mb, write_mb, total_mb in displayed:
            self.tree.insert("", tk.END, values=(pid, name, f"{read_mb:.2f}", f"{write_mb:.2f}", f"{total_mb:.2f}"))

        self.status_var.set(f"Done — displayed top {len(displayed)}")
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.export_button.config(state=tk.NORMAL)

        # Keep last result for export
        self._last_result = displayed
        self.root.after(500, self._periodic_poll)

    def export_json(self) -> None:
        try:
            data = []
            for pid, name, read_mb, write_mb, total_mb in getattr(self, "_last_result", []):
                data.append({
                    "pid": pid,
                    "name": name,
                    "read_mb": read_mb,
                    "write_mb": write_mb,
                    "total_mb": total_mb
                })
            if not data:
                messagebox.showinfo("Export", "No data to export.")
                return
            path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON", "*.json")])
            if not path:
                return
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(data, fh, indent=2)
            messagebox.showinfo("Export", f"Exported {len(data)} rows to {path}")
        except Exception as exc:
            messagebox.showerror("Export Error", f"Failed to export: {exc}")


def main() -> None:
    root = tk.Tk()
    app = DiskMonitorGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
