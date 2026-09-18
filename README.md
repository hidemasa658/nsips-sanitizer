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

## macOS で GUI 動作確認する場合

pyenv でインストールした Python では `_tkinter` が組み込まれていないことが多いため、
macOS の System Python (`/usr/bin/python3`) を使うのが手っ取り早い:

```bash
cd ~/dev/nsips-sanitizer
/usr/bin/python3 -m src
```

テスト自体は tkinter を必要としないので `pytest` は pyenv 環境で通る。

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
