# Behavior

TGMark turns plain text, as a `str` or as `bytes`, into the text of Telegram
messages that the Bot API server keeps exactly as sent: before anything is sent,
it makes each change the server would make, splits text too long for one
message, and reports each change as a diagnostic. Everything else links here for
what a result means.

## Processing

The steps run in this order:

| #   | Step                                                                                                                                                                                                                                                                                         | Result                                                                                                                                                                                                                                                 |
| --- | ---                                                                                                                                                                                                                                                                                          | ---                                                                                                                                                                                                                                                    |
| 1   | `bytes` input: the byte order mark of UTF-8, UTF-16BE, or UTF-16LE at its start, or none                                                                                                                                                                                                     | Decoded in the encoding the mark names, without the mark, else in UTF-8; lines and columns count the decoded text                                                                                                                                      |
| 2   | A byte sequence the encoding refuses                                                                                                                                                                                                                                                         | U+FFFD for each [maximal subpart](https://www.unicode.org/versions/Unicode18.0.0/core-spec/chapter-3/) of it, as `bytes.decode` with `errors="replace"` gives, with an `undecodable-bytes` diagnostic for each                                         |
| 3   | A lone surrogate in `str` input, U+D800 to U+DFFF, which the server refuses as invalid UTF-8                                                                                                                                                                                                 | U+FFFD, with a `lone-surrogate` diagnostic                                                                                                                                                                                                             |
| 4   | A line ending: LF, CR, or CR LF                                                                                                                                                                                                                                                              | LF                                                                                                                                                                                                                                                     |
| 5   | A control character, U+0000 to U+001F, other than LF                                                                                                                                                                                                                                         | A space, as the server makes it, with a `control-character` diagnostic                                                                                                                                                                                 |
| 6   | U+2028 to U+202E, U+030A, U+0333, or U+033F                                                                                                                                                                                                                                                  | Removed, as the server removes it, with an `unsupported-character` diagnostic                                                                                                                                                                          |
| 7   | U+200E or U+200F directly followed by another of the two                                                                                                                                                                                                                                     | U+200C, as the server makes it, with a `direction-mark` diagnostic                                                                                                                                                                                     |
| 8   | Spaces and line feeds at either end                                                                                                                                                                                                                                                          | Trimmed, as the server trims them                                                                                                                                                                                                                      |
| 9   | More text than one message holds: 4,096 code points, or `max_length`                                                                                                                                                                                                                         | Split into messages, each ending at the last paragraph break that fits, else the last line break, sentence end, or run of spaces, else between two grapheme clusters; the spaces and line feeds at each cut are dropped, as the server would trim them |
| 10  | A grapheme cluster longer than one message                                                                                                                                                                                                                                                   | Cut at the limit, with a `cluster-too-long` diagnostic at each such cut                                                                                                                                                                                |
| 11  | A run of blank characters that cannot share a message with other text, being longer than one message or followed by no other text; blank characters are spaces, line feeds, U+00A0, U+1680, U+180E, U+2000 to U+200F, U+202F, U+205F, U+2800, U+3000, U+FEFF, U+FFFC, and U+E0000 to U+E007F | Dropped, since the server refuses a message of them alone, with a `blank-text` diagnostic                                                                                                                                                              |
| 12  | More messages than `max_parts`                                                                                                                                                                                                                                                               | The text past the last one dropped, with a `truncated` diagnostic                                                                                                                                                                                      |

## Limits

| Limit                    | Value                               | Past it                                         |
| ---                      | ---                                 | ---                                             |
| Kept text of a message   | 4,096 code points, or `max_length`  | Split into another message                      |
| Messages of a conversion | `max_parts`, with no cap by default | The rest dropped, with a `truncated` diagnostic |
| Input the command reads  | 4 MiB                               | Refused, with exit code `65`                    |

## Guarantees

- The Bot API server accepts every message `convert` returns and keeps its text
  exactly as sent, as the server's code at Bot API 10.4 behaves. TDLib Oracle,
  which reproduces that code, checks every message the tests produce.
- Every message keeps at most 4,096 code points, or `max_length`, and a
  conversion returns at most `max_parts` messages.
- Text splits at a paragraph break, line break, sentence end, or run of spaces
  before any other place. A cut drops only spaces and line feeds, and never
  falls inside a [grapheme cluster](https://www.unicode.org/reports/tr29/), as
  Unicode 18.0 and the running Python's Unicode version define one, unless the
  cluster alone is longer than a message.
- Only the steps in Processing lose or change text, and each step but 1, 4, 8,
  and 9 reports every change it makes as a diagnostic.
- A diagnostic or a `ConversionError` names a line and a column of the input and
  never quotes its text; an error line of the command names `FILE` by at most
  its last 32 characters, each non-printable character escaped.
- Outside strict mode, `convert` raises only `TypeError` and `ValueError`, for
  its arguments.
- Time and memory grow linearly with the length of the input.

Threats and how to report them: [`SECURITY.md`](../SECURITY.md).

## Out of Scope

- Sending messages, and any network access — the caller's Bot API client sends
  what `Message.params()` returns or the command writes.
- Media, keyboards, link previews, and every other send parameter — the caller
  adds them to what `Message.params()` returns.
- Converting partial input as it streams in — the caller converts the whole text
  once it has it.
- The rules Telegram's backend applies after the server's code — only a send to
  Telegram itself meets them.

## Terms

- **cut** — a place where text splits between two messages.
- **lenient mode** — the default: each condition in Processing is repaired or
  dropped, and reported as a diagnostic.
- **line break** — a run of spaces and line feeds that holds one line feed.
- **paragraph break** — a run of spaces and line feeds that holds two line feeds
  or more.
- **sentence end** — a run of spaces after a mark that ends a sentence, with
  closing brackets and quotation marks allowed between: `.`, `!`, `?`, `…`, `‼`,
  `‽`, `⁇`, `⁈`, `⁉`, U+037E, `։`, `؟`, `۔`, `।`, `॥`, `။`, `።`, `。`, `！`,
  `．`, `？`, or `｡`. After `。`, `！`, `？`, or `｡` and any closing brackets
  and quotation marks, a sentence ends with no space too.
- **strict mode** — `strict=True`: the condition at the earliest position raises
  `ConversionError` instead.
