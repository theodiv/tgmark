import codecs
import errno
import json
import os
import subprocess
import sys
from io import BytesIO, TextIOWrapper
from pathlib import Path
from typing import NoReturn

import pytest

from tests.oracle.telegram import check_message
from tgmark import __version__
from tgmark.__main__ import main

# The most bytes the command reads.
_LIMIT = 4 * 1024 * 1024

# The source and target every conversion below names.
_FORMATS = ("--source", "plain", "--target", "entities")


class _BrokenStream(BytesIO):
    """A stream whose every read fails, as a read from a failing disk does."""

    def read(self, size: int | None = -1, /) -> bytes:
        raise OSError(errno.EIO, os.strerror(errno.EIO))


def _stdin(monkeypatch: pytest.MonkeyPatch, data: bytes) -> None:
    """Patch stdin to hold `data`."""
    monkeypatch.setattr(sys, "stdin", TextIOWrapper(BytesIO(data), encoding="utf-8"))


def _messages(out: bytes) -> list[dict[str, object]]:
    """Return the messages the command wrote, each passed through the checker.

    The output must be ASCII, one JSON object per line, each line ending in a line feed.
    """
    assert out.isascii()
    lines = out.decode("ascii").split("\n")
    assert lines.pop() == ""
    messages = [json.loads(line) for line in lines]
    for params in messages:
        check_message(params)
    return messages


def test_writes_each_message_of_a_file_as_a_line_of_json(
    tmp_path: Path, capfdbinary: pytest.CaptureFixture[bytes]
) -> None:
    first, second = "a" * 3000, "b" * 3000
    path = tmp_path / "report.txt"
    path.write_bytes(f"{first}\n\n{second}\n".encode())
    assert main([*_FORMATS, str(path)]) == 0
    out, err = capfdbinary.readouterr()
    assert (_messages(out), err) == ([{"text": first}, {"text": second}], b"")


@pytest.mark.parametrize(
    "arguments",
    [pytest.param([], id="no-file"), pytest.param(["-"], id="dash")],
)
def test_reads_stdin_without_a_file_or_for_a_dash(
    arguments: list[str],
    monkeypatch: pytest.MonkeyPatch,
    capfdbinary: pytest.CaptureFixture[bytes],
) -> None:
    _stdin(monkeypatch, b"Build #42 passed\n")
    assert main([*_FORMATS, *arguments]) == 0
    out, err = capfdbinary.readouterr()
    assert (_messages(out), err) == ([{"text": "Build #42 passed"}], b"")


def test_takes_the_short_flags(
    monkeypatch: pytest.MonkeyPatch, capfdbinary: pytest.CaptureFixture[bytes]
) -> None:
    _stdin(monkeypatch, b"Build #42 passed\n")
    assert main(["-s", "plain", "-t", "entities"]) == 0
    out, err = capfdbinary.readouterr()
    assert (_messages(out), err) == ([{"text": "Build #42 passed"}], b"")


def test_escapes_each_character_outside_ascii(
    monkeypatch: pytest.MonkeyPatch, capfdbinary: pytest.CaptureFixture[bytes]
) -> None:
    # The server keeps C1 controls, which some terminals act on.
    text = "Caf\u00e9 \N{WAVING HAND SIGN} \N{CONTROL SEQUENCE INTRODUCER}31m"
    _stdin(monkeypatch, text.encode())
    assert main(list(_FORMATS)) == 0
    out, err = capfdbinary.readouterr()
    assert out == b'{"text": "Caf\\u00e9 \\ud83d\\udc4b \\u009b31m"}\n'
    assert (_messages(out), err) == ([{"text": text}], b"")


def test_decodes_a_file_by_its_byte_order_mark(
    tmp_path: Path, capfdbinary: pytest.CaptureFixture[bytes]
) -> None:
    path = tmp_path / "report.txt"
    path.write_bytes(codecs.BOM_UTF16_LE + "Caf\u00e9\r\n".encode("utf-16-le"))
    assert main([*_FORMATS, str(path)]) == 0
    out, err = capfdbinary.readouterr()
    assert (_messages(out), err) == ([{"text": "Caf\u00e9"}], b"")


def test_writes_each_diagnostic_as_a_warning_line(
    monkeypatch: pytest.MonkeyPatch, capfdbinary: pytest.CaptureFixture[bytes]
) -> None:
    _stdin(monkeypatch, b"Build #42:\tpassed\nCaf\xe9\n")
    assert main(list(_FORMATS)) == 0
    out, err = capfdbinary.readouterr()
    assert _messages(out) == [{"text": "Build #42: passed\nCaf\ufffd"}]
    assert err.decode().splitlines() == [
        "tgmark: warning: control character replaced with a space at line 1, "
        "column 11 [control-character]",
        "tgmark: warning: undecodable bytes replaced with U+FFFD at line 2, "
        "column 4 [undecodable-bytes]",
    ]


