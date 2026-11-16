"""The pinned Bot API server's verdict on each message, through TDLib Oracle.

The TDLib Oracle release in the `dev` group checks a plain message text alone, so a
message holding any other parameter fails here: output in a parse mode, with entities,
or as a caption cannot pass before the release that checks it.
"""

from collections.abc import Mapping

from tdlib_oracle import check

# Code points of each text that a failure shows from the first change.
_EXCERPT = 20


def check_message(
    params: Mapping[str, object], *, max_length: int | None = None
) -> None:
    """Check that the pinned Bot API server keeps a message exactly as sent.

    The server's own limits, 4,096 code points of kept text and 32,768 bytes of text as
    sent, reach a test as TDLib Oracle's refusals; only a test's `max_length` is
    counted here.

    Args:
        params: The Bot API parameters of the message, such as `text`.
        max_length: The most code points the kept text may hold, or `None` for the
            server's limit alone.

    Raises:
        AssertionError: If the message holds a parameter TDLib Oracle does not check or
            no text; if the server refuses it, changes its text, or keeps an entity or a
            backend mark; or if the kept text holds more than `max_length` code points.
    """
    __tracebackhide__ = True  # pytest reports a failure at the test's call

    # The server reads an empty entities list as no list
    # (telegram-bot-api/Client.cpp, Client::get_formatted_text()).
    sent = {key: value for key, value in params.items() if key != "entities" or value}
    unchecked = sorted(sent.keys() - {"text"})
    if unchecked:
        raise AssertionError(
            f"TDLib Oracle checks a plain message text only, not {', '.join(unchecked)}"
        )

    text = sent.get("text")
    if not isinstance(text, str):
        raise AssertionError(f"the text parameter holds {text!r}, not a str")

    verdict = check(text)
    kept = verdict.text
    if kept is None:
        raise AssertionError(f"the server refuses the message: {verdict.refusal}")
    if kept != text:
        raise AssertionError(f"the server changes the text {_difference(text, kept)}")
    if verdict.entities or verdict.depends_on_backend:
        raise AssertionError(
            "the server keeps an entity or a backend mark the message did not send"
        )

    if max_length is not None and len(kept) > max_length:
        raise AssertionError(
            f"the kept text holds {len(kept)} code points, over max_length {max_length}"
        )


def _difference(sent: str, kept: str) -> str:
    """Return where `kept` first differs from `sent`, with each text from there."""
    start = next(
        (index for index, (s, k) in enumerate(zip(sent, kept, strict=False)) if s != k),
        min(len(sent), len(kept)),
    )
    end = start + _EXCERPT
    return (
        f"from code point {start}: sent {sent[start:end]!r}, kept {kept[start:end]!r}"
    )
