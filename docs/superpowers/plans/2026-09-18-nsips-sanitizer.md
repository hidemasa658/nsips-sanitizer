# NSIPS Sanitizer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Mac-developed / Windows-distributed GUI tool that removes NSIPS record type 1 (patient PII) lines from `.txt` files in a USB `OK` folder and writes sanitized copies to a chosen output folder.

**Architecture:** Two-layer design — a pure-function `sanitizer` module (bytes-in / bytes-out, no I/O globals, easily testable) and a thin tkinter `main` module that wires folder pickers + a background worker thread to the pure function via a `queue.Queue`. The GUI runs on the tkinter main thread; the sanitization runs on a worker thread and reports progress + final summary through the queue.

**Tech Stack:** Python 3.11, tkinter (stdlib), pytest, PyInstaller (`--onefile --windowed`). No third-party runtime dependencies.

**Reference spec:** `docs/superpowers/specs/2026-09-18-nsips-sanitizer-design.md`

---

## File Structure

```
~/dev/nsips-sanitizer/
├── src/
│   ├── __init__.py           # empty
│   ├── sanitizer.py          # pure sanitization + folder batch
│   ├── main.py               # tkinter GUI + worker thread wiring
│   └── __main__.py           # `python -m src` entrypoint
├── tests/
│   ├── __init__.py           # empty
│   ├── test_sanitizer.py     # unit tests for sanitize_bytes + sanitize_folder
│   └── fixtures/
│       └── sample_ok/
│           ├── rx_001.txt    # fake NSIPS with a "1," record
│           ├── rx_002.txt    # fake NSIPS without any "1," record
│           └── rx_empty.txt  # zero bytes
├── build.spec                # PyInstaller config
├── requirements-dev.txt      # pytest only
├── .gitignore                # build/, dist/, __pycache__, .venv
└── README.md                 # overview + Windows build instructions
```

**Responsibility boundaries**
- `sanitizer.py`: two public functions and one dataclass.
  - `sanitize_bytes(data: bytes) -> bytes` — pure, no I/O
  - `SanitizeSummary` dataclass — `processed: int`, `skipped: int`, `errors: int`
  - `sanitize_folder(input_dir: Path, output_dir: Path, progress_cb=None) -> SanitizeSummary` — walks input dir non-recursively, filters `.txt`/`.TXT`, writes sanitized bytes to output dir, calls `progress_cb(current: int, total: int, filename: str)` for each file.
- `main.py`: tkinter GUI. Owns folder-picker Entry widgets, "実行" button, status Label. Spawns a `threading.Thread` running `sanitize_folder(...)` and marshals updates back through `queue.Queue` polled by `root.after(200, poll)`.

---

## Task 1: Project skeleton + first commit

**Files:**
- Create: `~/dev/nsips-sanitizer/.gitignore`
- Create: `~/dev/nsips-sanitizer/requirements-dev.txt`
- Create: `~/dev/nsips-sanitizer/src/__init__.py`
- Create: `~/dev/nsips-sanitizer/tests/__init__.py`
- Create: `~/dev/nsips-sanitizer/README.md`

- [ ] **Step 1: Create `.gitignore`**

```
__pycache__/
*.pyc
.venv/
venv/
build/
dist/
*.spec.bak
.pytest_cache/
.DS_Store
```

- [ ] **Step 2: Create `requirements-dev.txt`**

```
pytest==8.3.3
```

- [ ] **Step 3: Create empty `src/__init__.py` and `tests/__init__.py`**

Both files are zero bytes.

- [ ] **Step 4: Create minimal `README.md`**

````markdown
# NSIPS Sanitizer

NSIPS 形式 (院外処方箋データ) の `.txt` ファイルから、record type 1 (患者PII) の行を削除するデスクトップツール。

- 開発: macOS + Python 3.11
- 配布: Windows 単一 `.exe` (PyInstaller)

