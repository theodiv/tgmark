from tgmark.exceptions import TGMarkError


def test_root_error_is_an_exception_but_not_an_argument_error() -> None:
    assert issubclass(TGMarkError, Exception)
    assert not issubclass(TGMarkError, (TypeError, ValueError))
