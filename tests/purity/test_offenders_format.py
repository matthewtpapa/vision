def test_offenders_are_objects():
    report = {
        "sandbox_mode": "strace-only",
        "network_syscalls": True,
        "offending": [{"event": "strace", "detail": "socket(...)=3"}],
    }
    assert isinstance(report["offending"], list)
    assert all(
        isinstance(offender, dict) and {"event", "detail"} <= set(offender)
        for offender in report["offending"]
    )