@pytest.mark.parametrize(
    "data",
    [pytest.param(b"", id="empty"), pytest.param(b" \n\r\n ", id="blank")],
)
def test_writes_nothing_for_input_without_text(
    data: bytes,
    monkeypatch: pytest.MonkeyPatch,
    capfdbinary: pytest.CaptureFixture[bytes],
) -> None:
    _stdin(monkeypatch, data)
    assert main(list(_FORMATS)) == 0
    assert capfdbinary.readouterr() == (b"", b"")


def test_converts_input_of_4_mib(
    tmp_path: Path, capfdbinary: pytest.CaptureFixture[bytes]
) -> None:
    path = tmp_path / "report.txt"
    path.write_bytes(b"a" + b" " * (_LIMIT - 1))
    assert main([*_FORMATS, str(path)]) == 0
    out, err = capfdbinary.readouterr()
    assert (_messages(out), err) == ([{"text": "a"}], b"")


def test_refuses_a_file_over_4_mib(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capfdbinary: pytest.CaptureFixture[bytes],
) -> None:
    monkeypatch.chdir(tmp_path)
    Path("report.txt").write_bytes(b"a" * (_LIMIT + 1))
    assert main([*_FORMATS, "report.txt"]) == 65
    assert capfdbinary.readouterr() == (
        b"",
        b"tgmark: error: 'report.txt' is larger than 4 MiB\n",
    )


def test_refuses_stdin_over_4_mib(
    monkeypatch: pytest.MonkeyPatch, capfdbinary: pytest.CaptureFixture[bytes]
) -> None:
    _stdin(monkeypatch, b"a" * (_LIMIT + 1))
    assert main(list(_FORMATS)) == 65
    assert capfdbinary.readouterr() == (
        b"",
        b"tgmark: error: stdin is larger than 4 MiB\n",
    )


@pytest.mark.skipif(not Path("/dev/zero").exists(), reason="no /dev/zero")
def test_stops_reading_endless_input_past_4_mib(
    capfdbinary: pytest.CaptureFixture[bytes],
) -> None:
    assert main([*_FORMATS, "/dev/zero"]) == 65
    assert capfdbinary.readouterr() == (
        b"",
        b"tgmark: error: '/dev/zero' is larger than 4 MiB\n",
    )


@pytest.mark.parametrize(
    ("name", "reason"),
    [
        pytest.param("missing.txt", errno.ENOENT, id="missing"),
        pytest.param("folder", errno.EISDIR, id="directory"),
    ],
)
def test_reports_a_file_it_cannot_open(
    name: str,
    reason: int,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capfdbinary: pytest.CaptureFixture[bytes],
) -> None:
    monkeypatch.chdir(tmp_path)
    Path("folder").mkdir()
    assert main([*_FORMATS, name]) == 66
    line = f"tgmark: error: cannot open '{name}': {os.strerror(reason)}\n"
    assert capfdbinary.readouterr() == (b"", line.encode())


@pytest.mark.parametrize(
    ("name", "shown"),
    [
        pytest.param("new\x1b[31mline.txt", r"'new\x1b[31mline.txt'", id="control"),
        pytest.param("caf\udce9.txt", r"'caf\udce9.txt'", id="undecodable"),
        pytest.param(
            "reports/2026/11/nightly-build-summary.txt",
            "'.../11/nightly-build-summary.txt'",
            id="long",
        ),
    ],
)
def test_names_a_path_by_its_last_32_characters_escaped(
    name: str,
    shown: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capfdbinary: pytest.CaptureFixture[bytes],
) -> None:
    monkeypatch.chdir(tmp_path)
    assert main([*_FORMATS, name]) == 66
    line = f"tgmark: error: cannot open {shown}: {os.strerror(errno.ENOENT)}\n"
    assert capfdbinary.readouterr() == (b"", line.encode())


def test_reports_a_failed_read(
    monkeypatch: pytest.MonkeyPatch, capfdbinary: pytest.CaptureFixture[bytes]
) -> None:
    monkeypatch.setattr(sys, "stdin", TextIOWrapper(_BrokenStream(), encoding="utf-8"))
    assert main(list(_FORMATS)) == 74
    line = f"tgmark: error: cannot read stdin: {os.strerror(errno.EIO)}\n"
    assert capfdbinary.readouterr() == (b"", line.encode())


def test_reports_a_failed_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capfdbinary: pytest.CaptureFixture[bytes],
) -> None:
    path = tmp_path / "report.txt"
    path.write_bytes(b"Build #42 passed\n")
    reader, writer = os.pipe()
    os.close(reader)
    # The patch ends before the capture does, so the capture's own stdout comes back.
    with monkeypatch.context() as patch, os.fdopen(writer, "wb") as stdout:
        patch.setattr(sys, "stdout", stdout)
        assert main([*_FORMATS, str(path)]) == 74
    line = f"tgmark: error: cannot write stdout: {os.strerror(errno.EPIPE)}\n"
    assert capfdbinary.readouterr() == (b"", line.encode())


