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
