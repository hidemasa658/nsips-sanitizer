from src.sanitizer import sanitize_bytes


def test_sanitize_bytes_removes_single_record_1_line():
    data = (
        b"VER010603,20260819175225\r\n"
        b"1,PATIENT_PII_HERE\r\n"
        b"2,rx_body\r\n"
    )
    result = sanitize_bytes(data)
    assert result == b"VER010603,20260819175225\r\n2,rx_body\r\n"
