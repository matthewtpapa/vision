def test_offenders_are_objects():
    rep = {
        "sandbox_mode": "strace-only",
        "network_syscalls": True,
        "offending": [{"event": "strace", "detail": "socket()=3"}],
    }
    assert isinstance(rep["offending"], list)
    assert all(
        isinstance(item, dict) and "event" in item and "detail" in item for item in rep["offending"]
    )
