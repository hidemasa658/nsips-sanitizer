"""NSIPS Sanitizer — 患者PII (record type 1) を削除する純関数群。"""
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional


ProgressCallback = Callable[[int, int, str], None]


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
