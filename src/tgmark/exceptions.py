"""Exception hierarchy rooted at `TGMarkError`."""

from functools import partial


class TGMarkError(Exception):
    """Root of the exceptions the package defines.

    Each exception class the package defines derives from it, so one `except` clause
    catches them all.
    """


class ConversionError(TGMarkError):
    """Raised in strict mode where lenient mode would repair or drop the input.

    Strict mode converts as lenient mode does, then raises for the condition at the
    earliest input position, the one the input's author fixes first, instead of
    returning a conversion that changes the input. The message names the condition and
    its position and never quotes the input.

    Attributes:
        code: The condition's code, as a `Diagnostic` carries it.
        line: The line where the condition starts in the input, counted from 1.
        column: The column in that line, counted from 1 in code points.
    """

    def __init__(self, message: str, *, code: str, line: int, column: int) -> None:
        super().__init__(message)
        self.code = code
        self.line = line
        self.column = column

    def __reduce__(
        self,
    ) -> tuple[partial["ConversionError"], tuple[object, ...], dict[str, object]]:
        # Unpickling calls the class with `args` alone, which lack the keyword-only
        # attributes, so they travel in a partial.
        rebuild = partial(
            type(self), code=self.code, line=self.line, column=self.column
        )
        return rebuild, self.args, self.__dict__