## 開発 (macOS)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
pytest -v
```

GUI 起動:

```bash
python -m src
```

## Windows ビルド

Windows 実機で以下を実行:

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install pyinstaller
pyinstaller build.spec
```

`dist\NsipsSanitizer.exe` が生成される。USB 経由で配布し、ダブルクリックで起動。

## 使い方

1. `NsipsSanitizer.exe` をダブルクリック
2. 「入力フォルダ (OK)」を選択 (USB 上の OK フォルダ)
3. 「出力フォルダ」を選択 (サニタイズ済みファイルの保存先)
4. 「実行」をクリック
5. 完了ダイアログで件数を確認
````

- [ ] **Step 5: Set up virtualenv and install dev deps**

Run:
```bash
cd ~/dev/nsips-sanitizer
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```
Expected: pytest installed, no errors.

- [ ] **Step 6: Commit**

Run:
```bash
cd ~/dev/nsips-sanitizer
git add .gitignore requirements-dev.txt src/__init__.py tests/__init__.py README.md
git commit -m "chore: project skeleton"
```

---

## Task 2: `sanitize_bytes` — 1件のPIIレコードを削除

**Files:**
- Create: `~/dev/nsips-sanitizer/src/sanitizer.py`
- Create: `~/dev/nsips-sanitizer/tests/test_sanitizer.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_sanitizer.py`:

```python
from src.sanitizer import sanitize_bytes


def test_sanitize_bytes_removes_single_record_1_line():
    data = (
        b"VER010603,20260819175225\r\n"
        b"1,PATIENT_PII_HERE\r\n"
        b"2,rx_body\r\n"
    )
    result = sanitize_bytes(data)
    assert result == b"VER010603,20260819175225\r\n2,rx_body\r\n"
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
cd ~/dev/nsips-sanitizer && source .venv/bin/activate
pytest tests/test_sanitizer.py::test_sanitize_bytes_removes_single_record_1_line -v
```
Expected: FAIL — `ModuleNotFoundError: No module named 'src.sanitizer'`.

- [ ] **Step 3: Write minimal implementation**

Create `src/sanitizer.py`:

```python
"""NSIPS Sanitizer — 患者PII (record type 1) を削除する純関数群。"""

def sanitize_bytes(data: bytes) -> bytes:
    """行頭が b"1," の行を削除。CRLF/LF は元の終端子を保持。"""
    lines = data.splitlines(keepends=True)
    kept = [ln for ln in lines if not ln.startswith(b"1,")]
    return b"".join(kept)
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
pytest tests/test_sanitizer.py::test_sanitize_bytes_removes_single_record_1_line -v
```
Expected: PASS.

- [ ] **Step 5: Commit**

Run:
```bash
git add src/sanitizer.py tests/test_sanitizer.py
git commit -m "feat(sanitizer): remove single record type 1 line"
```

---

## Task 3: `sanitize_bytes` — エッジケース網羅

**Files:**
- Modify: `~/dev/nsips-sanitizer/tests/test_sanitizer.py`

- [ ] **Step 1: Append edge-case tests**

Append to `tests/test_sanitizer.py`:

```python
def test_sanitize_bytes_no_record_1_returns_unchanged():
    data = b"VER010603,x\r\n2,rx\r\n3,dose\r\n"
    assert sanitize_bytes(data) == data


def test_sanitize_bytes_multiple_record_1_all_removed():
    data = (
        b"VER01,header\r\n"
        b"1,pii_a\r\n"
        b"2,rx\r\n"
        b"1,pii_b\r\n"
        b"3,dose\r\n"
    )
    expected = b"VER01,header\r\n2,rx\r\n3,dose\r\n"
    assert sanitize_bytes(data) == expected


def test_sanitize_bytes_empty_input_returns_empty():
    assert sanitize_bytes(b"") == b""


def test_sanitize_bytes_preserves_crlf():
    data = b"VER01,x\r\n1,pii\r\n2,y\r\n"
    assert b"\r\n" in sanitize_bytes(data)
    assert b"\n" in sanitize_bytes(data)  # (\r\n contains \n)


def test_sanitize_bytes_preserves_lf_only_when_input_is_lf():
    data = b"VER01,x\n1,pii\n2,y\n"
    result = sanitize_bytes(data)
    assert result == b"VER01,x\n2,y\n"
    assert b"\r\n" not in result


def test_sanitize_bytes_does_not_match_10_or_11_prefix():
    # 記録種別 10, 11 などは "1," で始まらないので残す
    data = b"1,pii\r\n10,other_record\r\n11,another\r\n"
    result = sanitize_bytes(data)
    assert result == b"10,other_record\r\n11,another\r\n"


def test_sanitize_bytes_does_not_match_1_in_middle_of_line():
    # 行の途中に "1," があっても削除しない
    data = b"4,1,1,1,4490025F2232\r\n1,pii\r\n"
    result = sanitize_bytes(data)
    assert result == b"4,1,1,1,4490025F2232\r\n"


def test_sanitize_bytes_shift_jis_bytes_pass_through():
    # Shift-JIS でエンコードされた日本語を含んでも壊れない
    header = "VER010603,ぞうさん薬局".encode("cp932")
    body = "2,処方情報".encode("cp932")
    pii = "1,患者太郎".encode("cp932")
    data = header + b"\r\n" + pii + b"\r\n" + body + b"\r\n"
    expected = header + b"\r\n" + body + b"\r\n"
    assert sanitize_bytes(data) == expected


def test_sanitize_bytes_no_trailing_newline():
    # 最終行に改行がなくても崩れない
    data = b"VER01,x\r\n1,pii\r\n2,last_no_newline"
    assert sanitize_bytes(data) == b"VER01,x\r\n2,last_no_newline"
```

- [ ] **Step 2: Run all sanitize_bytes tests**

Run:
```bash
pytest tests/test_sanitizer.py -v -k sanitize_bytes
```
Expected: 10 tests PASS (1 from Task 2 + 9 new).

- [ ] **Step 3: Commit**

Run:
```bash
git add tests/test_sanitizer.py
git commit -m "test(sanitizer): cover sanitize_bytes edge cases"
```

---

## Task 4: `SanitizeSummary` dataclass

**Files:**
- Modify: `~/dev/nsips-sanitizer/src/sanitizer.py`
- Modify: `~/dev/nsips-sanitizer/tests/test_sanitizer.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_sanitizer.py`:

```python
from src.sanitizer import SanitizeSummary


def test_summary_defaults_to_zero():
    s = SanitizeSummary()
    assert s.processed == 0
    assert s.skipped == 0
    assert s.errors == 0


def test_summary_fields_are_writable():
    s = SanitizeSummary()
    s.processed = 3
    s.errors = 1
    assert s.processed == 3
    assert s.errors == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
pytest tests/test_sanitizer.py::test_summary_defaults_to_zero -v
```
Expected: FAIL — `ImportError: cannot import name 'SanitizeSummary'`.

- [ ] **Step 3: Add dataclass to `src/sanitizer.py`**

Prepend imports and append the dataclass to `src/sanitizer.py`:

```python
"""NSIPS Sanitizer — 患者PII (record type 1) を削除する純関数群。"""
from dataclasses import dataclass


def sanitize_bytes(data: bytes) -> bytes:
    """行頭が b"1," の行を削除。CRLF/LF は元の終端子を保持。"""
    lines = data.splitlines(keepends=True)
    kept = [ln for ln in lines if not ln.startswith(b"1,")]
    return b"".join(kept)


@dataclass
class SanitizeSummary:
    processed: int = 0
    skipped: int = 0
    errors: int = 0
```

- [ ] **Step 4: Run tests to verify they pass**

Run:
```bash
pytest tests/test_sanitizer.py -v
```
Expected: 12 tests PASS.

- [ ] **Step 5: Commit**

Run:
```bash
git add src/sanitizer.py tests/test_sanitizer.py
git commit -m "feat(sanitizer): add SanitizeSummary dataclass"
```