@pytest.mark.parametrize(
    ("failure", "line"),
    [
        pytest.param(
            ArithmeticError("text of the input"),
            "unexpected ArithmeticError",
            id="exception",
        ),
        pytest.param(KeyboardInterrupt(), "interrupted", id="interrupt"),
    ],
)
def test_reports_a_failure_it_does_not_expect_in_one_line(
    failure: BaseException,
    line: str,
    monkeypatch: pytest.MonkeyPatch,
    capfdbinary: pytest.CaptureFixture[bytes],
) -> None:
    def fail(*args: object, **kwargs: object) -> NoReturn:
        raise failure

    monkeypatch.setattr("tgmark.__main__.convert", fail)
    _stdin(monkeypatch, b"Build #42 passed\n")
    assert main(list(_FORMATS)) == 1
    assert capfdbinary.readouterr() == (b"", f"tgmark: error: {line}\n".encode())


@pytest.mark.parametrize(
    "arguments",
    [
        pytest.param([], id="no-formats"),
        pytest.param(["--source", "plain"], id="no-target"),
        pytest.param(["--source", "html", "--target", "entities"], id="unknown-source"),
        pytest.param(["--sou", "plain", "--target", "entities"], id="abbreviation"),
        pytest.param([*_FORMATS, "--bogus"], id="unknown-flag"),
        pytest.param([*_FORMATS, "a.txt", "b.txt"], id="two-files"),
    ],
)
def test_refuses_arguments_it_does_not_take(
    arguments: list[str], capfdbinary: pytest.CaptureFixture[bytes]
) -> None:
    with pytest.raises(SystemExit) as exit_info:
        main(arguments)
    assert exit_info.value.code == 2
    out, err = capfdbinary.readouterr()
    assert out == b""
    assert err.decode().splitlines()[-1].startswith("tgmark: error: ")


@pytest.fixture
def plain_terminal(monkeypatch: pytest.MonkeyPatch) -> None:
    # Python 3.14 and later color the help where these variables ask for it, and
    # argparse fills it to the width that `COLUMNS` gives.
    monkeypatch.delenv("FORCE_COLOR", raising=False)
    monkeypatch.delenv("PYTHON_COLORS", raising=False)
    monkeypatch.setenv("COLUMNS", "80")


def _documented_help(root: Path) -> str:
    """Return the help that `docs/cli.md` under `root` shows in its Usage section."""
    text = (root / "docs" / "cli.md").read_text(encoding="utf-8")
    start = text.index("```text\n", text.index("\n## Usage\n")) + len("```text\n")
    return text[start : text.index("```", start)]


@pytest.mark.skipif(
    sys.version_info < (3, 13),
    reason="argparse lays out a short form with a metavar otherwise before 3.13",
)
@pytest.mark.usefixtures("plain_terminal")
@pytest.mark.parametrize("flag", ["-h", "--help"])
def test_prints_the_help_that_docs_cli_md_shows(
    flag: str, pytestconfig: pytest.Config, capfdbinary: pytest.CaptureFixture[bytes]
) -> None:
    with pytest.raises(SystemExit) as exit_info:
        main([flag])
    assert exit_info.value.code == 0
    expected = _documented_help(pytestconfig.rootpath)
    assert capfdbinary.readouterr() == (expected.encode(), b"")


@pytest.mark.usefixtures("plain_terminal")
def test_lists_help_and_version_last(
    capfdbinary: pytest.CaptureFixture[bytes],
) -> None:
    with pytest.raises(SystemExit) as exit_info:
        main(["--help"])
    assert exit_info.value.code == 0
    out, err = capfdbinary.readouterr()
    options = out.decode().split("\noptions:\n")[1].split("\n\n")[0].splitlines()
    assert [line.split()[:2] for line in options[-2:]] == [
        ["-h,", "--help"],
        ["-V,", "--version"],
    ]
    assert err == b""


@pytest.mark.parametrize("flag", ["-V", "--version"])
def test_prints_its_version(
    flag: str, capfdbinary: pytest.CaptureFixture[bytes]
) -> None:
    with pytest.raises(SystemExit) as exit_info:
        main([flag])
    assert exit_info.value.code == 0
    assert capfdbinary.readouterr() == (f"tgmark {__version__}\n".encode(), b"")


@pytest.mark.parametrize(
    "command",
    [
        pytest.param([str(Path(sys.executable).with_name("tgmark"))], id="script"),
        pytest.param([sys.executable, "-m", "tgmark"], id="module"),
    ],
)
def test_runs_as_a_script_and_as_a_module(command: list[str]) -> None:
    result = subprocess.run([*command, "--version"], capture_output=True, check=False)
    assert (result.returncode, result.stdout, result.stderr) == (
        0,
        f"tgmark {__version__}\n".encode(),
        b"",
    )
