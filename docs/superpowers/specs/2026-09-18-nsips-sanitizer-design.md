# NSIPS Sanitizer 設計書

- **日付**: 2026-09-18
- **プロジェクト名（仮）**: `nsips-sanitizer`
- **目的**: USB 上の NSIPS OK フォルダ内 `.txt` から患者個人情報（record type 1）を削除したコピーを出力するデスクトップツール

---

## 1. 背景と目的

薬局レセコン（Medicom Pharnes 等）が USB に書き出す NSIPS 形式の処方箋データ `.txt` には、以下のようなレコード種別が含まれる:

- `VER01xxxx,...` — ヘッダ（施設情報）
- `1,<患者PII>` — 患者個人情報（氏名・生年月日・住所等）
- `2,...` — 処方情報
- `3,...` — 用法
- `4,...` — 薬剤
- `5,`/`6,`/`7,` — 点数・調剤料等

このうち **record type 1（患者PII）を含む行を削除した .txt を、別フォルダに出力する** ユーティリティを作る。原本は USB 上でそのまま残す。

**似ているが別プロジェクト**: `nsips-watcher` は同じ NSIPS 形式を扱うが、solamichi クライアントの OK 監視 + 統計 API 送信が主目的で、常駐アプリ。本ツールは USB 上ファイルの都度サニタイズが目的で、常駐しない。

---

## 2. 技術スタック

- Python 3.11
- tkinter（stdlib）
- pytest（開発時のみ）
- PyInstaller で単一 `.exe` 化（`--onefile --windowed`）
- 依存追加ゼロ（stdlib のみ）

`nsips-watcher` / `sips-watcher` と揃えた構成。

---

## 3. ディレクトリ構成

```
~/dev/nsips-sanitizer/
├── src/
│   ├── __init__.py
│   ├── sanitizer.py     # サニタイズ純関数（I/O 非依存）
│   ├── main.py          # tkinter GUI + イベントハンドラ
│   └── __main__.py      # python -m nsips_sanitizer 起動用
├── tests/
│   ├── test_sanitizer.py
│   └── fixtures/
│       └── sample_ok/   # 架空データ .txt
├── docs/
│   └── superpowers/
│       └── specs/
│           └── 2026-09-18-nsips-sanitizer-design.md
├── build.spec           # PyInstaller 設定
├── requirements-dev.txt # pytest のみ
└── README.md
```

**責務分離**
- `sanitizer.py`: バイト列を受け取り `1,` 行削除済みバイト列を返す純関数 + 入出力フォルダを受け取り一括処理する関数。tkinter 非依存。
- `main.py`: GUI レイアウトとイベントハンドラのみ。処理は `sanitizer.py` に委譲。

---

## 4. GUI 仕様

**ウィンドウ**: 600×400、タイトル `NSIPS Sanitizer`

```
┌────────────────────────────────────────────────────────┐
│  NSIPS Sanitizer                                       │
├────────────────────────────────────────────────────────┤
│  入力フォルダ (OK):                                    │
│  ┌──────────────────────────────────┐ [ 選択... ]     │
│  │ (未選択)                          │                │
│  └──────────────────────────────────┘                 │
│                                                        │
│  出力フォルダ:                                         │
│  ┌──────────────────────────────────┐ [ 選択... ]     │
│  │ (未選択)                          │                │
│  └──────────────────────────────────┘                 │
│                                                        │
│                    [  実行  ]                          │
│                                                        │
│  ステータス: 待機中                                    │
└────────────────────────────────────────────────────────┘
```

**動作**
- 「選択...」ボタン → `filedialog.askdirectory()` でパス選択、Entry に反映
- 「実行」ボタン → 両フォルダ指定チェック（未指定なら `messagebox.showwarning`）
- 実行中はボタン disable、ステータス欄に `処理中: 3/12 (foo.txt)` 表示
- 完了時に `messagebox.showinfo` でサマリー:

  ```
  完了しました

  処理: 12 件
  スキップ: 0 件
  エラー: 0 件
  ```

- サニタイズは別スレッド、GUI 更新は `queue.Queue` + `root.after(200, poll)`（`nsips-watcher` と同じパターン）

**メニュー**
- `ファイル(F)` → `終了`
- `ヘルプ(H)` → `バージョン情報`

---

## 5. サニタイズ処理仕様

