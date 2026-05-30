#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gemini-web2api desktop manager.

Double-click this file with pythonw.exe on Windows to manage the API service
without showing a terminal window.
"""

import json
import os
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk


APP_DIR = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
SERVER_SCRIPT = APP_DIR / "gemini_web2api.py"
SERVER_EXE = APP_DIR / ("gemini_web2api_server.exe" if os.name == "nt" else "gemini_web2api_server")
CONFIG_FILE = APP_DIR / "config.json"
LOG_DIR = APP_DIR / "logs"
LOG_FILE = LOG_DIR / "gemini_web2api.log"
PID_FILE = APP_DIR / ".gemini_web2api.pid"

DEFAULT_PORT = 8881
CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def hidden_startupinfo():
    if os.name != "nt":
        return None
    info = subprocess.STARTUPINFO()
    info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    return info


def run_hidden(args, **kwargs):
    kwargs.setdefault("capture_output", True)
    kwargs.setdefault("text", True)
    kwargs.setdefault("encoding", "utf-8")
    kwargs.setdefault("errors", "replace")
    if os.name == "nt":
        kwargs.setdefault("creationflags", CREATE_NO_WINDOW)
        kwargs.setdefault("startupinfo", hidden_startupinfo())
    return subprocess.run(args, **kwargs)


def get_python_executable():
    if getattr(sys, "frozen", False):
        return "python"
    exe = Path(sys.executable)
    if exe.name.lower() == "pythonw.exe":
        python_exe = exe.with_name("python.exe")
        if python_exe.exists():
            return str(python_exe)
    return str(exe)


def load_config_port():
    try:
        with CONFIG_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return int(data.get("port") or DEFAULT_PORT)
    except Exception:
        return DEFAULT_PORT


def get_lan_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()


class GeminiManager(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("GeminiWeb2API 服务管理")
        self.geometry("1040x720")
        self.minsize(900, 600)
        self.configure(bg="#f4f7fb")

        self.process = None
        self.log_pos = 0
        self.port_var = tk.StringVar(value=str(load_config_port()))
        self.status_var = tk.StringVar(value="检测中")
        self.run_status_var = tk.StringVar(value="检测中")
        self.health_status_var = tk.StringVar(value="检测中")
        self.pid_var = tk.StringVar(value="PID：-")
        self.base_url_var = tk.StringVar()
        self.lan_url_var = tk.StringVar()
        self.admin_url_var = tk.StringVar()
        self.health_monitor_var = tk.BooleanVar(value=True)
        self.stop_on_exit_var = tk.BooleanVar(value=True)
        self.auto_scroll_var = tk.BooleanVar(value=True)

        self._setup_style()
        self._build_ui()
        self._ensure_log_file()
        self._load_recent_log()
        self._update_urls()

        self.port_var.trace_add("write", lambda *_: self._update_urls())
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self.after(300, self._refresh_status)
        self.after(500, self._poll_log_file)
        self.after(800, self._auto_start_if_needed)

    def _setup_style(self):
        self.colors = {
            "window": "#f4f7fb",
            "card": "#ffffff",
            "border": "#e5eaf1",
            "text": "#1f2937",
            "muted": "#64748b",
            "button": "#edf1f6",
            "button_active": "#e2e8f0",
            "green_text": "#16a34a",
            "green_bg": "#eaf8ef",
            "red_text": "#dc2626",
            "red_bg": "#fee2e2",
            "yellow_text": "#b45309",
            "yellow_bg": "#fef3c7",
            "log_bg": "#f8fafc",
        }
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure("App.TFrame", background=self.colors["window"])
        style.configure("Card.TFrame", background=self.colors["card"])
        style.configure("Title.TLabel", background=self.colors["card"], foreground="#0f172a", font=("Microsoft YaHei UI", 24, "bold"))
        style.configure("Subtitle.TLabel", background=self.colors["card"], foreground=self.colors["muted"], font=("Microsoft YaHei UI", 11))
        style.configure("SectionTitle.TLabel", background=self.colors["card"], foreground="#111827", font=("Microsoft YaHei UI", 13, "bold"))
        style.configure("Body.TLabel", background=self.colors["card"], foreground=self.colors["muted"], font=("Microsoft YaHei UI", 10))
        style.configure("Label.TLabel", background=self.colors["card"], foreground=self.colors["muted"], font=("Microsoft YaHei UI", 10))
        style.configure("Value.TLabel", background=self.colors["card"], foreground="#111827", font=("Microsoft YaHei UI", 11, "bold"))
        style.configure("Pid.TLabel", background=self.colors["card"], foreground=self.colors["muted"], font=("Microsoft YaHei UI", 9))
        style.configure("Plain.TButton", background=self.colors["button"], foreground="#334155", padding=(28, 12), borderwidth=0, focusthickness=0, font=("Microsoft YaHei UI", 11, "bold"))
        style.map("Plain.TButton", background=[("active", self.colors["button_active"]), ("disabled", "#f1f5f9")], foreground=[("disabled", "#94a3b8")])
        style.configure("Small.TButton", background=self.colors["button"], foreground="#334155", padding=(18, 9), borderwidth=0, focusthickness=0, font=("Microsoft YaHei UI", 10, "bold"))
        style.map("Small.TButton", background=[("active", self.colors["button_active"]), ("disabled", "#f1f5f9")], foreground=[("disabled", "#94a3b8")])
        style.configure("Port.TEntry", fieldbackground="#ffffff", foreground="#111827", insertcolor="#111827", bordercolor=self.colors["border"], lightcolor=self.colors["border"], darkcolor=self.colors["border"], padding=8, font=("Consolas", 11))
        style.configure("Modern.TCheckbutton", background=self.colors["card"], foreground="#334155", font=("Microsoft YaHei UI", 10), focuscolor=self.colors["card"])
        style.map("Modern.TCheckbutton", background=[("active", self.colors["card"])] )

    def _card(self, parent, row, column, columnspan=1, **grid):
        card = tk.Frame(parent, bg=self.colors["card"], highlightthickness=1, highlightbackground=self.colors["border"], bd=0)
        card.grid(row=row, column=column, columnspan=columnspan, sticky=tk.NSEW, **grid)
        inner = ttk.Frame(card, style="Card.TFrame", padding=28)
        inner.pack(fill=tk.BOTH, expand=True)
        return inner

    def _badge(self, parent, variable, bg, fg):
        label = tk.Label(parent, textvariable=variable, bg=bg, fg=fg, padx=28, pady=12, font=("Microsoft YaHei UI", 11, "bold"), bd=0)
        return label

    def _url_row(self, parent, row, label, variable, copy_command=None):
        ttk.Label(parent, text=label, style="Label.TLabel").grid(row=row, column=0, sticky=tk.W, pady=(0, 12))
        ttk.Label(parent, textvariable=variable, style="Value.TLabel").grid(row=row, column=1, sticky=tk.W, padx=(20, 48), pady=(0, 12))
        if copy_command:
            ttk.Button(parent, text="复制", style="Small.TButton", command=copy_command).grid(row=row, column=2, sticky=tk.E, pady=(0, 12))

    def _build_ui(self):
        root = ttk.Frame(self, padding=24, style="App.TFrame")
        root.pack(fill=tk.BOTH, expand=True)
        root.columnconfigure(0, weight=1)
        root.rowconfigure(2, weight=1)

        header = self._card(root, 0, 0, pady=(0, 20))
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text="GeminiWeb2API", style="Title.TLabel").grid(row=0, column=0, sticky=tk.W)
        ttk.Label(header, text="本地代理服务管理", style="Subtitle.TLabel").grid(row=1, column=0, sticky=tk.W, pady=(8, 0))
        self.run_badge = self._badge(header, self.run_status_var, self.colors["yellow_bg"], self.colors["yellow_text"])
        self.run_badge.grid(row=0, column=1, rowspan=2, sticky=tk.E, padx=(16, 0))
        self.health_badge = self._badge(header, self.health_status_var, self.colors["yellow_bg"], self.colors["yellow_text"])
        self.health_badge.grid(row=0, column=2, rowspan=2, sticky=tk.E, padx=(12, 32))

        control = self._card(root, 1, 0, pady=(0, 20))
        control.columnconfigure(1, weight=1)
        control.columnconfigure(3, weight=1)
        ttk.Label(control, text="服务控制", style="SectionTitle.TLabel").grid(row=0, column=0, columnspan=2, sticky=tk.W)
        ttk.Label(control, text="打开管理器后会自动静默启动服务", style="Body.TLabel").grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=(10, 28))

        button_bar = ttk.Frame(control, style="Card.TFrame")
        button_bar.grid(row=0, column=4, rowspan=2, sticky=tk.NE)
        self.start_button = ttk.Button(button_bar, text="启动", style="Plain.TButton", command=self.start_server)
        self.start_button.grid(row=0, column=0, padx=(0, 12))
        self.stop_button = ttk.Button(button_bar, text="停止", style="Plain.TButton", command=self.stop_server)
        self.stop_button.grid(row=0, column=1, padx=(0, 12))
        self.restart_button = ttk.Button(button_bar, text="重启", style="Plain.TButton", command=self.restart_server)
        self.restart_button.grid(row=0, column=2)
        ttk.Button(button_bar, text="打开 Web 管理台", style="Plain.TButton", command=self.open_admin_url).grid(row=1, column=0, columnspan=2, sticky=tk.EW, pady=(24, 0), padx=(0, 12))
        ttk.Button(button_bar, text="打开 API 地址", style="Plain.TButton", command=self.open_base_url).grid(row=1, column=2, pady=(24, 0))

        ttk.Label(control, text="端口", style="Label.TLabel").grid(row=2, column=0, sticky=tk.W, pady=(0, 14))
        self.port_entry = ttk.Entry(control, width=9, textvariable=self.port_var, style="Port.TEntry")
        self.port_entry.grid(row=2, column=1, sticky=tk.W, padx=(20, 56), pady=(0, 14))
        ttk.Label(control, textvariable=self.pid_var, style="Pid.TLabel").grid(row=2, column=2, columnspan=2, sticky=tk.W, pady=(0, 14))

        self._url_row(control, 3, "Web 管理台", self.admin_url_var, lambda: self.copy_text(self.admin_url_var.get()))
        self._url_row(control, 4, "API", self.base_url_var, lambda: self.copy_text(self.base_url_var.get()))
        self._url_row(control, 5, "Tavo/手机", self.lan_url_var, lambda: self.copy_text(self.lan_url_var.get()))

        ttk.Checkbutton(control, text="健康监控", variable=self.health_monitor_var, style="Modern.TCheckbutton").grid(row=6, column=0, sticky=tk.W, pady=(2, 0))
        ttk.Checkbutton(control, text="退出时停止本次服务", variable=self.stop_on_exit_var, style="Modern.TCheckbutton").grid(row=6, column=1, columnspan=2, sticky=tk.W, padx=(20, 0), pady=(2, 0))

        log_card = self._card(root, 2, 0)
        log_card.rowconfigure(1, weight=1)
        log_card.columnconfigure(0, weight=1)
        log_header = ttk.Frame(log_card, style="Card.TFrame")
        log_header.grid(row=0, column=0, sticky=tk.EW, pady=(0, 16))
        log_header.columnconfigure(0, weight=1)
        ttk.Label(log_header, text="运行日志", style="SectionTitle.TLabel").grid(row=0, column=0, sticky=tk.W)
        ttk.Checkbutton(log_header, text="自动滚动", variable=self.auto_scroll_var, style="Modern.TCheckbutton").grid(row=0, column=1, padx=(8, 0))
        ttk.Button(log_header, text="刷新", style="Small.TButton", command=self.refresh_log_view).grid(row=0, column=2, padx=(8, 0))
        ttk.Button(log_header, text="复制", style="Small.TButton", command=self.copy_log_view).grid(row=0, column=3, padx=(8, 0))
        ttk.Button(log_header, text="清空", style="Small.TButton", command=self.clear_log_view).grid(row=0, column=4, padx=(8, 0))
        ttk.Button(log_header, text="日志文件", style="Small.TButton", command=self.open_log_file).grid(row=0, column=5, padx=(8, 0))
        self.log_text = scrolledtext.ScrolledText(log_card, wrap=tk.WORD, state=tk.DISABLED, height=15, relief=tk.FLAT, bd=0)
        self.log_text.grid(row=1, column=0, sticky=tk.NSEW)
        self.log_text.configure(bg=self.colors["log_bg"], fg="#1f2937", insertbackground="#1f2937", selectbackground="#dbeafe", font=("Consolas", 11), padx=18, pady=14)

    def _ensure_log_file(self):
        LOG_DIR.mkdir(exist_ok=True)
        LOG_FILE.touch(exist_ok=True)

    def _load_recent_log(self):
        try:
            size = LOG_FILE.stat().st_size
            with LOG_FILE.open("rb") as f:
                if size > 65536:
                    f.seek(size - 65536)
                data = f.read()
            self._insert_log(data.decode("utf-8", errors="replace"))
            self.log_pos = size
        except Exception as e:
            self._insert_log(f"[manager] 读取日志失败：{e}\n")

    def _poll_log_file(self):
        try:
            self._ensure_log_file()
            size = LOG_FILE.stat().st_size
            if size < self.log_pos:
                self.log_pos = 0
            if size > self.log_pos:
                with LOG_FILE.open("rb") as f:
                    f.seek(self.log_pos)
                    data = f.read()
                    self.log_pos = f.tell()
                self._insert_log(data.decode("utf-8", errors="replace"))
        except Exception as e:
            self._insert_log(f"[manager] 刷新日志失败：{e}\n")
        self.after(500, self._poll_log_file)

    def _insert_log(self, text):
        if not text:
            return
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.insert(tk.END, text)
        line_count = int(self.log_text.index("end-1c").split(".")[0])
        if line_count > 5000:
            self.log_text.delete("1.0", "1000.0")
        if self.auto_scroll_var.get():
            self.log_text.see(tk.END)
        self.log_text.configure(state=tk.DISABLED)

    def _write_manager_log(self, message):
        self._ensure_log_file()
        line = f"[manager {time.strftime('%Y-%m-%d %H:%M:%S')}] {message}\n"
        with LOG_FILE.open("a", encoding="utf-8", buffering=1) as f:
            f.write(line)

    def _update_urls(self):
        port = self.port_var.get().strip() or str(DEFAULT_PORT)
        self.admin_url_var.set(f"http://127.0.0.1:{port}/admin")
        self.base_url_var.set(f"http://127.0.0.1:{port}/v1")
        self.lan_url_var.set(f"http://{get_lan_ip()}:{port}/v1")

    def _get_port(self):
        raw = self.port_var.get().strip()
        try:
            port = int(raw)
        except ValueError:
            raise ValueError("端口必须是数字")
        if not (1 <= port <= 65535):
            raise ValueError("端口必须在 1-65535 之间")
        return port

    def _health_check(self, port=None):
        try:
            port = port or self._get_port()
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=0.8) as resp:
                return 200 <= getattr(resp, "status", 200) < 500
        except Exception:
            return False

    def _read_pid(self):
        try:
            return int(PID_FILE.read_text(encoding="utf-8").strip())
        except Exception:
            return None

    def _write_pid(self, pid):
        PID_FILE.write_text(str(pid), encoding="utf-8")

    def _remove_pid(self):
        try:
            PID_FILE.unlink()
        except FileNotFoundError:
            pass
        except Exception:
            pass

    def _process_running(self):
        return self.process is not None and self.process.poll() is None

    def _auto_start_if_needed(self):
        if not self._process_running() and not self._health_check():
            self.start_server()

    def _refresh_status(self):
        pid = self.process.pid if self._process_running() else self._read_pid()
        healthy = self._health_check() if self.health_monitor_var.get() else None

        if self._process_running():
            self.status_var.set("运行中")
            self.run_status_var.set("运行中")
            self.run_badge.configure(bg=self.colors["green_bg"], fg=self.colors["green_text"])
            self.pid_var.set(f"PID：{self.process.pid}")
            self.start_button.configure(state=tk.DISABLED)
            self.stop_button.configure(state=tk.NORMAL)
            self.restart_button.configure(state=tk.NORMAL)
            self.port_entry.configure(state=tk.DISABLED)
        elif healthy:
            self.status_var.set("运行中")
            self.run_status_var.set("运行中")
            self.run_badge.configure(bg=self.colors["green_bg"], fg=self.colors["green_text"])
            self.pid_var.set(f"PID：{pid or '-'}")
            self.start_button.configure(state=tk.DISABLED)
            self.stop_button.configure(state=tk.NORMAL if pid else tk.DISABLED)
            self.restart_button.configure(state=tk.NORMAL if pid else tk.DISABLED)
            self.port_entry.configure(state=tk.DISABLED)
        else:
            self.status_var.set("未运行")
            self.run_status_var.set("未运行")
            self.run_badge.configure(bg=self.colors["red_bg"], fg=self.colors["red_text"])
            self.pid_var.set("PID：-")
            self.start_button.configure(state=tk.NORMAL)
            self.stop_button.configure(state=tk.DISABLED)
            self.restart_button.configure(state=tk.DISABLED)
            self.port_entry.configure(state=tk.NORMAL)
            if pid and healthy is False:
                self._remove_pid()

        if healthy is True:
            self.health_status_var.set("服务正常")
            self.health_badge.configure(bg=self.colors["green_bg"], fg=self.colors["green_text"])
        elif healthy is None:
            self.health_status_var.set("未监控")
            self.health_badge.configure(bg=self.colors["yellow_bg"], fg=self.colors["yellow_text"])
        else:
            self.health_status_var.set("服务异常")
            self.health_badge.configure(bg=self.colors["red_bg"], fg=self.colors["red_text"])

        self.after(1000, self._refresh_status)

    def start_server(self):
        try:
            port = self._get_port()
        except ValueError as e:
            messagebox.showerror("端口错误", str(e))
            return

        if self._health_check(port):
            messagebox.showwarning("已在运行", f"端口 {port} 已有服务在运行。")
            return

        self._ensure_log_file()
        if SERVER_EXE.exists():
            cmd = [str(SERVER_EXE), "--port", str(port)]
        else:
            cmd = [get_python_executable(), "-u", str(SERVER_SCRIPT), "--port", str(port)]
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"

        try:
            self._write_manager_log(f"启动服务：{' '.join(cmd)}")
            log_handle = LOG_FILE.open("a", encoding="utf-8", buffering=1)
            try:
                kwargs = {
                    "cwd": str(APP_DIR),
                    "stdout": log_handle,
                    "stderr": subprocess.STDOUT,
                    "stdin": subprocess.DEVNULL,
                    "env": env,
                }
                if os.name == "nt":
                    kwargs["creationflags"] = CREATE_NO_WINDOW
                    kwargs["startupinfo"] = hidden_startupinfo()
                self.process = subprocess.Popen(cmd, **kwargs)
            finally:
                log_handle.close()
            self._write_pid(self.process.pid)
            self._write_manager_log(f"服务已启动，PID={self.process.pid}，Base URL=http://127.0.0.1:{port}/v1")
        except Exception as e:
            self._write_manager_log(f"启动失败：{e}")
            messagebox.showerror("启动失败", str(e))

    def _pid_command_line(self, pid):
        if os.name != "nt":
            return ""
        script = f'(Get-CimInstance Win32_Process -Filter "ProcessId={pid}").CommandLine'
        try:
            result = run_hidden(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script])
            return (result.stdout or "").strip()
        except Exception:
            return ""

    def _terminate_pid(self, pid):
        if os.name == "nt":
            command_line = self._pid_command_line(pid)
            if command_line and "gemini_web2api.py" not in command_line and "gemini_web2api_server" not in command_line:
                messagebox.showwarning("拒绝关闭", f"PID {pid} 看起来不是 gemini_web2api 服务。")
                return False
            result = run_hidden(["taskkill", "/PID", str(pid), "/T", "/F"])
            return result.returncode == 0

        try:
            os.kill(pid, signal.SIGTERM)
            return True
        except Exception:
            return False

    def stop_server(self):
        stopped = False
        if self._process_running():
            pid = self.process.pid
            self._write_manager_log(f"关闭服务：PID={pid}")
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=5)
            stopped = True
        else:
            pid = self._read_pid()
            if pid:
                self._write_manager_log(f"按 PID 关闭后台服务：PID={pid}")
                stopped = self._terminate_pid(pid)

        if stopped:
            self._remove_pid()
            self.process = None
            self._write_manager_log("服务已关闭")
        elif self._health_check():
            messagebox.showwarning("无法关闭", "检测到端口仍有服务，但没有可安全关闭的管理器 PID。")
        else:
            self._remove_pid()

    def restart_server(self):
        self.stop_server()
        self.after(800, self.start_server)

    def open_base_url(self):
        webbrowser.open(self.base_url_var.get())

    def open_admin_url(self):
        webbrowser.open(self.admin_url_var.get())

    def open_log_file(self):
        self._ensure_log_file()
        if os.name == "nt":
            os.startfile(str(LOG_FILE))
        else:
            webbrowser.open(LOG_FILE.as_uri())

    def clear_log_view(self):
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.delete("1.0", tk.END)
        self.log_text.configure(state=tk.DISABLED)

    def refresh_log_view(self):
        self.log_pos = 0
        self.clear_log_view()
        self._load_recent_log()

    def copy_log_view(self):
        text = self.log_text.get("1.0", "end-1c")
        self.copy_text(text, "日志视图")

    def copy_text(self, value, label="文本"):
        self.clipboard_clear()
        self.clipboard_append(value)
        self._write_manager_log(f"已复制：{label}")

    def _on_close(self):
        if self.stop_on_exit_var.get() and self._process_running():
            self.stop_server()
        self.destroy()


if __name__ == "__main__":
    app = GeminiManager()
    app.mainloop()
