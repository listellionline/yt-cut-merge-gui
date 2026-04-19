from __future__ import annotations

import os
import queue
import subprocess
import sys
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional

import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

from .core import JobConfig, list_video_files, process_job
from .platform_utils import default_workdir, find_ffprobe, patch_runtime_path
from .version import get_version


patch_runtime_path()


class App:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("YT Cut Merge GUI")
        self.root.geometry("1100x840")

        self.version = get_version()
        self.log_lines: list[str] = []
        self.event_queue: queue.Queue[tuple[str, object]] = queue.Queue()

        self.source_mode_var = tk.StringVar(value="url")   # url | local
        self.clip_mode_var = tk.StringVar(value="csv")     # csv | file

        self.url_var = tk.StringVar()
        self.clipfile_var = tk.StringVar()
        self.ranges_var = tk.StringVar()
        self.output_var = tk.StringVar(value="output_finale.mp4")
        self.fade_var = tk.StringVar(value="0.0")
        self.reencode_var = tk.StringVar(value="yes")
        self.source_var = tk.StringVar()
        self.browser_var = tk.StringVar()
        self.workdir_var = tk.StringVar(value=str(default_workdir()))
        self.auto_clean_var = tk.BooleanVar(value=False)
        self.dry_run_var = tk.BooleanVar(value=False)

        self.status_var = tk.StringVar(value="Pronto")
        self.progress_text_var = tk.StringVar(value="Nessuna operazione in corso")
        self.progress_value_var = tk.DoubleVar(value=0.0)

        self.url_label: Optional[ttk.Label] = None
        self.url_entry: Optional[ttk.Entry] = None

        self.source_label: Optional[ttk.Label] = None
        self.source_entry: Optional[ttk.Entry] = None
        self.source_browse_btn: Optional[ttk.Button] = None

        self.ranges_label: Optional[ttk.Label] = None
        self.ranges_entry: Optional[ttk.Entry] = None
        self.csv_example_label: Optional[ttk.Label] = None

        self.clipfile_label: Optional[ttk.Label] = None
        self.clipfile_entry: Optional[ttk.Entry] = None
        self.clipfile_browse_btn: Optional[ttk.Button] = None

        self.run_button: Optional[ttk.Button] = None
        self.video_menu: Optional[tk.Menu] = None

        self._build_ui()
        self.apply_startup_args()
        self.update_source_mode()
        self.update_clip_mode()
        self.refresh_video_list()

        self.root.after(100, self.process_ui_queue)

    def _build_ui(self) -> None:
        frm = ttk.Frame(self.root, padding=12)
        frm.pack(fill="both", expand=True)
        frm.columnconfigure(1, weight=1)

        # --- sorgente ---
        ttk.Label(frm, text="Sorgente").grid(row=0, column=0, sticky="w", pady=4)

        source_mode_frame = ttk.Frame(frm)
        source_mode_frame.grid(row=0, column=1, columnspan=2, sticky="w", pady=4)

        ttk.Radiobutton(
            source_mode_frame,
            text="URL YouTube",
            variable=self.source_mode_var,
            value="url",
            command=self.update_source_mode,
        ).pack(side="left", padx=(0, 12))

        ttk.Radiobutton(
            source_mode_frame,
            text="File locale",
            variable=self.source_mode_var,
            value="local",
            command=self.update_source_mode,
        ).pack(side="left")

        self.url_label = ttk.Label(frm, text="URL")
        self.url_label.grid(row=1, column=0, sticky="w", pady=4)
        self.url_entry = ttk.Entry(frm, textvariable=self.url_var, width=72)
        self.url_entry.grid(row=1, column=1, sticky="ew", pady=4)

        self.source_label = ttk.Label(frm, text="Sorgente locale")
        self.source_label.grid(row=2, column=0, sticky="w", pady=4)
        self.source_entry = ttk.Entry(frm, textvariable=self.source_var, width=72)
        self.source_entry.grid(row=2, column=1, sticky="ew", pady=4)
        self.source_browse_btn = ttk.Button(frm, text="Sfoglia", command=self.pick_source)
        self.source_browse_btn.grid(row=2, column=2, padx=6, pady=4)

        # --- input clip ---
        ttk.Label(frm, text="Input clip").grid(row=3, column=0, sticky="w", pady=4)

        clip_mode_frame = ttk.Frame(frm)
        clip_mode_frame.grid(row=3, column=1, columnspan=2, sticky="w", pady=4)

        ttk.Radiobutton(
            clip_mode_frame,
            text="Ranges CSV",
            variable=self.clip_mode_var,
            value="csv",
            command=self.update_clip_mode,
        ).pack(side="left", padx=(0, 12))

        ttk.Radiobutton(
            clip_mode_frame,
            text="Clip file",
            variable=self.clip_mode_var,
            value="file",
            command=self.update_clip_mode,
        ).pack(side="left")

        self.ranges_label = ttk.Label(frm, text="Ranges CSV")
        self.ranges_label.grid(row=4, column=0, sticky="w", pady=4)
        self.ranges_entry = ttk.Entry(frm, textvariable=self.ranges_var, width=72)
        self.ranges_entry.grid(row=4, column=1, sticky="ew", pady=4)

        self.csv_example_label = ttk.Label(
            frm,
            text="Esempio: 00:00:05-00:00:10,00:00:12-00:00:18",
            foreground="gray",
        )
        self.csv_example_label.grid(row=5, column=1, columnspan=2, sticky="w", pady=(0, 6))

        self.clipfile_label = ttk.Label(frm, text="Clip file")
        self.clipfile_label.grid(row=6, column=0, sticky="w", pady=4)
        self.clipfile_entry = ttk.Entry(frm, textvariable=self.clipfile_var, width=72)
        self.clipfile_entry.grid(row=6, column=1, sticky="ew", pady=4)
        self.clipfile_browse_btn = ttk.Button(frm, text="Sfoglia", command=self.pick_clipfile)
        self.clipfile_browse_btn.grid(row=6, column=2, padx=6, pady=4)

        # --- output / workdir / browser ---
        ttk.Label(frm, text="Output").grid(row=7, column=0, sticky="w", pady=4)
        ttk.Entry(frm, textvariable=self.output_var, width=72).grid(row=7, column=1, sticky="ew", pady=4)

        ttk.Label(
            frm,
            text="Se il file esiste già, verrà creato automaticamente output_001, output_002, ...",
            foreground="gray",
        ).grid(row=8, column=1, columnspan=2, sticky="w", pady=(0, 6))

        ttk.Label(frm, text="Workdir").grid(row=9, column=0, sticky="w", pady=4)
        ttk.Entry(frm, textvariable=self.workdir_var, width=72).grid(row=9, column=1, sticky="ew", pady=4)
        ttk.Button(frm, text="Sfoglia", command=self.pick_workdir).grid(row=9, column=2, padx=6, pady=4)

        ttk.Label(frm, text="Browser").grid(row=10, column=0, sticky="w", pady=4)
        ttk.Entry(frm, textvariable=self.browser_var, width=72).grid(row=10, column=1, sticky="ew", pady=4)

        # --- opzioni ---
        opts = ttk.Frame(frm)
        opts.grid(row=11, column=0, columnspan=3, sticky="ew", pady=(8, 4))

        ttk.Label(opts, text="Fade").grid(row=0, column=0, padx=(0, 6))
        ttk.Entry(opts, textvariable=self.fade_var, width=8).grid(row=0, column=1)

        ttk.Label(opts, text="Ricodifica").grid(row=0, column=2, padx=(12, 6))
        ttk.Combobox(
            opts,
            textvariable=self.reencode_var,
            values=["yes", "no"],
            width=8,
            state="readonly",
        ).grid(row=0, column=3)

        ttk.Checkbutton(opts, text="Auto-clean", variable=self.auto_clean_var).grid(row=0, column=4, padx=10)
        ttk.Checkbutton(opts, text="Dry-run", variable=self.dry_run_var).grid(row=0, column=5, padx=10)
        ttk.Button(opts, text="About", command=self.show_about).grid(row=0, column=6, padx=10)

        # --- stato / avanzamento ---
        progress_frame = ttk.LabelFrame(frm, text="Stato operazione", padding=10)
        progress_frame.grid(row=12, column=0, columnspan=3, sticky="ew", pady=(12, 8))
        progress_frame.columnconfigure(0, weight=1)

        ttk.Label(progress_frame, textvariable=self.status_var).grid(row=0, column=0, sticky="w")
        ttk.Label(progress_frame, textvariable=self.progress_text_var, foreground="gray").grid(
            row=1, column=0, sticky="w", pady=(2, 6)
        )

        self.progressbar = ttk.Progressbar(
            progress_frame,
            orient="horizontal",
            mode="determinate",
            maximum=100.0,
            variable=self.progress_value_var,
        )
        self.progressbar.grid(row=2, column=0, sticky="ew")

        # --- pulsanti ---
        btns = ttk.Frame(frm)
        btns.grid(row=13, column=0, columnspan=3, sticky="ew", pady=(10, 8))
        ttk.Button(btns, text="Aggiorna lista video", command=self.refresh_video_list).pack(side="left")
        ttk.Button(btns, text="Apri workdir", command=self.open_workdir).pack(side="left", padx=8)
        ttk.Button(btns, text="Esporta log", command=self.export_log).pack(side="left", padx=8)
        self.run_button = ttk.Button(btns, text="Avvia", command=self.start_job)
        self.run_button.pack(side="left", padx=8)

        # --- video list ---
        ttk.Label(frm, text="Video nella cartella di lavoro").grid(row=14, column=0, columnspan=3, sticky="w")

        self.video_list = ttk.Treeview(
            frm,
            columns=("name", "duration", "size"),
            show="headings",
            height=8,
        )
        self.video_list.grid(row=15, column=0, columnspan=3, sticky="nsew", pady=(2, 8))

        self.video_list.heading("name", text="Nome file")
        self.video_list.heading("duration", text="Durata")
        self.video_list.heading("size", text="Dimensione")

        self.video_list.column("name", width=700, anchor="w")
        self.video_list.column("duration", width=100, anchor="center")
        self.video_list.column("size", width=120, anchor="e")

        self.video_list.bind("<Double-Button-1>", self.open_selected_video)
        self.video_list.bind("<Button-3>", self.show_video_context_menu)

        self.video_menu = tk.Menu(self.root, tearoff=0)
        self.video_menu.add_command(label="Apri video", command=self.open_selected_video)
        self.video_menu.add_command(label="Apri cartella", command=self.open_workdir)
        self.video_menu.add_command(label="Usa come sorgente", command=self.use_selected_video_as_source)
        self.video_menu.add_separator()
        self.video_menu.add_command(label="Mostra percorso completo", command=self.show_selected_video_path)
        self.video_menu.add_command(label="Copia percorso", command=self.copy_selected_video_path)
        self.video_menu.add_command(label="Rinomina file", command=self.rename_selected_video)
        self.video_menu.add_separator()
        self.video_menu.add_command(label="Elimina file", command=self.delete_selected_video)
        self.video_menu.add_separator()
        self.video_menu.add_command(label="Aggiorna lista", command=self.refresh_video_list)

        # --- log ---
        ttk.Label(frm, text="Log").grid(row=16, column=0, columnspan=3, sticky="w")
        self.log_text = tk.Text(frm, height=20, wrap="word")
        self.log_text.grid(row=17, column=0, columnspan=3, sticky="nsew")

        frm.rowconfigure(17, weight=1)

    def process_ui_queue(self) -> None:
        try:
            while True:
                event_type, payload = self.event_queue.get_nowait()

                if event_type == "log":
                    self._append_log(str(payload))

                elif event_type == "progress":
                    status, percent = payload
                    self.status_var.set("In esecuzione")
                    self.progress_text_var.set(str(status))
                    if percent is not None:
                        self.progress_value_var.set(max(0.0, min(100.0, float(percent))))

                elif event_type == "duration_update":
                    item_id, duration_str = payload
                    if self.video_list.exists(item_id):
                        values = list(self.video_list.item(item_id, "values"))
                        if len(values) >= 3:
                            values[1] = duration_str
                            self.video_list.item(item_id, values=values)

                elif event_type == "done":
                    output_path = str(payload)
                    self.status_var.set("Completato")
                    self.progress_text_var.set(f"Creato: {output_path}")
                    self.progress_value_var.set(100.0)
                    if self.run_button:
                        self.run_button.config(state="normal")
                    self.refresh_video_list()
                    messagebox.showinfo("Completato", f"Creato:\n{output_path}")

                elif event_type == "error":
                    self.status_var.set("Errore")
                    self.progress_text_var.set(str(payload))
                    if self.run_button:
                        self.run_button.config(state="normal")
                    messagebox.showerror("Errore", str(payload))

        except queue.Empty:
            pass
        finally:
            self.root.after(100, self.process_ui_queue)

    def _append_log(self, msg: str) -> None:
        line = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
        self.log_lines.append(line)
        self.log_text.insert("end", line + "\n")
        self.log_text.see("end")
        self.root.update_idletasks()

    def threadsafe_log(self, msg: str) -> None:
        self.event_queue.put(("log", msg))

    def threadsafe_progress(self, status: str, percent: Optional[float]) -> None:
        self.event_queue.put(("progress", (status, percent)))

    def format_size(self, size_bytes: int) -> str:
        units = ["B", "KB", "MB", "GB", "TB"]
        size = float(size_bytes)
        for unit in units:
            if size < 1024.0 or unit == units[-1]:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size_bytes} B"

    def format_duration(self, seconds: float) -> str:
        total = int(round(seconds))
        h = total // 3600
        m = (total % 3600) // 60
        s = total % 60
        return f"{h:02d}:{m:02d}:{s:02d}"

    def get_video_duration_seconds(self, filepath: Path) -> Optional[float]:
        ffprobe = find_ffprobe()
        if not ffprobe:
            return None

        try:
            result = subprocess.run(
                [
                    ffprobe,
                    "-v",
                    "error",
                    "-show_entries",
                    "format=duration",
                    "-of",
                    "default=noprint_wrappers=1:nokey=1",
                    str(filepath),
                ],
                text=True,
                capture_output=True,
                check=True,
            )
            return float(result.stdout.strip())
        except Exception:
            return None

    def _load_duration_for_item(self, item_id: str, filepath: Path) -> None:
        try:
            dur = self.get_video_duration_seconds(filepath)
            duration_str = self.format_duration(dur) if dur is not None else "?"
            self.event_queue.put(("duration_update", (item_id, duration_str)))
        except Exception:
            self.event_queue.put(("duration_update", (item_id, "?")))

    def show_about(self) -> None:
        messagebox.showinfo(
            "About",
            f"YT Cut Merge GUI\n\n"
            f"Versione {self.version}\n\n"
            f"Autore: Antonio Fiumara\n"
            f"© 2026 Antonio Fiumara",
        )

    def export_log(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Salva log",
            defaultextension=".log",
            filetypes=[("Log", "*.log"), ("Text", "*.txt"), ("All", "*.*")],
        )
        if not path:
            return
        Path(path).write_text("\n".join(self.log_lines), encoding="utf-8")
        messagebox.showinfo("Log", f"Log salvato in:\n{path}")

    def apply_startup_args(self) -> None:
        args = sys.argv[1:]
        i = 0
        while i < len(args):
            arg = args[i]

            if arg in ("--url", "-u") and i + 1 < len(args):
                self.url_var.set(args[i + 1])
                self.source_mode_var.set("url")
                i += 2
                continue

            if arg in ("--workdir", "-w") and i + 1 < len(args):
                self.workdir_var.set(args[i + 1])
                i += 2
                continue

            if arg in ("--output", "-o") and i + 1 < len(args):
                self.output_var.set(args[i + 1])
                i += 2
                continue

            if arg in ("--clipfile", "-f") and i + 1 < len(args):
                self.clipfile_var.set(args[i + 1])
                self.clip_mode_var.set("file")
                i += 2
                continue

            if arg in ("--source", "-s") and i + 1 < len(args):
                self.source_var.set(args[i + 1])
                self.source_mode_var.set("local")
                i += 2
                continue

            if i == 0 and not arg.startswith("-"):
                self.url_var.set(arg)
                self.source_mode_var.set("url")
                i += 1
                continue

            i += 1

    def update_source_mode(self) -> None:
        mode = self.source_mode_var.get()

        if mode == "url":
            self.source_var.set("")

            if self.url_label:
                self.url_label.grid()
            if self.url_entry:
                self.url_entry.grid()

            if self.source_label:
                self.source_label.grid_remove()
            if self.source_entry:
                self.source_entry.grid_remove()
            if self.source_browse_btn:
                self.source_browse_btn.grid_remove()

        else:
            self.url_var.set("")

            if self.url_label:
                self.url_label.grid_remove()
            if self.url_entry:
                self.url_entry.grid_remove()

            if self.source_label:
                self.source_label.grid()
            if self.source_entry:
                self.source_entry.grid()
            if self.source_browse_btn:
                self.source_browse_btn.grid()

    def update_clip_mode(self) -> None:
        mode = self.clip_mode_var.get()

        if mode == "csv":
            self.clipfile_var.set("")

            if self.ranges_label:
                self.ranges_label.grid()
            if self.ranges_entry:
                self.ranges_entry.grid()
            if self.csv_example_label:
                self.csv_example_label.grid()

            if self.clipfile_label:
                self.clipfile_label.grid_remove()
            if self.clipfile_entry:
                self.clipfile_entry.grid_remove()
            if self.clipfile_browse_btn:
                self.clipfile_browse_btn.grid_remove()

        else:
            self.ranges_var.set("")

            if self.ranges_label:
                self.ranges_label.grid_remove()
            if self.ranges_entry:
                self.ranges_entry.grid_remove()
            if self.csv_example_label:
                self.csv_example_label.grid_remove()

            if self.clipfile_label:
                self.clipfile_label.grid()
            if self.clipfile_entry:
                self.clipfile_entry.grid()
            if self.clipfile_browse_btn:
                self.clipfile_browse_btn.grid()

    def pick_clipfile(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("Text", "*.txt"), ("All", "*.*")])
        if path:
            self.clipfile_var.set(path)
            self.clip_mode_var.set("file")
            self.update_clip_mode()

    def pick_source(self) -> None:
        path = filedialog.askopenfilename(
            filetypes=[("Video", "*.mp4 *.mkv *.webm *.mov *.m4v"), ("All", "*.*")]
        )
        if path:
            self.source_var.set(path)
            self.source_mode_var.set("local")
            self.update_source_mode()

    def pick_workdir(self) -> None:
        path = filedialog.askdirectory()
        if path:
            self.workdir_var.set(path)
            self.refresh_video_list()

    def refresh_video_list(self) -> None:
        for item in self.video_list.get_children():
            self.video_list.delete(item)

        try:
            workdir = Path(self.workdir_var.get()).expanduser().resolve()
            if not workdir.is_dir():
                return

            vids = list_video_files(workdir)

            for v in vids:
                try:
                    size_str = self.format_size(v.stat().st_size)
                except Exception:
                    size_str = "?"

                item_id = self.video_list.insert("", "end", values=(v.name, "...", size_str))
                threading.Thread(
                    target=self._load_duration_for_item,
                    args=(item_id, v),
                    daemon=True,
                ).start()

        except Exception as e:
            self._append_log(f"Errore aggiornamento lista video: {e}")

    def get_selected_video_path(self) -> Optional[Path]:
        selection = self.video_list.selection()
        if not selection:
            return None

        item_id = selection[0]
        values = self.video_list.item(item_id, "values")
        if not values:
            return None

        filename = values[0]
        workdir = Path(self.workdir_var.get()).expanduser().resolve()
        return workdir / filename

    def show_video_context_menu(self, event) -> None:
        try:
            item_id = self.video_list.identify_row(event.y)
            if not item_id:
                return

            self.video_list.selection_set(item_id)
            self.video_list.focus(item_id)

            if self.video_menu:
                self.video_menu.tk_popup(event.x_root, event.y_root)
        finally:
            try:
                if self.video_menu:
                    self.video_menu.grab_release()
            except Exception:
                pass

    def open_selected_video(self, event=None) -> None:
        try:
            filepath = self.get_selected_video_path()
            if not filepath:
                return

            if not filepath.exists():
                messagebox.showerror("Errore", f"File non trovato:\n{filepath}")
                return

            system = sys.platform.lower()

            if system.startswith("linux"):
                subprocess.Popen(["xdg-open", str(filepath)])
            elif system.startswith("win"):
                os.startfile(str(filepath))  # type: ignore[attr-defined]
            elif system == "darwin":
                subprocess.Popen(["open", str(filepath)])
            else:
                messagebox.showerror("Errore", "Sistema operativo non supportato")

        except Exception as e:
            messagebox.showerror("Errore apertura file", str(e))

    def open_workdir(self) -> None:
        try:
            workdir = Path(self.workdir_var.get()).expanduser().resolve()
            if not workdir.exists():
                messagebox.showerror("Errore", f"Cartella non trovata:\n{workdir}")
                return

            system = sys.platform.lower()

            if system.startswith("linux"):
                subprocess.Popen(["xdg-open", str(workdir)])
            elif system.startswith("win"):
                os.startfile(str(workdir))  # type: ignore[attr-defined]
            elif system == "darwin":
                subprocess.Popen(["open", str(workdir)])
            else:
                messagebox.showerror("Errore", "Sistema operativo non supportato")

        except Exception as e:
            messagebox.showerror("Errore apertura cartella", str(e))

    def use_selected_video_as_source(self) -> None:
        try:
            filepath = self.get_selected_video_path()
            if not filepath:
                return

            if not filepath.exists():
                messagebox.showerror("Errore", f"File non trovato:\n{filepath}")
                return

            self.source_var.set(str(filepath))
            self.source_mode_var.set("local")
            self.update_source_mode()

            self.status_var.set("Pronto")
            self.progress_text_var.set(f"Sorgente selezionata: {filepath.name}")

        except Exception as e:
            messagebox.showerror("Errore selezione sorgente", str(e))

    def show_selected_video_path(self) -> None:
        try:
            filepath = self.get_selected_video_path()
            if not filepath:
                return

            messagebox.showinfo("Percorso completo", str(filepath))

        except Exception as e:
            messagebox.showerror("Errore", str(e))

    def copy_selected_video_path(self) -> None:
        try:
            filepath = self.get_selected_video_path()
            if not filepath:
                return

            self.root.clipboard_clear()
            self.root.clipboard_append(str(filepath))
            self.root.update()

            self.status_var.set("Pronto")
            self.progress_text_var.set("Percorso copiato negli appunti")
            self._append_log(f"Percorso copiato: {filepath}")

        except Exception as e:
            messagebox.showerror("Errore copia percorso", str(e))

    def rename_selected_video(self) -> None:
        try:
            filepath = self.get_selected_video_path()
            if not filepath:
                return

            if not filepath.exists():
                messagebox.showerror("Errore", f"File non trovato:\n{filepath}")
                self.refresh_video_list()
                return

            current_stem = filepath.stem
            suffix = filepath.suffix

            new_stem = simpledialog.askstring(
                "Rinomina file",
                f"Nuovo nome file (senza estensione {suffix}):",
                initialvalue=current_stem,
                parent=self.root,
            )
            if new_stem is None:
                return

            new_stem = new_stem.strip()
            if not new_stem:
                messagebox.showerror("Errore", "Il nome file non può essere vuoto")
                return

            target = filepath.with_name(new_stem + suffix)

            if target == filepath:
                return

            if target.exists():
                messagebox.showerror("Errore", f"Esiste già un file con questo nome:\n{target.name}")
                return

            filepath.rename(target)

            self.refresh_video_list()
            self.status_var.set("Pronto")
            self.progress_text_var.set(f"File rinominato: {target.name}")
            self._append_log(f"File rinominato: {filepath} -> {target}")

        except Exception as e:
            messagebox.showerror("Errore rinomina file", str(e))

    def delete_selected_video(self) -> None:
        try:
            filepath = self.get_selected_video_path()
            if not filepath:
                return

            if not filepath.exists():
                messagebox.showerror("Errore", f"File non trovato:\n{filepath}")
                self.refresh_video_list()
                return

            ok = messagebox.askyesno(
                "Conferma eliminazione",
                f"Vuoi eliminare questo file?\n\n{filepath.name}"
            )
            if not ok:
                return

            filepath.unlink()

            self.refresh_video_list()
            self.status_var.set("Pronto")
            self.progress_text_var.set(f"File eliminato: {filepath.name}")
            self._append_log(f"File eliminato: {filepath}")

        except Exception as e:
            messagebox.showerror("Errore eliminazione file", str(e))

    def start_job(self) -> None:
        self.log_text.delete("1.0", "end")
        self.log_lines.clear()
        self.status_var.set("In preparazione")
        self.progress_text_var.set("Avvio operazione...")
        self.progress_value_var.set(0.0)

        if self.run_button:
            self.run_button.config(state="disabled")

        threading.Thread(target=self._run_job, daemon=True).start()

    def _run_job(self) -> None:
        try:
            workdir = Path(self.workdir_var.get()).expanduser().resolve()
            workdir.mkdir(parents=True, exist_ok=True)

            source = None
            url = None

            if self.source_mode_var.get() == "url":
                url = self.url_var.get().strip() or None
            else:
                source = Path(self.source_var.get()).expanduser().resolve() if self.source_var.get().strip() else None

            clipfile = None
            ranges_csv = None

            if self.clip_mode_var.get() == "file":
                clipfile = Path(self.clipfile_var.get()).expanduser().resolve() if self.clipfile_var.get().strip() else None
            else:
                ranges_csv = self.ranges_var.get().strip() or None

            output = workdir / (self.output_var.get().strip() or "output_finale.mp4")

            cfg = JobConfig(
                url=url,
                clipfile=clipfile,
                ranges_csv=ranges_csv,
                source_file=source,
                output_file=output,
                workdir=workdir,
                fade=float(self.fade_var.get().strip()),
                reencode=(self.reencode_var.get().strip() == "yes"),
                dry_run=self.dry_run_var.get(),
                auto_clean=self.auto_clean_var.get(),
                browser=self.browser_var.get().strip() or None,
            )

            result = process_job(cfg, self.threadsafe_log, progress=self.threadsafe_progress)
            self.event_queue.put(("done", str(result)))

        except Exception as e:
            self.threadsafe_log(f"Errore: {e}")
            self.event_queue.put(("error", str(e)))


def main() -> None:
    root = tk.Tk()
    try:
        ttk.Style().theme_use("clam")
    except Exception:
        pass
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