**入力データの前提**
- NSIPS 形式 CSV ライクテキスト
- 各行の先頭が「レコード種別番号 + `,`」
- 行区切りは CRLF（NSIPS 標準）
- エンコーディングは Shift-JIS（NSIPS 標準）

**アルゴリズム**
1. ファイルを **バイナリモード** (`rb`) で読み込む
2. `bytes.splitlines(keepends=True)` で行ごとの終端子を含めた分割
3. 各行について、行頭が `b"1,"` で始まる行を除外（`bytes.startswith(b"1,")` で判定）
4. `b"".join(...)` で結合し、出力ファイルへバイナリ書き込み

`b"1,"` プレフィックス判定なので `b"10,"` `b"11,"` `b"2,"` 等の他レコード種別は誤マッチしない。また `keepends=True` により CRLF/LF が混在していても各行の元の終端子が保持される。

**バイナリ処理の理由**
- Shift-JIS デコード/再エンコードを避け、レセコン依存の外字による文字化けを回避
- 改行コード（CRLF）を機械的に保持
- 「先頭 `1,`」は ASCII 範囲のためバイト比較で安全に判定可能

**エッジケース**

| ケース | 挙動 |
|---|---|
| `1,` レコードが 0 件 | そのままコピー |
| `1,` レコードが複数 | すべて削除 |
| ファイルが空 | 空ファイルを出力 |
| バイナリ壊れ / 読めない | スキップしてエラーカウント +1 |
| 出力先に同名ファイルあり | **上書き** |
| 出力先フォルダが未作成 | 自動作成（`mkdir(parents=True, exist_ok=True)`）|

**処理スコープ**
- 入力フォルダ **直下** の `.txt` / `.TXT` のみ
- サブフォルダは再帰しない
- `.txt` 以外はスキップ（サマリーに含めない）

**保持する情報**
- ファイル名: 変更なし
- タイムスタンプ: `shutil.copystat` 相当で保持

---

## 6. テスト戦略

`tests/test_sanitizer.py`（pytest, macOS で全 pass 目標）

**サニタイズ純関数テスト** (`sanitize_bytes`)
- `1,` レコード 1 件のファイル → 削除される
- `1,` レコード 0 件 → そのまま
- `1,` レコード複数 → すべて削除
- 空ファイル → 空
- CRLF が保持される
- `1,` を含むが行頭でない行（例: `4,1,1,1,...`）は残る
- Shift-JIS 実バイト列を通しても壊れない

**フォルダ一括処理テスト** (`sanitize_folder`)
- `.txt` のみ処理される（他拡張子はスキップ）
- サブフォルダ内の `.txt` は無視される
- 出力先が存在しなくても作成される
- 出力先の同名ファイルは上書きされる
- 結果サマリー（処理件数・スキップ件数・エラー件数）が正しい

**Fixture**: `tests/fixtures/sample_ok/` に架空データ .txt 数件（患者名は「テスト太郎」等ダミー）。

---

## 7. 配布 (Windows .exe)

- `build.spec` を PyInstaller 用に用意（`--onefile --windowed --name NsipsSanitizer`）
- **ビルドは Windows 実機で実施**（PyInstaller はクロスビルド不可）

**手順**（README に記載）
1. Windows PC で Python 3.11 インストール
2. `git clone https://github.com/hidemasa658/nsips-sanitizer.git`
3. `pip install pyinstaller`
4. `pyinstaller build.spec` → `dist\NsipsSanitizer.exe` 生成
5. USB にコピー → 対象 PC でダブルクリック起動

**Windows 実機動作確認**（手動、README にチェックリスト）
- GUI 起動、フォルダ選択、実行、サマリー表示
- USB 上の実 .txt でサニタイズ動作
- 出力ファイルの `1,` レコード削除をメモ帳で目視確認

---

## 8. リポジトリ

- 初回コミット後、GitHub `hidemasa658/nsips-sanitizer` (private) に push

---

## 9. スコープ外 (YAGNI)

- ドラッグ&ドロップ対応
- 常駐監視モード（必要なら `nsips-watcher` を使う）
- 進捗プログレスバー（ステータス文字列で十分）
- 多言語対応
- Inno Setup 化（配布方式は単一 .exe で確定）
- ログファイル出力（GUI サマリーのみで十分）
- ハッシュや監査証跡の記録