---

## Task 5: `sanitize_folder` — .txt 一括処理 (fixture 準備)

**Files:**
- Create: `~/dev/nsips-sanitizer/tests/fixtures/sample_ok/rx_001.txt`
- Create: `~/dev/nsips-sanitizer/tests/fixtures/sample_ok/rx_002.txt`
- Create: `~/dev/nsips-sanitizer/tests/fixtures/sample_ok/rx_empty.txt`
- Create: `~/dev/nsips-sanitizer/tests/fixtures/sample_ok/readme.md` (非 .txt ファイル、無視されることを検証する用)

- [ ] **Step 1: Create fixture `rx_001.txt` (record 1 あり)**

Path: `tests/fixtures/sample_ok/rx_001.txt`. Encoding: Shift-JIS (cp932). Line ending: CRLF. Content (write via Python one-liner to guarantee bytes):

```bash
cd ~/dev/nsips-sanitizer
python3 -c "
data = (
    'VER010603,20260819175225,Medicom Pharnes,SERVER,14,4,2683084,ぞうさん薬局淵野辺店\r\n'
    '1,テスト太郎,19700101,男,神奈川県相模原市中央区淵野辺1-1-1\r\n'
    '2,260819000104001,218,A,20260819\r\n'
    '3,1,259,分２　朝夕食後服用\r\n'
    '4,1,1,1,4490025F2232\r\n'
).encode('cp932')
open('tests/fixtures/sample_ok/rx_001.txt', 'wb').write(data)
"
```

- [ ] **Step 2: Create fixture `rx_002.txt` (record 1 なし)**

```bash
python3 -c "
data = (
    'VER010603,20260819180000,Medicom Pharnes\r\n'
    '2,260819000105001,218,B,20260819\r\n'
    '3,1,7914,１日２回塗布\r\n'
).encode('cp932')
open('tests/fixtures/sample_ok/rx_002.txt', 'wb').write(data)
"
```

- [ ] **Step 3: Create empty fixture `rx_empty.txt`**

```bash
: > tests/fixtures/sample_ok/rx_empty.txt
```

- [ ] **Step 4: Create dummy non-txt file**

```bash
echo 'not a target' > tests/fixtures/sample_ok/readme.md
```

- [ ] **Step 5: Verify fixture bytes**

Run:
```bash
python3 -c "
import pathlib
p = pathlib.Path('tests/fixtures/sample_ok')
for f in sorted(p.iterdir()):
    print(f.name, f.stat().st_size, 'bytes')
"
```
Expected: 4 files listed, `rx_empty.txt` = 0 bytes, others > 0.

- [ ] **Step 6: Commit fixtures**

Run:
```bash
git add tests/fixtures/
git commit -m "test(fixtures): add sample_ok NSIPS files"
```

---

## Task 6: `sanitize_folder` — 基本動作 (処理・スキップ)

**Files:**
- Modify: `~/dev/nsips-sanitizer/src/sanitizer.py`
- Modify: `~/dev/nsips-sanitizer/tests/test_sanitizer.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_sanitizer.py`:

