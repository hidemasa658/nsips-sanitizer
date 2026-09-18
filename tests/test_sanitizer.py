from pathlib import Path

from src.sanitizer import sanitize_bytes, sanitize_folder, SanitizeSummary

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "sample_ok"


def test_sanitize_bytes_removes_single_record_1_line():
    data = (
        b"VER010603,20260819175225\r\n"
        b"1,PATIENT_PII_HERE\r\n"
        b"2,rx_body\r\n"
    )
    result = sanitize_bytes(data)
    assert result == b"VER010603,20260819175225\r\n2,rx_body\r\n"


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
