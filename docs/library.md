# Library

Every name in `tgmark.__all__`, with its parameters, return value, and
exceptions. What a result means: [Behavior](behavior.md).

## `Conversion`

What converting a text produced: its messages and its diagnostics.

- `messages` — the messages, as `Message` values in input order; empty when
  nothing remains to send.
- `diagnostics` — each condition lenient mode repaired or dropped, as
  `Diagnostic` values in input order.

## `Diagnostic`

A condition in the input that lenient mode repaired or dropped.

- `code` — the condition's code, one of those in
  [Processing](behavior.md#processing); a released code never changes.
- `message` — the condition and what lenient mode did instead, in one clause
  that never quotes the input.
- `line` — the line where the condition starts in the input, counted from 1.
- `column` — the column in that line, counted from 1 in code points.

## `Message`

One Telegram message, as the Bot API server keeps it.

- `text` — the text of the message.
- `params()` — the message's parameters for the Bot API's `sendMessage` method,
  as a new `dict` on each call, so the caller can add `chat_id` and the call's
  other parameters to it.

```pycon
>>> from tgmark import convert
>>> message = convert("Total: 42", source="plain", target="entities").messages[0]
>>> message.params()
{'text': 'Total: 42'}
```

## `convert`

```python
convert(text: str | bytes, *, source: Literal["plain"], target: Literal["entities"], max_length: int | None = None, max_parts: int | None = None, strict: bool = False) -> Conversion
```

Converts `text` into Telegram messages that the Bot API server keeps exactly as
sent, splitting text too long for one message.

- `text` — the text to convert: a `str`, or `bytes` in the encoding their byte
  order mark names, UTF-8, UTF-16BE, or UTF-16LE, else in UTF-8; a diagnostic's
  `line` and `column` then count the decoded text. *Changed in the next release:
  also takes `bytes`.*
- `source` — the format of `text`: `"plain"` reads every character as
  written; required.
- `target` — the form of each message: `"entities"` sends its text with no parse
  mode; required.
- `max_length` — the most code points the text of each message keeps, from 1 to
  4,096; default `None`, for 4,096.
- `max_parts` — the most messages to return, 1 or more, dropping the text past
  the last one with a `truncated` diagnostic; default `None`, for no cap.
- `strict` — whether to raise `ConversionError` instead of repairing or
  dropping; default `False`.

Returns a `Conversion`. Raises `TypeError` when an argument has the wrong type,
`ValueError` when `source` or `target` names another format or `max_length` or
`max_parts` is out of its range, and `ConversionError` when `strict` is set and
lenient mode would repair or drop anything.

```pycon
>>> from tgmark import convert
>>> convert("Total:\t42\n", source="plain", target="entities")
Conversion(messages=(Message(text='Total: 42'),), diagnostics=(Diagnostic(code='control-character', message='control character replaced with a space', line=1, column=7),))
>>> convert("First line.\nSecond line.", source="plain", target="entities", max_length=12)
Conversion(messages=(Message(text='First line.'), Message(text='Second line.')), diagnostics=())
>>> convert(b"\xef\xbb\xbfTotal: 42\r\n", source="plain", target="entities")
Conversion(messages=(Message(text='Total: 42'),), diagnostics=())
>>> convert(b"Caf\xe9", source="plain", target="entities").diagnostics
(Diagnostic(code='undecodable-bytes', message='undecodable bytes replaced with U+FFFD', line=1, column=4),)
```

## Exceptions

Every exception the package defines derives from `TGMarkError`, so one `except`
clause catches them all.

- `TGMarkError` — the root.
  - `ConversionError` — raised in strict mode for the condition at the earliest
    input position; its `code`, `line`, and `column` are those of the diagnostic
    lenient mode would report.
