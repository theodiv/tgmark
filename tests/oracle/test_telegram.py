import re

import pytest
from tdlib_oracle import Entity, Verdict

from tests.oracle.telegram import check_message


@pytest.mark.parametrize(
    "text",
    [
        pytest.param("Total: 42", id="plain"),
        # The server cleans C0 controls only.
        pytest.param("a\x7fb\x85c", id="del-and-c1"),
        # The limit counts code points, so 8,192 UTF-16 units still fit.
        pytest.param("\N{GRINNING FACE}" * 4096, id="limit-astral"),
    ],
)
def test_passes_a_text_the_server_keeps_as_sent(text: str) -> None:
    check_message({"text": text})


def test_passes_an_empty_entity_list() -> None:
    check_message({"text": "Total: 42", "entities": []})


@pytest.mark.parametrize(
    ("text", "description"),
    [
        pytest.param("\N{ZERO WIDTH SPACE}", "text must be non-empty", id="blank"),
        pytest.param("a" * 4097, "message is too long", id="over-limit"),
        pytest.param("\r" * 32768 + "a", "text is too long", id="over-byte-cap"),
        pytest.param("a\ud800", "strings must be encoded in UTF-8", id="surrogate"),
    ],
)
def test_fails_a_text_the_server_refuses(text: str, description: str) -> None:
    match = f"refuses the message: .*{re.escape(description)}"
    with pytest.raises(AssertionError, match=match):
        check_message({"text": text})


@pytest.mark.parametrize(
    ("text", "start", "kept"),
    [
        pytest.param("a\rb", 1, "b", id="dropped"),
        pytest.param("a\tb", 1, " b", id="replaced"),
        pytest.param(
            "a\N{LEFT-TO-RIGHT MARK}\N{RIGHT-TO-LEFT MARK}b",
            1,
            "\N{ZERO WIDTH NON-JOINER}\N{RIGHT-TO-LEFT MARK}b",
            id="marks-replaced",
        ),
        pytest.param(" a\n", 0, "a", id="edges-trimmed"),
    ],
)
def test_fails_a_text_the_server_changes(text: str, start: int, kept: str) -> None:
    difference = f"from code point {start}: sent {text[start:]!r}, kept {kept!r}"
    with pytest.raises(AssertionError, match=re.escape(difference)):
        check_message({"text": text})


@pytest.mark.parametrize(
    ("params", "unchecked"),
    [
        pytest.param(
            {"text": "<b>a</b>", "parse_mode": "HTML"}, "parse_mode", id="parse-mode"
        ),
        pytest.param(
            {"text": "a", "entities": [{"type": "bold", "offset": 0, "length": 1}]},
            "entities",
            id="entities",
        ),
        pytest.param({"caption": "a"}, "caption", id="caption"),
    ],
)
def test_fails_a_parameter_tdlib_oracle_does_not_check(
    params: dict[str, object], unchecked: str
) -> None:
    with pytest.raises(AssertionError, match=rf"text only, not {unchecked}$"):
        check_message(params)


@pytest.mark.parametrize(
    ("params", "held"),
    [
        pytest.param({}, "None", id="missing"),
        pytest.param({"text": 42}, "42", id="int"),
    ],
)
def test_fails_a_message_without_a_text_string(
    params: dict[str, object], held: str
) -> None:
    with pytest.raises(AssertionError, match=rf"holds {held}, not a str$"):
        check_message(params)


def test_passes_a_text_at_max_length() -> None:
    check_message({"text": "\N{GRINNING FACE}" * 3}, max_length=3)


def test_fails_a_text_one_code_point_over_max_length() -> None:
    with pytest.raises(AssertionError, match=r"3 code points, over max_length 2$"):
        check_message({"text": "\N{GRINNING FACE}" * 3}, max_length=2)


@pytest.mark.parametrize(
    "verdict",
    [
        pytest.param(
            Verdict(
                accepted=True,
                text="a",
                entities=(Entity(type="bold", offset=0, length=1),),
                refusal=None,
                depends_on_backend=False,
            ),
            id="entity",
        ),
        pytest.param(
            Verdict(
                accepted=True,
                text="a",
                entities=(),
                refusal=None,
                depends_on_backend=True,
            ),
            id="backend-mark",
        ),
    ],
)
def test_fails_an_entity_or_mark_the_message_did_not_send(
    verdict: Verdict, monkeypatch: pytest.MonkeyPatch
) -> None:
    # No plain text keeps either, so the test builds the verdict.
    monkeypatch.setattr("tests.oracle.telegram.check", lambda text: verdict)
    with pytest.raises(AssertionError, match="keeps an entity or a backend mark"):
        check_message({"text": "a"})