```python
from pathlib import Path
from src.sanitizer import sanitize_folder

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "sample_ok"


def test_sanitize_folder_processes_txt_only(tmp_path):
    out = tmp_path / "out"
    summary = sanitize_folder(FIXTURE_DIR, out)

    # rx_001, rx_002, rx_empty の 3 つが処理対象
    assert summary.processed == 3
    assert summary.errors == 0

    # 出力ファイルが存在
    assert (out / "rx_001.txt").exists()
    assert (out / "rx_002.txt").exists()
    assert (out / "rx_empty.txt").exists()

    # 非 .txt はコピーされない
    assert not (out / "readme.md").exists()


def test_sanitize_folder_removes_record_1_from_output(tmp_path):
    out = tmp_path / "out"
    sanitize_folder(FIXTURE_DIR, out)

    output_bytes = (out / "rx_001.txt").read_bytes()
    # record 1 行は削除されている
    for line in output_bytes.splitlines():
        assert not line.startswith(b"1,")
    # ヘッダは残っている
    assert output_bytes.startswith(b"VER010603,")


def test_sanitize_folder_leaves_file_without_record_1_intact(tmp_path):
    out = tmp_path / "out"
    sanitize_folder(FIXTURE_DIR, out)

    src = (FIXTURE_DIR / "rx_002.txt").read_bytes()
    dst = (out / "rx_002.txt").read_bytes()
    assert src == dst
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
```bash
pytest tests/test_sanitizer.py::test_sanitize_folder_processes_txt_only -v
```
Expected: FAIL — `ImportError: cannot import name 'sanitize_folder'`.

- [ ] **Step 3: Implement `sanitize_folder`**

Append to `src/sanitizer.py`:

```python
from pathlib import Path
from typing import Callable, Optional


ProgressCallback = Callable[[int, int, str], None]


