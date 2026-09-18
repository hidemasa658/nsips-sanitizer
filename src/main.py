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
        input_path = self.input_var.get().strip()
        output_path = self.output_var.get().strip()

        if not input_path or not output_path:
            messagebox.showwarning(APP_TITLE, "入力フォルダと出力フォルダの両方を選択してください。")
            return

        input_dir = Path(input_path)
        output_dir = Path(output_path)

        if not input_dir.is_dir():
            messagebox.showerror(APP_TITLE, f"入力フォルダが存在しません:\n{input_dir}")
            return

        self.run_button.state(["disabled"])
        self.status_var.set("処理中...")

        self._worker = threading.Thread(
            target=self._worker_run,
            args=(input_dir, output_dir),
            daemon=True,
        )
        self._worker.start()
        self.root.after(POLL_INTERVAL_MS, self._poll_queue)

    def _worker_run(self, input_dir: Path, output_dir: Path) -> None:
        try:
            summary = sanitize_folder(
                input_dir,
                output_dir,
                progress_cb=lambda i, t, n: self._queue.put(("progress", i, t, n)),
            )
            self._queue.put(("done", summary))
        except Exception as exc:  # noqa: BLE001 — worker thread must not crash silently
            self._queue.put(("error", str(exc)))

    def _poll_queue(self) -> None:
        try:
            while True:
                msg = self._queue.get_nowait()
                kind = msg[0]
                if kind == "progress":
                    _, i, t, name = msg
                    self.status_var.set(f"処理中: {i}/{t} ({name})")
                elif kind == "done":
                    _, summary = msg
                    self._on_done(summary)
                    return
                elif kind == "error":
                    _, err = msg
                    self._on_error(err)
                    return
        except queue.Empty:
            pass

        if self._worker and self._worker.is_alive():
            self.root.after(POLL_INTERVAL_MS, self._poll_queue)

    def _on_done(self, summary: SanitizeSummary) -> None:
        self.run_button.state(["!disabled"])
        self.status_var.set("完了")
        messagebox.showinfo(
            APP_TITLE,
            f"完了しました\n\n"
            f"処理: {summary.processed} 件\n"
            f"スキップ: {summary.skipped} 件\n"
            f"エラー: {summary.errors} 件",
        )

    def _on_error(self, err: str) -> None:
        self.run_button.state(["!disabled"])
        self.status_var.set("エラー")
        messagebox.showerror(APP_TITLE, f"処理中にエラーが発生しました:\n{err}")


def main() -> None:
    root = Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
