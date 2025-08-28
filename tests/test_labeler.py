from vision import Labeler


def test_labeler_returns_unknown_label():
    labeler = Labeler()
    assert labeler.label(object()) == "unknown"
