from __future__ import annotations

import sys

from latency_vision.cli import main


def test_warns_on_vision_alias(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["vision"])
    main(["--version"])
    err = capsys.readouterr().err
    assert "'vision' is an alias of 'latvision'" in err


def test_no_warning_when_silenced(monkeypatch, capsys):
    monkeypatch.setenv("VISION_SILENCE_DEPRECATION", "1")
    monkeypatch.setattr(sys, "argv", ["vision"])
    main(["--version"])
    err = capsys.readouterr().err
    assert err == ""


def test_latvision_no_warning(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["latvision"])
    main(["--version"])
    err = capsys.readouterr().err
    assert "'vision' is an alias" not in err


def test_importing_vision_warns(monkeypatch, capsys):
    monkeypatch.delenv("VISION_SILENCE_DEPRECATION", raising=False)
    import importlib

    sys.modules.pop("vision", None)
    importlib.import_module("vision")
    err = capsys.readouterr().err
    assert "alias of 'latency_vision'" in err