def sanitize_folder(
    input_dir: Path,
    output_dir: Path,
    progress_cb: Optional[ProgressCallback] = None,
) -> SanitizeSummary:
    """input_dir 直下の .txt / .TXT をサニタイズして output_dir に書き出す。

    - サブフォルダは走査しない
    - .txt 以外の拡張子はスキップ (サマリーに含めない)
    - 出力先が存在しなければ作成
    - 出力先の同名ファイルは上書き
    - 読めない/書けないファイルは errors にカウント
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    summary = SanitizeSummary()

    targets = sorted(
        p for p in input_dir.iterdir()
        if p.is_file() and p.suffix.lower() == ".txt"
    )
    total = len(targets)

    for i, src in enumerate(targets, start=1):
        if progress_cb:
            progress_cb(i, total, src.name)
        try:
            data = src.read_bytes()
            (output_dir / src.name).write_bytes(sanitize_bytes(data))
            summary.processed += 1
        except OSError:
            summary.errors += 1

    return summary
```

- [ ] **Step 4: Run tests to verify they pass**

Run:
```bash
pytest tests/test_sanitizer.py -v
```
Expected: all tests PASS (12 previous + 3 new = 15).

- [ ] **Step 5: Commit**

Run:
```bash
git add src/sanitizer.py tests/test_sanitizer.py
git commit -m "feat(sanitizer): batch process .txt files into output dir"
```

---

## Task 7: `sanitize_folder` — サブフォルダ無視・上書き・自動作成

**Files:**
- Modify: `~/dev/nsips-sanitizer/tests/test_sanitizer.py`

- [ ] **Step 1: Write additional tests**

Append to `tests/test_sanitizer.py`:

```python
def test_sanitize_folder_ignores_subdirectories(tmp_path):
    src_dir = tmp_path / "in"
    src_dir.mkdir()
    (src_dir / "top.txt").write_bytes(b"VER,h\r\n1,pii\r\n2,x\r\n")
    sub = src_dir / "sub"
    sub.mkdir()
    (sub / "nested.txt").write_bytes(b"VER,h\r\n1,pii\r\n")

    out = tmp_path / "out"
    summary = sanitize_folder(src_dir, out)

    assert summary.processed == 1
    assert (out / "top.txt").exists()
    assert not (out / "nested.txt").exists()
    assert not (out / "sub").exists()


def test_sanitize_folder_creates_missing_output_dir(tmp_path):
    src_dir = tmp_path / "in"
    src_dir.mkdir()
    (src_dir / "a.txt").write_bytes(b"VER,h\r\n")

    out = tmp_path / "nested" / "does_not_exist" / "yet"
    assert not out.exists()

    sanitize_folder(src_dir, out)

    assert out.is_dir()
    assert (out / "a.txt").exists()


def test_sanitize_folder_overwrites_existing_output_file(tmp_path):
    src_dir = tmp_path / "in"
    src_dir.mkdir()
    (src_dir / "a.txt").write_bytes(b"VER,new\r\n1,pii\r\n2,new\r\n")

    out = tmp_path / "out"
    out.mkdir()
    (out / "a.txt").write_bytes(b"STALE_CONTENT")

    sanitize_folder(src_dir, out)

    result = (out / "a.txt").read_bytes()
    assert b"STALE_CONTENT" not in result
    assert result == b"VER,new\r\n2,new\r\n"


def test_sanitize_folder_case_insensitive_extension(tmp_path):
    src_dir = tmp_path / "in"
    src_dir.mkdir()
    (src_dir / "upper.TXT").write_bytes(b"VER,h\r\n1,pii\r\n")

    out = tmp_path / "out"
    summary = sanitize_folder(src_dir, out)

    assert summary.processed == 1
    assert (out / "upper.TXT").exists()


def test_sanitize_folder_progress_callback_invoked(tmp_path):
    src_dir = tmp_path / "in"
    src_dir.mkdir()
    (src_dir / "a.txt").write_bytes(b"VER,a\r\n")
    (src_dir / "b.txt").write_bytes(b"VER,b\r\n")

    out = tmp_path / "out"
    calls = []
    sanitize_folder(src_dir, out, progress_cb=lambda i, t, n: calls.append((i, t, n)))

    assert calls == [(1, 2, "a.txt"), (2, 2, "b.txt")]


def test_sanitize_folder_empty_input_dir_returns_zero_summary(tmp_path):
    src_dir = tmp_path / "in"
    src_dir.mkdir()
    out = tmp_path / "out"

    summary = sanitize_folder(src_dir, out)

    assert summary.processed == 0
    assert summary.errors == 0
    assert out.is_dir()  # output dir は作成される
```

- [ ] **Step 2: Run all tests to verify they pass**

Run:
```bash
pytest tests/test_sanitizer.py -v
```
Expected: 21 tests PASS.

- [ ] **Step 3: Commit**

Run:
```bash
git add tests/test_sanitizer.py
git commit -m "test(sanitizer): cover folder-level edge cases"
```

---

## Task 8: GUI 骨格 (ウィンドウ + Entry + ボタン、動作なし)

**Files:**
- Create: `~/dev/nsips-sanitizer/src/main.py`
- Create: `~/dev/nsips-sanitizer/src/__main__.py`

- [ ] **Step 1: Create `src/main.py`**

```python
"""NSIPS Sanitizer GUI (tkinter)."""
from __future__ import annotations

import queue
import threading
from pathlib import Path
from tkinter import Tk, StringVar, filedialog, messagebox
from tkinter import ttk

from src.sanitizer import sanitize_folder, SanitizeSummary


APP_TITLE = "NSIPS Sanitizer"
POLL_INTERVAL_MS = 200


class App:
    def __init__(self, root: Tk) -> None:
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
        from tkinter import Menu
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
```

- [ ] **Step 2: Create `src/__main__.py`**

```python
from src.main import main

if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Smoke-test GUI launch (manual)**

Run:
```bash
cd ~/dev/nsips-sanitizer && source .venv/bin/activate
python -m src
```
Expected: 600×400 ウィンドウが開く。2 つの Entry + 「選択...」ボタン、「実行」ボタン、「ステータス: 待機中」が表示される。「選択...」を押すとフォルダ選択ダイアログが開き、選んだパスが Entry に入る。「実行」は押しても何も起こらない (次タスク)。ウィンドウを閉じてプロセスが終了することを確認。

- [ ] **Step 4: Commit**

Run:
```bash
git add src/main.py src/__main__.py
git commit -m "feat(gui): tkinter window skeleton with folder pickers"
```

---

## Task 9: GUI 実行ロジック (worker thread + queue + サマリー)

**Files:**
- Modify: `~/dev/nsips-sanitizer/src/main.py`

- [ ] **Step 1: Replace `_on_run` and add polling / worker methods**

In `src/main.py`, replace the `_on_run` method (currently `pass`) and add three new methods. Full replacement of the `App` class methods related to run/poll — locate `def _on_run(self) -> None:` and replace it with:

```python
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
```

- [ ] **Step 2: Manual smoke test — 正常系**

Create a scratch input dir with a sample file:
```bash
cd ~/dev/nsips-sanitizer
mkdir -p /tmp/nsips_in /tmp/nsips_out
cp tests/fixtures/sample_ok/rx_001.txt /tmp/nsips_in/
cp tests/fixtures/sample_ok/rx_002.txt /tmp/nsips_in/
python -m src
```

In the GUI:
1. 入力フォルダに `/tmp/nsips_in` を選択
2. 出力フォルダに `/tmp/nsips_out` を選択
3. 「実行」をクリック
4. サマリーダイアログ「処理: 2 件」を確認
5. OK を押して閉じる

Verify output:
```bash
ls /tmp/nsips_out
python3 -c "
data = open('/tmp/nsips_out/rx_001.txt', 'rb').read()
for line in data.splitlines():
    assert not line.startswith(b'1,'), 'record 1 が残っている!'
print('OK: rx_001.txt は record 1 削除済み')
"
```
Expected: `rx_001.txt` `rx_002.txt` の 2 ファイルが出力されている。record 1 削除確認スクリプトが「OK」を出す。

- [ ] **Step 3: Manual smoke test — フォルダ未指定エラー**

Run `python -m src`, フォルダを何も選ばずに「実行」→ 「入力フォルダと出力フォルダの両方を選択してください。」のダイアログが出ることを確認。

- [ ] **Step 4: Manual smoke test — 入力フォルダ不存在エラー**

Run `python -m src`, 入力欄に手で `/nonexistent/path` と入力、出力欄は `/tmp/nsips_out` を選択、「実行」→ 「入力フォルダが存在しません」のダイアログが出ることを確認。

- [ ] **Step 5: Cleanup smoke test dirs**

```bash
rm -rf /tmp/nsips_in /tmp/nsips_out
```

- [ ] **Step 6: Commit**

Run:
```bash
git add src/main.py
git commit -m "feat(gui): worker thread + queue polling + summary dialog"
```

---

## Task 10: PyInstaller build spec

**Files:**
- Create: `~/dev/nsips-sanitizer/build.spec`

- [ ] **Step 1: Create `build.spec`**

```python
# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file — Windows でのビルド用
# 使い方: pyinstaller build.spec

block_cipher = None

a = Analysis(
    ["src/__main__.py"],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="NsipsSanitizer",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # --windowed 相当 (コンソールを出さない)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
```

- [ ] **Step 2: Commit**

Run:
```bash
git add build.spec
git commit -m "build: add PyInstaller spec for Windows single-exe"
```

---

## Task 11: README にビルド手順とチェックリストを追記

**Files:**
- Modify: `~/dev/nsips-sanitizer/README.md`

- [ ] **Step 1: Append Windows 実機動作確認チェックリストと GitHub push 手順**

Append to `README.md`:

```markdown

## Windows 実機動作確認チェックリスト

`.exe` を Windows PC で配布する前に以下を目視確認:

- [ ] `dist\NsipsSanitizer.exe` をダブルクリックで GUI が起動する
- [ ] 「選択...」でフォルダ選択ダイアログが開く
- [ ] 実際の USB の OK フォルダを入力に指定してサニタイズが走る
- [ ] 出力フォルダに `.txt` が生成される
- [ ] 生成された `.txt` をメモ帳で開き、`1,` で始まる行が消えていることを確認
- [ ] 入力フォルダを空欄で「実行」→ 警告ダイアログが出る
- [ ] メニュー「ファイル → 終了」でアプリが終了する
- [ ] ウィンドウ右上の × でアプリが終了する

## GitHub

初回のみ:

```bash
gh repo create hidemasa658/nsips-sanitizer --private --source=. --push
```
```

- [ ] **Step 2: Commit**

Run:
```bash
git add README.md
git commit -m "docs: add Windows verification checklist and GitHub bootstrap"
```

---

## Task 12: 最終テスト & GitHub 初回 push

**Files:**
- (none — verification + external action only)

- [ ] **Step 1: 全テスト再実行**

Run:
```bash
cd ~/dev/nsips-sanitizer && source .venv/bin/activate
pytest -v
```
Expected: 21 tests PASS, 0 failures.

- [ ] **Step 2: git log 確認**

Run:
```bash
git log --oneline
```
Expected: 全 12 前後のコミットが並ぶ (Task 1〜11 分 + 事前の設計書コミット)。

- [ ] **Step 3: GitHub private repo 作成 & push (要ユーザー確認)**

⚠️ **このステップは実行前にユーザーに確認すること。** GitHub にリポジトリを作る破壊的でないが外向きの操作。

Run (ユーザー承認後):
```bash
cd ~/dev/nsips-sanitizer
gh repo create hidemasa658/nsips-sanitizer --private --source=. --push
```
Expected: `https://github.com/hidemasa658/nsips-sanitizer` が作成され、`main` が push される。

- [ ] **Step 4: メモリ更新 (要ユーザー確認)**

`~/.claude/projects/-Users-a/memory/MEMORY.md` に nsips-sanitizer プロジェクトエントリを追加、`~/.claude/projects/-Users-a/memory/nsips-sanitizer.md` に詳細メモを新規作成。

Contents に含めるべき情報:
- 場所: `~/dev/nsips-sanitizer/`
- GitHub: `hidemasa658/nsips-sanitizer` (private)
- 用途: NSIPS `.txt` から record 1 (患者PII) を削除して別フォルダに出力する Windows GUI (tkinter + PyInstaller)
- 姉妹プロジェクト: [[nsips-watcher]] は常駐監視 + 統計送信、こちらは USB 上ファイルの都度サニタイズ
- Windows 実機ビルドは未実施

---

## Self-Review (計画作成者のセルフチェック)

**Spec coverage:**
- ✅ アーキテクチャ (Task 8-9)
- ✅ 技術スタック (Task 1)
- ✅ ディレクトリ構成 (Task 1, 5, 8, 10)
- ✅ GUI レイアウト・動作 (Task 8, 9)
- ✅ サニタイズアルゴリズム (Task 2)
- ✅ エッジケース網羅 (Task 3, 7)
- ✅ .txt 一括処理 (Task 6)
- ✅ 上書き / 自動作成 (Task 7)
- ✅ サブフォルダ無視 (Task 7)
- ✅ 大文字 .TXT (Task 7)
- ✅ 進捗コールバック (Task 7)
- ✅ Shift-JIS スルー (Task 3)
- ✅ PyInstaller ビルド (Task 10)
- ✅ Windows 実機チェックリスト (Task 11)
- ✅ GitHub push (Task 12)

**Placeholder scan:** 全ステップに具体的なコードとコマンドあり。「次タスクで実装」表記は Task 8 の `_on_run` にのみあり、Task 9 で確実に埋まる旨明記。OK。

**Type consistency:** `SanitizeSummary` フィールド (`processed`, `skipped`, `errors`) は Task 4 で定義、Task 6/9 で同じ名前で参照。`sanitize_folder` の引数順 (input_dir, output_dir, progress_cb) は Task 6 で定義、Task 9 で同順で呼び出し。`progress_cb` 引数順 (i, t, name) も一致。OK。

**注意点:**
- Task 6 の `sanitize_folder` は `.txt` を発見できないケースでも `output_dir` を作成する (`mkdir(...)` を早期に実行するため)。Task 7 の空入力テストで検証済み。
- `SanitizeSummary.skipped` は現在の実装では常に 0 (仕様上、非 .txt は「スキップ」ではなく「対象外」なのでカウント対象外)。設計書 §5 エッジケース表と一致 (`.txt` 以外はサマリーに含めない)。
