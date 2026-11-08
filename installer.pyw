import ast
import importlib.util
import math
from pathlib import Path
import queue
import subprocess
import sys
import threading
import time
import tkinter as tk


APP_DIR = Path(__file__).resolve().parent
ENTRY_POINT = APP_DIR / "start.pyw"
PYTHON_SOURCES = (APP_DIR / "main.py", ENTRY_POINT)
DEPENDENCY_NAMES = {
    "PIL": "Pillow",
    "cv2": "opencv-python",
    "bs4": "beautifulsoup4",
    "yaml": "PyYAML",
    "sklearn": "scikit-learn",
}


def scan_imports():
    local_names = {path.stem for path in PYTHON_SOURCES if path.exists()}
    local_names.update(
        path.name for path in APP_DIR.iterdir() if path.is_dir()
    )
    imports = set()
    for source_path in PYTHON_SOURCES:
        if not source_path.exists():
            continue
        tree = ast.parse(source_path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                imports.add(node.module.split(".", 1)[0])

    standard_library = getattr(sys, "stdlib_module_names", set())
    external = set()
    for name in imports - local_names - standard_library:
        try:
            if importlib.util.find_spec(name) is None:
                external.add(name)
        except (ImportError, ValueError, ModuleNotFoundError):
            external.add(name)
    return sorted(external)


def install_missing_imports(imports, emit, on_process=None):
    packages = sorted({DEPENDENCY_NAMES.get(name, name) for name in imports})
    if not packages:
        emit("All imports are available; this app currently needs no extra packages.")
        return
    emit("Installing: " + ", ".join(packages))
    command = [
        sys.executable, "-m", "pip", "install", "--disable-pip-version-check",
        *packages,
    ]
    try:
        process = subprocess.Popen(
            command, cwd=APP_DIR, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True, encoding="utf-8",
            errors="replace", bufsize=1,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except OSError as exc:
        raise RuntimeError(f"Could not start pip: {exc}") from exc
    if on_process is not None:
        on_process(process)
    if process.stdout is not None:
        for line in process.stdout:
            line = line.strip()
            if line:
                emit(line)
    result = process.wait()
    if result:
        raise RuntimeError(
            f"pip could not install the required packages (exit code {result}). "
            "Check your internet connection and Python's pip setup."
        )


class ForestInstaller:
    WIDTH = 1000
    HEIGHT = 680
    BG = "#08131d"
    CARD = "#0b1725"
    TEXT = "#f4f7ff"
    MUTED = "#9cacc1"
    PURPLE = "#a58bff"
    CYAN = "#64d9ee"
    GREEN = "#83e6ba"
    RED = "#ff8c91"

    STAGES = (
        "Find app",
        "Check Python",
        "Scan imports",
        "Install",
        "Verify",
    )

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Pawstra AI - Setup")
        self.root.geometry(f"{self.WIDTH}x{self.HEIGHT}")
        self.root.minsize(820, 600)
        self.root.configure(bg=self.BG)
        self.root.protocol("WM_DELETE_WINDOW", self._close)
        self.canvas = tk.Canvas(
            self.root, bg=self.BG, highlightthickness=0, borderwidth=0,
        )
        self.canvas.pack(fill="both", expand=True)
        self.events = queue.Queue()
        self.started_at = time.monotonic()
        self.progress = 0.0
        self.stage = 0
        self.status = "Preparing your workspace..."
        self.detail = "The five-step setup will check Python, install missing imports, and verify the app."
        self.error = ""
        self.finished = False
        self.closing = False
        self._process = None
        self.canvas.bind("<Configure>", self._resized)
        self.canvas.bind("<Button-1>", self._clicked)
        self._tick()
        self.root.after(500, self._start_install)
        self.root.after(60, self._poll_events)

    def run(self):
        self.root.mainloop()

    def _close(self):
        self.closing = True
        if self._process is not None and self._process.poll() is None:
            self._process.terminate()
        self.root.destroy()

    def _resized(self, _event=None):
        self._draw()

    def _start_install(self):
        if self.closing or self.finished:
            return
        worker = threading.Thread(target=self._install, daemon=True)
        worker.start()

    def _emit(self, kind, value=None):
        self.events.put((kind, value))

    def _install(self):
        try:
            self._emit("stage", (1, 0.06, "Finding the app files..."))
            if not (APP_DIR / "main.py").is_file() or not ENTRY_POINT.is_file():
                raise RuntimeError(
                    "main.py or start.pyw is missing. Keep installer.pyw beside the app files."
                )
            self._emit("log", "App files found.")

            self._emit("stage", (2, 0.24, "Checking Python and Tkinter..."))
            if sys.version_info < (3, 10):
                raise RuntimeError("Python 3.10 or newer is required.")
            if importlib.util.find_spec("tkinter") is None:
                raise RuntimeError(
                    "Tkinter is missing. Reinstall Python with Tcl/Tk support enabled."
                )
            self._emit("log", f"Python {sys.version.split()[0]} and Tkinter are ready.")

            self._emit("stage", (3, 0.43, "Scanning the app’s Python imports..."))
            imports = scan_imports()
            if imports:
                self._emit("log", "Missing imports: " + ", ".join(imports))
            else:
                self._emit("log", "All imports found; no third-party packages are currently required.")

            self._emit("stage", (4, 0.61, "Installing missing packages..."))
            install_missing_imports(
                imports, lambda line: self._emit("log", line),
                on_process=self._set_process,
            )
            self._emit("progress", 0.82)

            self._emit("stage", (5, 0.86, "Verifying the app..."))
            compile_command = [
                sys.executable, "-c",
                "import ast, pathlib; "
                "ast.parse(pathlib.Path('main.py').read_text(encoding='utf-8'))",
            ]
            result = subprocess.run(
                compile_command, cwd=APP_DIR, capture_output=True,
                text=True, encoding="utf-8", errors="replace",
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            if result.returncode:
                detail = (result.stderr or result.stdout).strip()
                raise RuntimeError("App verification failed: " + detail)
            for name in imports:
                if importlib.util.find_spec(name) is None:
                    raise RuntimeError(f"The import '{name}' is still unavailable after installation.")
            self._emit("log", "Imports and Python syntax verified.")
            self._emit("complete", None)
        except (OSError, RuntimeError, SyntaxError, ValueError) as exc:
            self._emit("error", str(exc))

    def _set_process(self, process):
        self._process = process

    def _poll_events(self):
        if self.closing:
            return
        changed = False
        try:
            while True:
                kind, value = self.events.get_nowait()
                changed = True
                if kind == "stage":
                    self.stage, self.progress, self.status = value
                    self.error = ""
                elif kind == "progress":
                    self.progress = value
                elif kind == "log":
                    self.detail = value
                elif kind == "error":
                    self.error = value
                    self.status = "Setup needs attention"
                    self.finished = True
                elif kind == "complete":
                    self.progress = 1.0
                    self.status = "Your workspace is ready"
                    self.detail = "All five stages are complete. Launch Pawstra AI when you’re ready."
                    self.finished = True
        except queue.Empty:
            pass
        if changed:
            self._draw()
        self.root.after(60, self._poll_events)

    def _draw(self):
        if self.closing or not self.canvas.winfo_exists():
            return
        width = max(self.canvas.winfo_width(), 1)
        height = max(self.canvas.winfo_height(), 1)
        self.canvas.delete("all")
        self._draw_forest(width, height)
        self._draw_panel(width, height)

    def _draw_forest(self, width, height):
        canvas = self.canvas
        horizon = int(height * 0.39)
        canvas.create_rectangle(0, 0, width, height, fill="#101d2a", outline="")
        canvas.create_rectangle(0, 0, width, horizon, fill="#142636", outline="")
        canvas.create_polygon(
            0, horizon + 16, width * 0.23, horizon - 48,
            width * 0.48, horizon + 9, width * 0.74, horizon - 62,
            width, horizon + 12, width, height, 0, height,
            fill="#19313a", outline="",
        )
        canvas.create_polygon(
            width * 0.41, horizon + 3, width * 0.59, horizon + 3,
            width * 0.94, height, width * 0.06, height,
            fill="#20343a", outline="",
        )
        elapsed = time.monotonic() - self.started_at
        camera = elapsed * 0.48
        for index in range(24):
            seed = (index * 0.61803398875) % 1
            depth = (seed + camera) % 1
            spread = 0.20 + depth * 1.55
            world_x = ((index * 37) % 101) / 50.0 - 1.0
            x = width * (0.5 + world_x * spread * 0.5)
            base_y = horizon + depth * height * 0.12
            tree_height = height * (0.07 + depth * 0.56)
            trunk_width = max(2, int(width * (0.002 + depth * 0.012)))
            foliage_width = tree_height * (0.42 + depth * 0.11)
            top = base_y - tree_height
            if x < -foliage_width or x > width + foliage_width:
                continue
            shade = "#18353a" if index % 2 else "#20423e"
            canvas.create_polygon(
                x, top, x - foliage_width * 0.56, base_y - tree_height * 0.35,
                x - foliage_width * 0.28, base_y - tree_height * 0.29,
                x - foliage_width * 0.65, base_y - tree_height * 0.04,
                x + foliage_width * 0.65, base_y - tree_height * 0.04,
                x + foliage_width * 0.28, base_y - tree_height * 0.29,
                x + foliage_width * 0.56, base_y - tree_height * 0.35,
                fill=shade, outline="",
            )
            canvas.create_rectangle(
                x - trunk_width // 2, base_y - tree_height * 0.27,
                x + trunk_width // 2, base_y,
                fill="#334239", outline="",
            )
        canvas.create_rectangle(
            0, 0, width, height, fill="#07111b", stipple="gray50", outline="",
        )

    def _draw_panel(self, width, height):
        canvas = self.canvas
        scale = min(width / self.WIDTH, height / self.HEIGHT)
        left, right = width * 0.06, width * 0.94
        top, bottom = height * 0.07, height * 0.93
        canvas.create_rectangle(
            left, top, right, bottom, fill=self.CARD, stipple="gray50",
            outline="#3b5567", width=2,
        )
        canvas.create_text(
            left + 34 * scale, top + 36 * scale, anchor="w",
            text="AI CHAT  /  SETUP", fill=self.CYAN,
            font=("Segoe UI", max(9, int(10 * scale)), "bold"),
        )
        canvas.create_text(
            left + 34 * scale, top + 82 * scale, anchor="w",
            text="Getting your workspace ready",
            fill=self.TEXT, font=("Segoe UI", max(19, int(26 * scale)), "bold"),
        )
        canvas.create_text(
            left + 35 * scale, top + 114 * scale, anchor="w",
            text="A small forest journey for your Python setup.",
            fill=self.MUTED, font=("Segoe UI", max(9, int(11 * scale))),
        )

        stage_y = top + 175 * scale
        stage_left, stage_right = left + 54 * scale, right - 54 * scale
        spacing = (stage_right - stage_left) / 4
        canvas.create_line(
            stage_left, stage_y, stage_right, stage_y,
            fill="#31485a", width=max(2, int(3 * scale)),
        )
        canvas.create_line(
            stage_left, stage_y,
            stage_left + (stage_right - stage_left) * self.progress, stage_y,
            fill=self.CYAN, width=max(3, int(4 * scale)),
        )
        for index, name in enumerate(self.STAGES):
            x = stage_left + spacing * index
            complete = index + 1 < self.stage or self.finished and not self.error
            active = index + 1 == self.stage and not self.error
            color = self.GREEN if complete else self.PURPLE if active else "#526574"
            radius = 14 * scale
            canvas.create_oval(
                x - radius, stage_y - radius, x + radius, stage_y + radius,
                fill="#172a3a", outline=color, width=max(2, int(2 * scale)),
            )
            canvas.create_text(
                x, stage_y, text="✓" if complete else str(index + 1),
                fill=color, font=("Segoe UI", max(8, int(9 * scale)), "bold"),
            )
            canvas.create_text(
                x, stage_y + 29 * scale, text=name, fill=color,
                font=("Segoe UI", max(8, int(9 * scale))),
            )

        status_y = top + 260 * scale
        canvas.create_text(
            left + 35 * scale, status_y, anchor="w", text=self.status,
            fill=self.RED if self.error else self.TEXT,
            font=("Segoe UI", max(13, int(16 * scale)), "bold"),
        )
        canvas.create_text(
            left + 35 * scale, status_y + 28 * scale, anchor="w",
            text=self.detail[:120], fill=self.MUTED,
            font=("Segoe UI", max(9, int(10 * scale))),
        )

        line_y = top + 355 * scale
        line_left, line_right = left + 34 * scale, right - 34 * scale
        canvas.create_text(
            line_left, line_y - 19 * scale, anchor="w",
            text="INSTALLATION FLIGHT PATH",
            fill=self.CYAN, font=("Segoe UI", max(8, int(9 * scale)), "bold"),
        )
        canvas.create_line(
            line_left, line_y, line_right, line_y,
            fill="#526779", width=max(2, int(2 * scale)), dash=(7, 5),
        )
        visual_progress = self.progress
        if not self.finished and not self.error and self.stage:
            stage_end = self.stage / len(self.STAGES)
            visual_progress = min(
                stage_end,
                self.progress + 0.035 * (
                    1 + math.sin((time.monotonic() - self.started_at) * 4)
                ),
            )
        completed_x = line_left + (line_right - line_left) * self.progress
        canvas.create_line(
            line_left, line_y, completed_x, line_y,
            fill=self.PURPLE, width=max(3, int(4 * scale)),
        )
        for index in range(5):
            x = line_left + (line_right - line_left) * index / 4
            canvas.create_oval(
                x - 4 * scale, line_y - 4 * scale,
                x + 4 * scale, line_y + 4 * scale,
                fill=self.CYAN if index / 4 <= self.progress else "#526779",
                outline="",
            )
        self._draw_cat(
            line_left + (line_right - line_left) * visual_progress,
            line_y, scale,
        )

        detail_y = top + 425 * scale
        canvas.create_text(
            left + 35 * scale, detail_y, anchor="w",
            text=f"PYTHON  {sys.version.split()[0]}     •     IMPORTS  AUTO-CHECKED",
            fill="#a5bbcc", font=("Consolas", max(8, int(9 * scale))),
        )
        if self.error:
            action_text = "RETRY"
            button_color = "#713b63"
        elif self.finished:
            action_text = "OPEN AI CHAT"
            button_color = "#6151b7"
        else:
            action_text = "INSTALLING..."
            button_color = "#263747"
        button_width, button_height = 166 * scale, 42 * scale
        button_x, button_y = right - 35 * scale - button_width, bottom - 54 * scale
        self.button_bounds = (
            button_x, button_y, button_x + button_width, button_y + button_height
        )
        canvas.create_rectangle(
            *self.button_bounds, fill=button_color, outline="#a58bff",
            width=max(1, int(scale)),
        )
        canvas.create_text(
            button_x + button_width / 2, button_y + button_height / 2,
            text=action_text, fill=self.TEXT,
            font=("Segoe UI", max(9, int(10 * scale)), "bold"),
        )
        if self.error:
            canvas.create_text(
                left + 35 * scale, bottom - 32 * scale, anchor="w",
                text=self.error[:100], fill=self.RED,
                font=("Segoe UI", max(8, int(9 * scale))),
            )

    def _draw_cat(self, x, y, scale):
        canvas = self.canvas
        bob = math.sin(time.monotonic() * 8) * 3 * scale
        y += bob
        color = "#c8a9ff"
        outline = "#efe8ff"
        body_w, body_h = 24 * scale, 14 * scale
        canvas.create_arc(
            x - 26 * scale, y - 10 * scale, x - 7 * scale, y + 9 * scale,
            start=200, extent=270, style="arc", outline=self.CYAN,
            width=max(2, int(2 * scale)),
        )
        wing = 7 * scale + abs(math.sin(time.monotonic() * 13)) * 5 * scale
        canvas.create_polygon(
            x - 6 * scale, y - 3 * scale,
            x - 14 * scale, y - wing,
            x - 2 * scale, y - 7 * scale,
            fill="#72cee5", outline="#d5faff",
        )
        canvas.create_oval(
            x - body_w / 2, y - body_h / 2,
            x + body_w / 2, y + body_h / 2,
            fill=color, outline=outline, width=max(1, int(scale)),
        )
        canvas.create_polygon(
            x + 5 * scale, y - 4 * scale,
            x + 8 * scale, y - 13 * scale,
            x + 14 * scale, y - 6 * scale,
            fill=color, outline=outline,
        )
        canvas.create_polygon(
            x + 12 * scale, y - 5 * scale,
            x + 17 * scale, y - 12 * scale,
            x + 19 * scale, y - 3 * scale,
            fill=color, outline=outline,
        )
        canvas.create_oval(
            x + 10 * scale, y - 5 * scale,
            x + 12 * scale, y - 3 * scale,
            fill="#142235", outline="",
        )
        for offset in (-4, 1):
            canvas.create_text(
                x + offset * scale, y + body_h / 2 + 5 * scale,
                text="‹", fill="#fff5c4",
                font=("Consolas", max(8, int(9 * scale)), "bold"),
            )
        canvas.create_line(
            x - 14 * scale, y + 12 * scale,
            x + 6 * scale, y + 12 * scale,
            fill=self.CYAN, width=max(1, int(scale)),
        )

    def _tick(self):
        if self.closing:
            return
        self._draw()
        self.root.after(16, self._tick)

    def _clicked(self, event):
        bounds = getattr(self, "button_bounds", None)
        if bounds is None:
            return
        x1, y1, x2, y2 = bounds
        if not (x1 <= event.x <= x2 and y1 <= event.y <= y2):
            return
        if self.error:
            self.error = ""
            self.finished = False
            self.progress = 0.0
            self.stage = 0
            self.status = "Preparing your workspace..."
            self._start_install()
        elif self.finished:
            try:
                subprocess.Popen(
                    [sys.executable, str(ENTRY_POINT)], cwd=APP_DIR,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
            except OSError as exc:
                self.error = f"Could not launch Pawstra AI: {exc}"
                self.finished = False
                self._draw()
if __name__ == "__main__":
    ForestInstaller().run()
