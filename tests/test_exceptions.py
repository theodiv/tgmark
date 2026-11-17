import pickle

from tgmark.exceptions import ConversionError, TGMarkError


def test_root_error_is_an_exception_but_not_an_argument_error() -> None:
    assert issubclass(TGMarkError, Exception)
    assert not issubclass(TGMarkError, (TypeError, ValueError))


def test_conversion_error_carries_the_condition_and_its_position() -> None:
    error = ConversionError(
        "blank text at line 2, column 1", code="blank-text", line=2, column=1
    )
    assert isinstance(error, TGMarkError)
    assert (str(error), error.code, error.line, error.column) == (
        "blank text at line 2, column 1",
        "blank-text",
        2,
        1,
    )


def test_conversion_error_survives_pickling() -> None:
    # A process pool pickles an error to hand it back from a worker.
    error = ConversionError(
        "blank text at line 2, column 1", code="blank-text", line=2, column=1
    )
    error.add_note("in a worker")
    copy = pickle.loads(pickle.dumps(error))  # noqa: S301  # the test's own error
    assert type(copy) is ConversionError
    assert (str(copy), copy.code, copy.line, copy.column, copy.__notes__) == (
        "blank text at line 2, column 1",
        "blank-text",
        2,
        1,
        ["in a worker"],
    )
