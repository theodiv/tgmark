"""Command-line entry point.

This module alone parses arguments, reads the input, writes the messages and the
diagnostics, and maps each failure to an exit code, so it is the only one in the package
that calls `sys.exit`. It reaches the domains only through the composition module.
"""

import argparse
import json
import os
import sys
from collections.abc import Sequence
from contextlib import nullcontext

from tgmark import __version__
from tgmark.conversion import SOURCES, TARGETS, convert

# The most input the command reads, in MiB; more is refused, so endless input cannot use
# up the memory.
_LIMIT_MIB = 4
_LIMIT = _LIMIT_MIB * 1024 * 1024

# The most characters of a path that a diagnostic shows.
_PATH_LIMIT = 32

# Exit codes from sysexits.h, which `os` defines on Unix alone.
_EX_DATAERR = 65
_EX_NOINPUT = 66
_EX_IOERR = 74


def _parser() -> argparse.ArgumentParser:
    """Return the parser of the command's arguments.

    The options that set the conversion come first and `-h` and `-V` last, so the help
    option that argparse would add at the top gives way to one added after them.
    """
    parser = argparse.ArgumentParser(
        prog="tgmark",
        description=(
            "Convert text into Telegram messages that the Bot API server keeps as sent."
        ),
        epilog="Writes each message's Bot API parameters to stdout as a line of JSON.",
        add_help=False,
        allow_abbrev=False,
    )
    parser.add_argument(
        "file",
        nargs="?",
        metavar="FILE",
        help=f"the input file, at most {_LIMIT_MIB} MiB; stdin when absent or -",
    )
    parser.add_argument(
        "-s",
        "--source",
        required=True,
        choices=SOURCES,
        metavar="SOURCE",
        help="the format of the text: %(choices)s",
    )
    parser.add_argument(
        "-t",
        "--target",
        required=True,
        choices=TARGETS,
        metavar="TARGET",
        help="the form of each message: %(choices)s",
    )
    parser.add_argument(
        "-h", "--help", action="help", help="show this help message and exit"
    )
    parser.add_argument(
        "-V", "--version", action="version", version=f"%(prog)s {__version__}"
    )
    return parser


def _error(message: str) -> None:
    """Write `message` to stderr as an error line."""
    sys.stderr.write(f"tgmark: error: {message}\n")


def _warn(message: str) -> None:
    """Write `message` to stderr as a warning line."""
    sys.stderr.write(f"tgmark: warning: {message}\n")


def _quote(path: str) -> str:
    """Return how a diagnostic names the file at `path`.

    A path is input as much as the text is, so a diagnostic shows at most its last 32
    characters, the end that names the file, and `repr` quotes them and escapes each
    character a terminal could act on.
    """
    if len(path) > _PATH_LIMIT:
        path = "..." + path[3 - _PATH_LIMIT :]
    return repr(path)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the `tgmark` command and return its exit code.

    An exception nobody expected, or an interrupt, ends the run with exit code 1 and one
    error line instead of a traceback. The line names the exception by its class alone,
    since its message could quote the input.

    Args:
        argv: The arguments, or `None` for the process's own.

    Raises:
        SystemExit: If argparse ends the run: with code 0 once it prints the help or the
            version, or with code 2 for arguments it refuses.
    """
    arguments = _parser().parse_args(argv)
    try:
        return _run(arguments)
    except KeyboardInterrupt:
        _error("interrupted")
    except Exception as exc:
        _error(f"unexpected {type(exc).__name__}")
    return 1


def _run(arguments: argparse.Namespace) -> int:
    """Run the conversion that `arguments` describe and return the exit code."""
    path = None if arguments.file in (None, "-") else arguments.file
    name = "stdin" if path is None else _quote(path)
    try:
        stream = nullcontext(sys.stdin.buffer) if path is None else open(path, "rb")
    except OSError as exc:
        _error(f"cannot open {name}: {exc.strerror}")
        return _EX_NOINPUT
    try:
        with stream as reader:
            data = reader.read(_LIMIT + 1)
    except OSError as exc:
        _error(f"cannot read {name}: {exc.strerror}")
        return _EX_IOERR
    if len(data) > _LIMIT:
        _error(f"{name} is larger than {_LIMIT_MIB} MiB")
        return _EX_DATAERR

    conversion = convert(data, source=arguments.source, target=arguments.target)
    for diagnostic in conversion.diagnostics:
        _warn(
            f"{diagnostic.message} at line {diagnostic.line}, "
            f"column {diagnostic.column} [{diagnostic.code}]"
        )

    # `json.dumps` escapes each character outside ASCII, so the output reads the same in
    # any locale, and a terminal never meets a C1 control that the server keeps.
    lines = "".join(
        f"{json.dumps(message.params())}\n" for message in conversion.messages
    )
    output = sys.stdout.fileno()
    try:
        _write(output, lines.encode("ascii"))
    except OSError as exc:
        _error(f"cannot write stdout: {exc.strerror}")
        return _EX_IOERR
    return 0


def _write(descriptor: int, data: bytes) -> None:
    """Write all of `data` to `descriptor`.

    The bytes go to the descriptor itself, past `sys.stdout`: Python flushes that stream
    again at exit, so bytes a closed pipe refused would fail there a second time, with a
    message of Python's own and exit code 120.
    """
    view = memoryview(data)
    while view:
        view = view[os.write(descriptor, view) :]


if __name__ == "__main__":
    sys.exit(main())
