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
