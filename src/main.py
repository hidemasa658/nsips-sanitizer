"""NSIPS Sanitizer GUI (tkinter)."""
from __future__ import annotations

import queue
import threading
from pathlib import Path

# tkinter は macOS の pyenv Python で _tkinter が組み込まれていないことがあるため
# トップレベル import は try で包み、実行時 (main()) のみエラーを表面化する。
try:
    from tkinter import Tk, StringVar, filedialog, messagebox, Menu
    from tkinter import ttk
except ModuleNotFoundError:  # pragma: no cover
    Tk = StringVar = filedialog = messagebox = Menu = ttk = None  # type: ignore

from src.sanitizer import sanitize_folder, SanitizeSummary


APP_TITLE = "NSIPS Sanitizer"
POLL_INTERVAL_MS = 200


class App:
    def __init__(self, root: "Tk") -> None:
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("600x400")

        self.input_var = StringVar(value="")
        self.output_var = StringVar(value="")
        self.status_var = StringVar(value="待機中")

        self._queue: queue.Queue = queue.Queue()
        self._worker: threading.Thread | None = None

        self._build_ui()

    def _build_ui(self) -> None:
        frame = ttk.Frame(self.root, padding=16)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="入力フォルダ (OK):").grid(row=0, column=0, sticky="w", pady=(0, 4))
        input_entry = ttk.Entry(frame, textvariable=self.input_var, width=52)
        input_entry.grid(row=1, column=0, sticky="we", padx=(0, 8))
        ttk.Button(frame, text="選択...", command=self._pick_input).grid(row=1, column=1)

        ttk.Label(frame, text="出力フォルダ:").grid(row=2, column=0, sticky="w", pady=(12, 4))
        output_entry = ttk.Entry(frame, textvariable=self.output_var, width=52)
        output_entry.grid(row=3, column=0, sticky="we", padx=(0, 8))
        ttk.Button(frame, text="選択...", command=self._pick_output).grid(row=3, column=1)

        self.run_button = ttk.Button(frame, text="実行", command=self._on_run)
        self.run_button.grid(row=4, column=0, columnspan=2, pady=(24, 8))

        ttk.Label(frame, text="ステータス:").grid(row=5, column=0, sticky="w", pady=(16, 4))
        ttk.Label(frame, textvariable=self.status_var, foreground="#333").grid(
            row=6, column=0, columnspan=2, sticky="w"
        )

        frame.columnconfigure(0, weight=1)

        self._build_menu()

    def _build_menu(self) -> None:
        menubar = Menu(self.root)
        file_menu = Menu(menubar, tearoff=0)
        file_menu.add_command(label="終了", command=self.root.quit)
        menubar.add_cascade(label="ファイル(F)", menu=file_menu)

        help_menu = Menu(menubar, tearoff=0)
        help_menu.add_command(
            label="バージョン情報",
            command=lambda: messagebox.showinfo(APP_TITLE, f"{APP_TITLE} 1.0.0"),
        )
        menubar.add_cascade(label="ヘルプ(H)", menu=help_menu)
        self.root.config(menu=menubar)

    def _pick_input(self) -> None:
        path = filedialog.askdirectory(title="入力フォルダ (OK) を選択")
        if path:
            self.input_var.set(path)

    def _pick_output(self) -> None:
        path = filedialog.askdirectory(title="出力フォルダを選択")
        if path:
            self.output_var.set(path)

    def _on_run(self) -> None:
        # 次タスクで実装
        pass


def main() -> None:
    root = Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
